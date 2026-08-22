"""Agent registry."""

from __future__ import annotations

from .analysis import (
    CompetitionAgent,
    FinancialAgent,
    FutureAgent,
    MarketAgent,
    TechnologyAgent,
)
from .base import Agent, AgentResult, CandidateContext
from .critique import ContrarianAgent, DebateJudgeAgent, FactCheckerAgent
from .discovery import DiscoveryAgent, ThesisAgent, dedupe_key
from .quant import ManagementAgent, SignalAgent, ValuationAgent

#: Agents that contribute a dimension score, in execution order.
#: Signals and financials run first because later agents see their output;
#: the contrarian runs last so it can attack a fully formed case.
ANALYSIS_AGENTS: list[type[Agent]] = [
    SignalAgent,
    FinancialAgent,
    TechnologyAgent,
    MarketAgent,
    CompetitionAgent,
    ManagementAgent,
    FutureAgent,
    ValuationAgent,
    ContrarianAgent,
]

__all__ = [
    "Agent", "AgentResult", "CandidateContext",
    "TechnologyAgent", "MarketAgent", "CompetitionAgent", "FinancialAgent",
    "FutureAgent", "ContrarianAgent", "FactCheckerAgent", "DebateJudgeAgent",
    "DiscoveryAgent", "ThesisAgent", "ValuationAgent", "SignalAgent",
    "ManagementAgent", "ANALYSIS_AGENTS", "dedupe_key",
]
