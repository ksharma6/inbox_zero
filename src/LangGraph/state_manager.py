import pickle
from typing import Optional, Dict
from datetime import datetime
from src.models.agent import GmailAgentState


class StateManager:
    """Custom state manager for LangGraph workflow state serialization"""

    def __init__(self, storage_backend: str = "memory"):
        """
        Initialize state manager

        Args:
            storage_backend: "memory", "file", or "redis" (future enhancement)
        """
        self.storage_backend = storage_backend
        self._memory_store: Dict[str, bytes] = {}

    def save_state(self, state: GmailAgentState) -> None:
        """
        Save state with proper serialization

        Args:
            state: GmailAgentState object to save
        """
        if not isinstance(state, GmailAgentState):
            raise ValueError(f"Expected GmailAgentState, got {type(state)}")

        # Serialize with metadata for type safety
        serialized_data = {
            "type": "GmailAgentState",
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "data": state.model_dump(),  # Use Pydantic's built-in serialization
        }

        serialized_bytes = pickle.dumps(serialized_data)

        if self.storage_backend == "memory":
            self._memory_store[state.user_id] = serialized_bytes
        elif self.storage_backend == "file":
            self._save_to_file(state.user_id, serialized_bytes)
        # Future: Add Redis, database, etc.

    def load_state(self, user_id: str) -> Optional[GmailAgentState]:
        """
        Load state with proper deserialization

        Args:
            user_id: User ID to load state for

        Returns:
            GmailAgentState object or None if not found
        """
        try:
            if self.storage_backend == "memory":
                serialized_bytes = self._memory_store.get(user_id)
            elif self.storage_backend == "file":
                serialized_bytes = self._load_from_file(user_id)
            else:
                serialized_bytes = None

            if not serialized_bytes:
                return None

            # Deserialize with type checking
            serialized_data = pickle.loads(serialized_bytes)

            # Validate the serialized data
            if not isinstance(serialized_data, dict):
                raise ValueError("Invalid serialized state format")

            if serialized_data.get("type") != "GmailAgentState":
                raise ValueError(
                    f"Expected GmailAgentState, got {serialized_data.get('type')}"
                )

            # Reconstruct the state object
            state_data = serialized_data["data"]

            # Handle nested LangGraph state structure
            actual_state = extract_langgraph_state(state_data)
            return GmailAgentState(**actual_state)

        except Exception as e:
            print(f"Error loading state for user {user_id}: {e}")
            return None

    def delete_state(self, user_id: str) -> bool:
        """
        Delete state for a user

        Args:
            user_id: User ID to delete state for

        Returns:
            True if deleted, False if not found
        """
        try:
            if self.storage_backend == "memory":
                if user_id in self._memory_store:
                    del self._memory_store[user_id]
                    return True
            elif self.storage_backend == "file":
                return self._delete_file(user_id)
            return False
        except Exception as e:
            print(f"Error deleting state for user {user_id}: {e}")
            return False

    def list_states(self) -> list[str]:
        """List all user IDs with saved states"""
        if self.storage_backend == "memory":
            return list(self._memory_store.keys())
        elif self.storage_backend == "file":
            return self._list_files()
        return []


# Global state manager instance
state_manager = StateManager()


def extract_langgraph_state(state_dict: dict) -> dict:
    """
    Extract the actual state from LangGraph's nested dictionary structure

    Args:
        state_dict: Dictionary that might be nested from LangGraph

    Returns:
        Flat dictionary with the actual state data
    """
    if (
        isinstance(state_dict, dict)
        and len(state_dict) == 1
        and isinstance(next(iter(state_dict.values())), dict)
    ):
        # LangGraph nested structure: {'node_name': {'actual_state': 'data'}}
        return next(iter(state_dict.values()))
    else:
        # Direct state structure
        return state_dict


# helper functions for backward compatibility
def save_state_to_store(state: GmailAgentState) -> None:
    """Save state using the state manager"""
    state_manager.save_state(state)


def load_state_from_store(user_id: str) -> Optional[GmailAgentState]:
    """Load state using the state manager"""
    return state_manager.load_state(user_id)
