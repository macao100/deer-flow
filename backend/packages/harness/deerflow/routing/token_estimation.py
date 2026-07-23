"""CJK-aware token estimation — shared by model_router and complexity_router.

This module provides a single token estimation heuristic so both routing
paths stay in sync without duplicating the estimation logic.
"""


def estimate_tokens(text: str) -> int:
    """CJK-aware token estimation (chars→tokens heuristic).

    Uses the common approximation of ~4 ASCII characters per token and
    ~1 CJK character per token.  No external tokenizer is needed.
    """
    if not text:
        return 0
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿" or "぀" <= ch <= "ヿ")
    ascii_chars = len(text) - cjk
    return cjk + max(1, ascii_chars // 4)
