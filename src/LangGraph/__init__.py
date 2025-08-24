"""LangGraph package public API.

Expose the commonly used classes/functions for cleaner imports:

    from src.LangGraph import GmailAgent, GmailAgentState
"""

from .state_manager import StateManager
from .workflow import EmailProcessingWorkflow

__all__ = ["EmailProcessingWorkflow", "StateManager"]
