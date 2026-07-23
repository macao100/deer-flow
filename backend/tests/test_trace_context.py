"""Tests for deerflow.tracing.observability.trace_context."""

from __future__ import annotations

from deerflow.tracing.observability.trace_context import TraceContext


class TestTraceContext:
    def test_root_context_creation(self):
        ctx = TraceContext.from_config({}, agent_name="lead-agent")
        assert len(ctx.trace_id) == 16
        assert len(ctx.span_id) == 8
        assert ctx.parent_span_id is None
        assert ctx.agent_name == "lead-agent"

    def test_child_propagation(self):
        parent = TraceContext.from_config({}, agent_name="lead-agent")
        child = parent.child(agent_name="general-purpose", node_name="subagent:general-purpose")
        assert child.trace_id == parent.trace_id  # trace is shared
        assert child.span_id != parent.span_id  # span is unique
        assert child.parent_span_id == parent.span_id  # parent link
        assert child.agent_name == "general-purpose"

    def test_grandchild_propagation(self):
        root = TraceContext.from_config({}, agent_name="lead-agent")
        child = root.child(agent_name="sub-1")
        grandchild = child.child(agent_name="sub-2")
        assert grandchild.trace_id == root.trace_id
        assert grandchild.parent_span_id == child.span_id
        assert grandchild.span_id != root.span_id
        assert grandchild.span_id != child.span_id

    def test_inject_adds_metadata_keys(self):
        ctx = TraceContext.from_config({}, agent_name="lead-agent", node_name="agent")
        config: dict = {}
        ctx.inject(config)
        metadata = config["metadata"]
        assert metadata["langfuse_trace_id"] == ctx.trace_id
        assert metadata["deerflow_trace_id"] == ctx.trace_id
        assert metadata["deerflow_span_id"] == ctx.span_id
        assert metadata["deerflow_agent_name"] == "lead-agent"
        assert metadata["deerflow_node_name"] == "agent"
        assert "agent:lead-agent" in metadata["langfuse_tags"]

    def test_inject_does_not_overwrite_existing(self):
        config: dict = {"metadata": {"deerflow_trace_id": "abc123", "langfuse_tags": ["custom:tag"]}}
        ctx = TraceContext.from_config(config, agent_name="override")
        ctx.inject(config)
        # Existing values preserved
        assert config["metadata"]["deerflow_trace_id"] == "abc123"
        assert "custom:tag" in config["metadata"]["langfuse_tags"]

    def test_from_config_inherits_trace_id(self):
        config: dict = {"metadata": {"deerflow_trace_id": "deadbeef12345678"}}
        ctx = TraceContext.from_config(config, agent_name="sub")
        assert ctx.trace_id == "deadbeef12345678"

    def test_id_uniqueness(self):
        # Create 100 contexts and ensure all span_ids are unique
        span_ids = set()
        for _ in range(100):
            ctx = TraceContext.from_config({}, agent_name="test")
            span_ids.add(ctx.span_id)
        assert len(span_ids) == 100

    def test_inject_with_parent_span(self):
        parent = TraceContext.from_config({}, agent_name="lead")
        child = parent.child(agent_name="sub")
        config: dict = {}
        child.inject(config)
        assert config["metadata"]["langfuse_parent_observation_id"] == parent.span_id

    def test_model_name_propagation(self):
        ctx = TraceContext.from_config({}, agent_name="lead", model_name="gpt-4")
        assert ctx.model_name == "gpt-4"
        child = ctx.child(agent_name="sub", model_name="gpt-4-mini")
        assert child.model_name == "gpt-4-mini"
