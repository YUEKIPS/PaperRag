"""LangGraph agentic orchestrator (decide → retrieve → grade → rewrite → generate).

decide turns a follow-up into a standalone working query when session history is present.
"""

from src.agent.run import AgenticResult, run_agentic_query

__all__ = ["AgenticResult", "run_agentic_query"]
