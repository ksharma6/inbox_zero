from src.LangGraph.state_manager import (
    load_state_from_store,
    save_state_to_store,
    extract_langgraph_state,
)
from src.models.agent import GmailAgentState


def resume_workflow_after_action(user_id: str, respond, workflow):

    state = load_state_from_store(user_id)
    if state is None:
        return
    if isinstance(state, dict):
        state = GmailAgentState(**extract_langgraph_state(state))
    state.awaiting_approval = False
    state.current_draft_index += 1

    result_gen = workflow.workflow.stream(state)
    final_state = state
    for new_state in result_gen:
        if isinstance(new_state, dict):
            new_state = GmailAgentState(**extract_langgraph_state(new_state))
        final_state = new_state

    save_state_to_store(final_state)
    if final_state.awaiting_approval:
        respond("⏸️ Workflow paused. Waiting for next draft approval.")
    elif final_state.workflow_complete:
        respond("✅ Workflow completed successfully!")
    else:
        respond("✅ Workflow resumed and completed.")
