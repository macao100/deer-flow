"""Configuration for complexity-based model routing."""

from pydantic import BaseModel, Field, model_validator


class ComplexityRouterConfig(BaseModel):
    """Heuristic-based complexity detection that routes to the appropriate model.

    When enabled, the router analyzes the last user message BEFORE graph
    construction and selects between a "simple" (fast/cheap) model and a
    "complex" (powerful/expensive) model. The user's explicit ``model_name``
    override always wins — the router only fires when no model was requested.
    """

    enabled: bool = Field(
        default=False,
        description="Enable complexity-based model routing",
    )
    simple_model: str = Field(
        default="deepseek-v4-flash",
        description="Model used for simple/routine tasks (default: fast & cheap)",
    )
    complex_model: str = Field(
        default="deepseek-v4-pro",
        description="Model used for complex tasks (default: powerful, thinking enabled)",
    )
    complex_thinking: bool = Field(
        default=True,
        description="Enable extended thinking when routing to the complex model",
    )
    simple_thinking: bool = Field(
        default=False,
        description="Enable extended thinking when routing to the simple model",
    )
    # ── Heuristic thresholds ──────────────────────────────────────────
    token_threshold: int = Field(
        default=500,
        ge=1,
        description="Message length (characters) above which complexity is suspected",
    )
    history_threshold: int = Field(
        default=10,
        ge=1,
        description="Thread message count above which complexity is suspected",
    )
    # Keywords that signal a complex task (case-insensitive, matched as substrings)
    complex_keywords: list[str] = Field(
        default_factory=lambda: [
            "architecture",
            "refactor",
            "design",
            "analyser",
            "analyze",
            "pourquoi",
            "explique",
            "explain",
            "compare",
            "plan",
            "stratégie",
            "strategy",
            "debug",
            "diagnostiquer",
            "optimiser",
            "optimize",
            "sécurité",
            "security",
            "audit",
            "migrer",
            "migrate",
        ],
        description="Keywords that signal a complex task (matched case-insensitive as substrings)",
    )
    # Minimum criteria that must be met for a task to be considered complex
    min_criteria: int = Field(
        default=2,
        ge=1,
        le=4,
        description="Minimum number of complexity signals required to promote to complex model",
    )

    @model_validator(mode="after")
    def _validate_models(self) -> "ComplexityRouterConfig":
        if self.enabled and self.simple_model == self.complex_model:
            raise ValueError("simple_model and complex_model must differ when routing is enabled")
        return self
