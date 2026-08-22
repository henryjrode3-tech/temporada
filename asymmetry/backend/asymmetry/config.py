"""Configuration. Secrets come from the environment, never from source."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_prefix="ASYMMETRY_", extra="ignore"
    )

    # ---- Database -------------------------------------------------------
    database_url: str = "postgresql+psycopg2://asymmetry:asymmetry@localhost:5432/asymmetry"
    sql_echo: bool = False

    # ---- LLM ------------------------------------------------------------
    #: Read from the conventional variable name so an existing Anthropic setup
    #: works without renaming anything.
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")

    #: Tiered models (section 43). Discovery and screening run on the cheap
    #: model; only candidates that survive earn the expensive one.
    model_cheap: str = "claude-haiku-4-5-20251001"
    model_deep: str = "claude-sonnet-5"
    model_judge: str = "claude-opus-5"

    #: Hard ceiling per pipeline run. The pipeline aborts rather than
    #: overspending; an unbounded agent loop is a financial risk, not just a bug.
    max_cost_per_run_usd: float = 5.0
    max_llm_calls_per_run: int = 400
    llm_cache_enabled: bool = True
    llm_timeout_seconds: int = 90
    llm_max_retries: int = 3

    # ---- Pipeline -------------------------------------------------------
    stage1_max_candidates: int = 500
    stage2_max_candidates: int = 60
    stage3_max_candidates: int = 12
    default_horizon_years: float = 10.0
    required_return: float = 0.15

    # ---- API ------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    api_key: str = ""          # when set, required on mutating endpoints
    rate_limit_per_minute: int = 120

    # ---- Sources --------------------------------------------------------
    #: Identifies the client to public APIs. The SEC in particular requires a
    #: contactable user agent and will reject requests without one.
    user_agent: str = "AsymmetryEngine/0.1 (research; contact: set ASYMMETRY_USER_AGENT)"
    use_mock_sources: bool = True
    source_timeout_seconds: int = 20

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_available(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def llm_mode(self) -> str:
        """Which reasoner is in use - surfaced in the UI so results are never
        mistaken for live model output when they are deterministic stand-ins."""
        return "anthropic" if self.llm_available else "heuristic (no API key)"


@lru_cache
def get_settings() -> Settings:
    return Settings()
