"""Complexity-based model routing — heuristic detection, no LLM involved.

This module is NOT a LangGraph middleware.  The lead-agent model is
instantiated at graph-construction time (``_make_lead_agent``), before
middleware hooks execute.  Changing the model after construction would
require tearing down and rebuilding the agent graph, which is not
practical inside a middleware hook.

Instead, this module provides a plain function that entry points
(``worker.py`` and ``client.py``) call **before** the agent factory,
so the correct model name lands in ``config["configurable"]["model_name"]``
before ``_make_lead_agent`` reads it.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deerflow.config.complexity_router_config import ComplexityRouterConfig

logger = logging.getLogger(__name__)

# Patterns that look like file paths or module references.
_FILE_PATH_PATTERN = re.compile(
    r"(?:^|\s|[`\"'])(?:[./]?[\w-]+/)+[\w.-]+\.\w{1,6}(?:[`\"']|$|\s|[:,])"
)


from deerflow.routing.token_estimation import estimate_tokens


_count_tokens_heuristic = estimate_tokens


def _count_file_references(text: str) -> int:
    """Count unique file-path-like substrings in *text*."""
    return len(set(m.group(0).strip("`\"' ") for m in _FILE_PATH_PATTERN.finditer(text)))


def route_by_complexity(
    *,
    user_message: str,
    current_model_name: str | None,
    thread_message_count: int,
    simple_model: str,
    complex_model: str,
    complex_thinking: bool,
    simple_thinking: bool,
    token_threshold: int,
    history_threshold: int,
    complex_keywords: list[str],
    min_criteria: int,
) -> tuple[str, bool] | None:
    """Determine whether a task is complex enough to promote to *complex_model*.

    Returns ``(model_name, thinking_enabled)`` if routing should happen,
    or ``None`` when the current model should be kept (either because the
    task is simple or the user explicitly chose a non-default model).

    Parameters
    ----------
    user_message:
        The latest user message text (empty string if none).
    current_model_name:
        Model name currently set on the config.  Used to detect user overrides.
    thread_message_count:
        Total number of messages in the thread so far.
    simple_model, complex_model, complex_thinking, simple_thinking:
        Values from :class:`ComplexityRouterConfig`.
    token_threshold, history_threshold, complex_keywords, min_criteria:
        Heuristic thresholds from :class:`ComplexityRouterConfig`.
    """
    # ── Override guard ──────────────────────────────────────────────────
    # If the caller explicitly requested a model that is NOT the simple
    # model, assume the user knows what they want and do not reroute.
    if current_model_name and current_model_name != simple_model:
        logger.debug(
            "Complexity router: skipping — user explicitly requested model=%r (simple=%r)",
            current_model_name,
            simple_model,
        )
        return None

    # ── Heuristic scoring ───────────────────────────────────────────────
    criteria_met = 0
    reasons: list[str] = []

    # 1. Long message?
    tokens = _count_tokens_heuristic(user_message)
    if tokens > token_threshold:
        criteria_met += 1
        reasons.append(f"long message ({tokens} tokens > {token_threshold})")

    # 2. Complex keywords?
    text_lower = user_message.lower()
    matched_keywords = [kw for kw in complex_keywords if kw in text_lower]
    if matched_keywords:
        criteria_met += 1
        reasons.append(f"keywords matched: {matched_keywords}")

    # 3. Long thread history?
    if thread_message_count > history_threshold:
        criteria_met += 1
        reasons.append(f"long history ({thread_message_count} msgs > {history_threshold})")

    # 4. Multiple file references?
    file_refs = _count_file_references(user_message)
    if file_refs >= 2:
        criteria_met += 1
        reasons.append(f"multiple file refs ({file_refs})")

    # ── Decision ────────────────────────────────────────────────────────
    if criteria_met >= min_criteria:
        logger.info(
            "Complexity router: promoting to %s (thinking=%s) — %d/%d criteria: %s",
            complex_model,
            complex_thinking,
            criteria_met,
            min_criteria,
            "; ".join(reasons),
        )
        return (complex_model, complex_thinking)

    # Simple task — ensure we're on the simple model with its default thinking.
    # This also resets the model if it was previously promoted.
    if current_model_name != simple_model or current_model_name is None:
        logger.debug(
            "Complexity router: keeping simple model %r (thinking=%s) — %d/%d criteria met",
            simple_model,
            simple_thinking,
            criteria_met,
            min_criteria,
        )
    return (simple_model, simple_thinking)
