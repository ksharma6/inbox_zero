"""LangGraph package public API.

Expose the commonly used classes/functions for cleaner imports:

    from src.workflows import GmailAgent, GmailAgentState
"""

from .state_manager import StateManager
from .workflow import EmailProcessingWorkflow

__all__ = ["EmailProcessingWorkflow", "StateManager"]
