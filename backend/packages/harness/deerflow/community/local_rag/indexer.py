"""Local RAG indexer — scan, chunk, embed (Ollama HTTP), store (SQLite + numpy).

Run as CLI to build or rebuild the index:
    python -m deerflow.community.local_rag.indexer --source-dir /path/to/docs
"""

from __future__ import annotations

import asyncio
import sqlite3
import struct
from collections.abc import Callable
from pathlib import Path

import httpx
import numpy as np

SUPPORTED_EXTENSIONS = frozenset({".md", ".txt", ".rst"})
DEFAULT_CHUNK_SIZE = 400
DEFAULT_CHUNK_OVERLAP = 60
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "

EmbedFn = Callable[[list[str]], list[list[float]]]


# ── Text chunking ──────────────────────────────────────────────────────────────


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    step = max(1, chunk_size - chunk_overlap)
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        if end >= len(words):
            break
        start += step
    return chunks


# ── Vector packing ─────────────────────────────────────────────────────────────


def _pack_vector(v: list[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)


def _unpack_vector(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32).copy()


# ── SQLite helpers ─────────────────────────────────────────────────────────────


def _open_db(index_path: str | Path) -> sqlite3.Connection:
    path = Path(index_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS chunks (id INTEGER PRIMARY KEY, source TEXT NOT NULL, content TEXT NOT NULL, embedding BLOB NOT NULL)")
    conn.commit()
    return conn


def _set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
    conn.commit()


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


# ── Cosine search (sync, safe for asyncio.to_thread) ──────────────────────────


def search_sync(
    index_path: str | Path,
    query_vector: list[float],
    k: int = 5,
) -> list[dict]:
    """Return top-k chunks by cosine similarity. Returns [] if index missing."""
    path = Path(index_path)
    if not path.exists():
        return []
    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute("SELECT source, content, embedding FROM chunks").fetchall()
    finally:
        conn.close()
    if not rows:
        return []
    q = np.array(query_vector, dtype=np.float32)
    q_norm = np.linalg.norm(q)
    results: list[dict] = []
    for source, content, emb_blob in rows:
        vec = _unpack_vector(emb_blob)
        v_norm = np.linalg.norm(vec)
        score = float(np.dot(q, vec) / (q_norm * v_norm)) if (q_norm > 0 and v_norm > 0) else 0.0
        results.append({"source": source, "content": content, "score": score})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]


# ── Embedding via Ollama HTTP API ─────────────────────────────────────────────


async def embed_texts(
    texts: list[str],
    model: str,
    base_url: str,
) -> list[list[float]]:
    """Call Ollama /api/embed and return one embedding per text."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/api/embed",
            json={"model": model, "input": texts},
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]


# ── Index builder ──────────────────────────────────────────────────────────────


async def build_index(
    source_dir: str | Path,
    index_path: str | Path,
    embedding_model: str = "nomic-embed-text",
    base_url: str = "http://localhost:11434",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    embed_fn: EmbedFn | None = None,
) -> int:
    """Scan source_dir, chunk text files, embed with Ollama, store in SQLite.

    Returns the number of chunks indexed.
    embed_fn replaces the Ollama HTTP call (used in tests for deterministic results).
    """
    source_path = Path(source_dir)
    if not source_path.is_dir():
        raise ValueError(f"source_dir does not exist: {source_dir}")

    conn = _open_db(index_path)
    conn.execute("DELETE FROM chunks")
    conn.commit()

    files = sorted(p for p in source_path.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS)

    total_chunks = 0
    last_dim: int = 0
    for file_path in files:
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        chunks = _chunk_text(text, chunk_size, chunk_overlap)
        if not chunks:
            continue
        prefixed = [f"{DOCUMENT_PREFIX}{c}" for c in chunks]
        if embed_fn is not None:
            embeddings = embed_fn(prefixed)
        else:
            embeddings = await embed_texts(prefixed, embedding_model, base_url)
        for chunk, embedding in zip(chunks, embeddings):
            conn.execute(
                "INSERT INTO chunks (source, content, embedding) VALUES (?, ?, ?)",
                (str(file_path), chunk, _pack_vector(embedding)),
            )
        conn.commit()
        total_chunks += len(chunks)
        last_dim = len(embeddings[0]) if embeddings else last_dim

    _set_meta(conn, "embedding_model", embedding_model)
    _set_meta(conn, "chunk_size", str(chunk_size))
    _set_meta(conn, "dimension", str(last_dim))
    conn.close()
    return total_chunks


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build local RAG index from a document folder.")
    parser.add_argument("--source-dir", required=True, help="Folder containing .md/.txt/.rst files")
    parser.add_argument("--index-path", default=".deer-flow/data/local_rag.db")
    parser.add_argument("--model", default="nomic-embed-text")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)
    args = parser.parse_args()

    n = asyncio.run(
        build_index(
            source_dir=args.source_dir,
            index_path=args.index_path,
            embedding_model=args.model,
            base_url=args.base_url,
            chunk_size=args.chunk_size,
            chunk_overlap=args.overlap,
        )
    )
    print(f"Index built: {n} chunks in {args.index_path}")
