"""LangChain callback adaptor for observability components.

Translates LangChain callback events (on_chain_start, on_llm_end, etc.)
into calls to MetricsCollector and injects TraceContext metadata onto
every span. This is the sole point of contact between the observability
system and the LangChain ecosystem.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from .metrics_collector import MetricsCollector, NodeLatency, TokenUsage, ToolCallResult

logger = logging.getLogger(__name__)

# Keys in serialized chain/tool dicts that carry the name
_CHAIN_NAME_KEYS = ("name", "id", "__class__")
_LLM_NAME_KEYS = ("name", "id", "ls_provider", "ls_model_name")


def _extract_name(serialized: dict[str, Any] | None, extra_keys: tuple[str, ...] = ()) -> str:
    """Best-effort name extraction from a LangChain serialized dict."""
    if not isinstance(serialized, dict):
        return "unknown"
    for key in (*extra_keys, *_CHAIN_NAME_KEYS):
        value = serialized.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "unknown"


def _extract_model_name(serialized: dict[str, Any] | None, kwargs: dict[str, Any] | None = None) -> str:
    """Extract model name from LLM serialized dict or invocation params."""
    if isinstance(serialized, dict):
        for key in ("ls_model_name", "name", "id"):
            value = serialized.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if isinstance(kwargs, dict):
        inv_params = kwargs.get("invocation_params") or {}
        if isinstance(inv_params, dict):
            model = inv_params.get("model") or inv_params.get("model_name")
            if isinstance(model, str) and model.strip():
                return model.strip()
    return "unknown"


class ObservabilityCallbacks(BaseCallbackHandler):
    """Adaptor: LangChain callbacks → MetricsCollector + TraceContext metadata.

    Attached at graph-invocation root via ``build_tracing_callbacks()`` so
    a single run produces one trace with all node/LLM/tool spans as children.

    Thread-safe: the internal timer dict is protected by a lock because
    LangChain can dispatch callbacks from multiple threads.
    """

    def __init__(self, metrics: MetricsCollector) -> None:
        self._metrics = metrics
        self._timers: dict[uuid.UUID, tuple[float, str, str, str | None]] = {}  # start_time, name, agent_name, model_name
        self._timer_lock = threading.RLock()

    # ── Chain (node) callbacks → latency ───────────────────────────────

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        chain_name = _extract_name(serialized)
        agent_name = (metadata or {}).get("deerflow_agent_name") or (metadata or {}).get("agent_name") or "lead-agent"
        model_name = (metadata or {}).get("deerflow_model_name") or (metadata or {}).get("model_name")
        with self._timer_lock:
            self._timers[run_id] = (time.monotonic(), chain_name, agent_name, model_name)

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        with self._timer_lock:
            timer_entry = self._timers.pop(run_id, None)
        if timer_entry is None:
            return
        start_time, chain_name, agent_name, _model_name = timer_entry
        duration_ms = (time.monotonic() - start_time) * 1000.0
        self._metrics.record_latency(
            NodeLatency(
                node_name=chain_name,
                agent_name=agent_name,
                start_time=start_time,
                end_time=time.monotonic(),
                duration_ms=duration_ms,
            )
        )

    # ── LLM callbacks → token usage ────────────────────────────────────

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        model_name = _extract_model_name(serialized, kwargs)
        with self._timer_lock:
            self._timers[run_id] = (time.monotonic(), model_name, "", None)

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        with self._timer_lock:
            timer_entry = self._timers.pop(run_id, None)
        if timer_entry is None:
            return
        _start_time, model_name, _agent, _mdl = timer_entry

        # Extract token counts from the LLM response
        input_tokens = 0
        output_tokens = 0
        try:
            if hasattr(response, "llm_output") and isinstance(response.llm_output, dict):
                usage = response.llm_output.get("token_usage") or {}
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
            if input_tokens == 0 and output_tokens == 0:
                # Fallback: try response_metadata (langchain_openai path)
                gen = getattr(response, "generations", None)
                if gen and len(gen) > 0 and len(gen[0]) > 0:
                    msg = gen[0][0]
                    resp_meta = getattr(msg, "response_metadata", {}) or {}
                    usage_info = resp_meta.get("token_usage") or {}
                    input_tokens = usage_info.get("prompt_tokens", 0)
                    output_tokens = usage_info.get("completion_tokens", 0)
        except Exception:
            logger.debug("Failed to extract token counts from LLM response", exc_info=True)

        if input_tokens > 0 or output_tokens > 0:
            self._metrics.record_tokens(
                TokenUsage(
                    model_name=model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    timestamp=time.monotonic(),
                )
            )

    # ── Tool callbacks → success/failure ───────────────────────────────

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        tool_name = _extract_name(serialized)
        with self._timer_lock:
            self._timers[run_id] = (time.monotonic(), tool_name, "", None)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        with self._timer_lock:
            timer_entry = self._timers.pop(run_id, None)
        if timer_entry is None:
            return
        start_time, tool_name, _agent, _mdl = timer_entry
        duration_ms = (time.monotonic() - start_time) * 1000.0

        # Determine success/failure from the output
        success = True
        error_msg: str | None = None
        if isinstance(output, str) and output.startswith("Error:"):
            success = False
            error_msg = output
        elif hasattr(output, "content") and isinstance(output.content, str):
            if output.content.startswith("Error:"):
                success = False
                error_msg = output.content

        self._metrics.record_tool_call(
            ToolCallResult(
                tool_name=tool_name,
                success=success,
                duration_ms=duration_ms,
                error=error_msg,
            )
        )
