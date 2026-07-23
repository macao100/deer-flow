"""Distributed trace context for multi-agent tracing.

Provides a TraceContext that propagates trace_id and span_id through
agent delegation (subagent task tool), enabling proper parent-child
span relationships in Langfuse and other tracing backends.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TraceContext:
    """Immutable trace context propagated across agent boundaries.

    Stored in ``RunnableConfig.metadata`` so Langfuse's CallbackHandler
    can lift the ids onto the root trace span.

    IDs are short hex strings (not full UUIDs) for readability while
    remaining probabilistically unique.
    """

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    agent_name: str = "lead-agent"
    node_name: str | None = None
    model_name: str | None = None

    @staticmethod
    def from_config(
        config: dict[str, Any],
        *,
        agent_name: str = "lead-agent",
        node_name: str | None = None,
        model_name: str | None = None,
    ) -> TraceContext:
        """Extract or create a TraceContext from a RunnableConfig.

        If the config already contains a trace_id in its metadata, it is
        inherited. Otherwise a new root trace is created.
        """
        metadata: dict[str, Any] = config.get("metadata") or {}
        trace_id = metadata.get("deerflow_trace_id") or uuid.uuid4().hex[:16]
        span_id = uuid.uuid4().hex[:8]
        parent_span_id = metadata.get("deerflow_span_id")

        return TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            agent_name=agent_name,
            node_name=node_name,
            model_name=model_name,
        )

    def child(
        self,
        *,
        agent_name: str,
        node_name: str | None = None,
        model_name: str | None = None,
    ) -> TraceContext:
        """Create a child context with this span as the parent."""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=uuid.uuid4().hex[:8],
            parent_span_id=self.span_id,
            agent_name=agent_name,
            node_name=node_name,
            model_name=model_name,
        )

    def inject(self, config: dict[str, Any]) -> None:
        """Inject this trace context into a RunnableConfig's metadata.

        The metadata keys are chosen so that Langfuse's CallbackHandler
        can recognise and propagate them. Caller-supplied values (via
        setdefault) are never overwritten.
        """
        metadata: dict[str, Any] = config.setdefault("metadata", {})

        # Core trace identifiers
        metadata.setdefault("langfuse_trace_id", self.trace_id)
        metadata.setdefault("deerflow_trace_id", self.trace_id)
        metadata.setdefault("deerflow_span_id", self.span_id)
        if self.parent_span_id:
            metadata.setdefault("langfuse_parent_observation_id", self.parent_span_id)

        # Tags for filtering in Langfuse / LangSmith UIs
        tags: list[str] = metadata.setdefault("langfuse_tags", [])
        if not isinstance(tags, list):
            tags = list(tags)
            metadata["langfuse_tags"] = tags
        tag_set = set(tags)
        for tag in (f"agent:{self.agent_name}", f"node:{self.node_name}" if self.node_name else None):
            if tag and tag not in tag_set:
                tags.append(tag)
                tag_set.add(tag)

        metadata.setdefault("deerflow_agent_name", self.agent_name)
        if self.node_name:
            metadata.setdefault("deerflow_node_name", self.node_name)
        if self.model_name:
            metadata.setdefault("deerflow_model_name", self.model_name)
