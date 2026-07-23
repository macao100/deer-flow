"""Observability configuration for MetricsCollector, AlertManager, and MetricsExporter."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MetricsConfig(BaseModel):
    """Configuration for the MetricsCollector ring buffer and export."""

    buffer_size: int = Field(default=10000, description="Maximum number of events held in memory", ge=100)
    export_path: str | None = Field(default=None, description="Directory for daily JSON exports; null = OS-specific default")
    rotation_days: int = Field(default=30, description="Number of days to retain exported metrics files", ge=1)


class AlertsConfig(BaseModel):
    """Thresholds and behaviour for the AlertManager."""

    latence_max_ms: float = Field(default=5000.0, description="P95 latency threshold per node (ms)", gt=0)
    error_rate_max: float = Field(default=0.05, description="Maximum tool-call error rate before alert", ge=0, le=1)
    token_budget_warn: int = Field(default=4000, description="Average input-token budget warning threshold", gt=0)
    rate_limit_seconds: int = Field(default=300, description="Minimum interval between repeated alerts of the same type", ge=30)


class PrometheusConfig(BaseModel):
    """Configuration for the Prometheus metrics endpoint."""

    enabled: bool = Field(default=False, description="Start a dedicated HTTP server for Prometheus scraping")
    port: int = Field(default=9090, description="Port for the Prometheus HTTP server", ge=1024, le=65535)


class ObservabilityConfig(BaseModel):
    """Top-level observability configuration.

    When ``enabled`` is ``False`` (the default), no observability
    components are created and the system is fully backward-compatible.
    """

    enabled: bool = Field(default=False, description="Master switch for the observability subsystem")
    metrics: MetricsConfig = Field(default_factory=MetricsConfig, description="Metrics collector configuration")
    alerts: AlertsConfig = Field(default_factory=AlertsConfig, description="Alert manager thresholds")
    prometheus: PrometheusConfig = Field(default_factory=PrometheusConfig, description="Prometheus endpoint configuration")
