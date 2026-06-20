"""DeerFlow tool: semantic search over local documents with source citation."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from langchain.tools import tool

from deerflow.config import get_app_config

from .indexer import QUERY_PREFIX, embed_texts, search_sync

logger = logging.getLogger(__name__)

_DEFAULT_INDEX_PATH = ".deer-flow/data/local_rag.db"
_DEFAULT_MODEL = "nomic-embed-text"
_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_K = 5


@tool("local_docs_search", parse_docstring=True)
async def local_docs_search_tool(query: str, k: int = _DEFAULT_K) -> str:
    """Search local documents (droit, économie, ASC) by semantic similarity.

    Always cite the 'source' file path for each result so the user can locate
    the original document. Results are ordered by relevance score (1.0 = best).

    Before first use, build the index:
        python -m deerflow.community.local_rag.indexer --source-dir /path/to/docs

    Args:
        query: Natural language description of what you are looking for.
        k: Number of document excerpts to return (default 5).
    """
    index_path: str = _DEFAULT_INDEX_PATH
    embedding_model: str = _DEFAULT_MODEL
    base_url: str = _DEFAULT_BASE_URL
    k_val: int = k

    config = get_app_config().get_tool_config("local_docs_search")
    if config is not None:
        index_path = str(config.model_extra.get("index_path", index_path))
        embedding_model = str(config.model_extra.get("embedding_model", embedding_model))
        base_url = str(config.model_extra.get("base_url", base_url))
        k_val = int(config.model_extra.get("k", k_val))

    if not Path(index_path).exists():
        return json.dumps(
            {
                "error": "Index not built yet.",
                "hint": "Run: python -m deerflow.community.local_rag.indexer --source-dir <docs>",
                "index_path": index_path,
            },
            ensure_ascii=False,
        )

    try:
        embeddings = await embed_texts([f"{QUERY_PREFIX}{query}"], embedding_model, base_url)
        query_vector = embeddings[0]
    except Exception as exc:
        logger.error("local_docs_search: embedding failed: %s", exc)
        return json.dumps({"error": f"Embedding error: {exc}"}, ensure_ascii=False)

    results = await asyncio.to_thread(search_sync, index_path, query_vector, k_val)

    if not results:
        return json.dumps({"query": query, "total": 0, "results": []}, ensure_ascii=False)

    return json.dumps(
        {
            "query": query,
            "total": len(results),
            "results": [
                {
                    "source": r["source"],
                    "score": round(r["score"], 4),
                    "content": r["content"],
                }
                for r in results
            ],
        },
        indent=2,
        ensure_ascii=False,
    )
