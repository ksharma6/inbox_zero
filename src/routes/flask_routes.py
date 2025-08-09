from flask import request, jsonify
import uuid

from src.LangGraph.factory import get_workflow
from src.LangGraph.state_manager import (
    load_state_from_store,
    save_state_to_store,
    extract_langgraph_state,
)
from src.models.agent import GmailAgentState


def start_workflow():
    """
    Start the workflow for a new user.

    Requirements from .env:
        - TOKENS_PATH: Path to Gmail authentication tokens
        - SLACK_BOT_TOKEN: Slack bot token for integration
        - OPENAI_API_KEY: OpenAI API key for AI processing

    Required JSON body:
        - user_id: The ID of the Slack user or Slack channel

    Returns:
        json: A JSON response indicating the status of the workflow

    Example:
        {
            "status": "paused",
            "awaiting_approval": True
        }
    """
    user_id = request.json["user_id"]
    thread_id = str(uuid.uuid4())
    initial_state = GmailAgentState(user_id=user_id, thread_id=thread_id)

    workflow = get_workflow()

    # start the workflow execution as a generator
    result_gen = workflow.workflow.stream(initial_state)

    for state in result_gen:
        if isinstance(state, dict):
            # LangGraph returns nested dict structure, extract the actual state
            actual_state = extract_langgraph_state(state)
            state = GmailAgentState(**actual_state)

        if state.awaiting_approval:
            save_state_to_store(
                state
            )  # Save the current state to persistent storage so it can be resumed later
            return jsonify(
                {"status": "paused", "awaiting_approval": True}
            )  # Return HTTP response indicating workflow is paused
        final_state = state  # Store the current state as final_state (will be overwritten in each iteration)
    save_state_to_store(
        final_state
    )  # Save the final state after workflow completes all steps
    return jsonify(
        {"status": "completed", "workflow_complete": final_state.workflow_complete}
    )  # Return HTTP response with completion status


def resume_workflow():
    user_id = request.json["user_id"]
    action = request.json["action"]  # e.g., 'approve' or 'reject'
    state = load_state_from_store(user_id)

    # Ensure state is a GmailAgentState object
    if isinstance(state, dict):
        # LangGraph returns nested dict structure, extract the actual state
        actual_state = extract_langgraph_state(state)
        state = GmailAgentState(**actual_state)

    # Update state based on Slack action
    state.awaiting_approval = False

    if action == "approve_draft":
        # Keep the current draft and move to next
        state.current_draft_index += 1
        print(f"User approved draft {state.current_draft_index - 1}")
    elif action == "reject_draft":
        # Use the draft handler to reject the draft
        if state.draft_responses and state.current_draft_index < len(
            state.draft_responses
        ):
            draft_info = state.draft_responses[state.current_draft_index]
            # The DraftApprovalHandler will handle the rejection logic
            print(f"User rejected draft {state.current_draft_index}")
        state.current_draft_index += 1
    elif action == "save_draft":
        # Save the current draft
        print(f"User saved draft {state.current_draft_index}")
        # Optionally, you could add a saved_drafts list to track this
        # state.saved_drafts.append(state.draft_responses[state.current_draft_index])
        state.current_draft_index += 1
    else:
        # Unknown action, just continue
        # MAY NEED TO REMOVE THIS
        print(f"Unknown action: {action}, continuing workflow")
        state.current_draft_index += 1

    workflow = get_workflow()
    result_gen = workflow.workflow.stream(state)
    for new_state in result_gen:
        # Ensure new_state is a GmailAgentState object
        if isinstance(new_state, dict):
            # LangGraph returns nested dict structure, extract the actual state
            actual_state = extract_langgraph_state(new_state)
            new_state = GmailAgentState(**actual_state)
        final_state = new_state
    save_state_to_store(final_state)
    return jsonify(
        {"status": "resumed", "workflow_complete": final_state.workflow_complete}
    )


def resume_workflow_after_action(user_id, respond):
    """Helper function to resume workflow after draft action"""
    print(f"DEBUG: resume_workflow_after_action called for user: {user_id}")
    try:
        state = load_state_from_store(user_id)
        print(f"DEBUG: Loaded state: {state}")
        if state is None:
            print(f"DEBUG: No state found for user: {user_id}")
            return  # No workflow to resume

        # Ensure state is a GmailAgentState object
        if isinstance(state, dict):
            actual_state = extract_langgraph_state(state)
            state = GmailAgentState(**actual_state)
            print(f"DEBUG: Converted state to GmailAgentState")

        print(f"DEBUG: Current draft index: {state.current_draft_index}")
        print(
            f"DEBUG: Total drafts: {len(state.draft_responses) if state.draft_responses else 0}"
        )
        print(f"DEBUG: Awaiting approval: {state.awaiting_approval}")

        # Update state to continue workflow
        state.awaiting_approval = False
        state.current_draft_index += 1
        print(f"DEBUG: Updated draft index to: {state.current_draft_index}")

        # Resume the workflow
        workflow = get_workflow()
        print(f"DEBUG: Got workflow, about to stream")
        result_gen = workflow.workflow.stream(state)
        for new_state in result_gen:
            if isinstance(new_state, dict):
                actual_state = extract_langgraph_state(new_state)
                new_state = GmailAgentState(**actual_state)
            final_state = new_state
            print(
                f"DEBUG: Processing new state, awaiting_approval: {final_state.awaiting_approval}"
            )

            # Check if workflow paused again
            if final_state.awaiting_approval:
                save_state_to_store(final_state)
                print(f"DEBUG: Workflow paused again, saved state")
                respond(f"⏸️ Workflow paused. Waiting for next draft approval.")
                return

        save_state_to_store(final_state)
        print(
            f"DEBUG: Workflow completed, final state: {final_state.workflow_complete}"
        )
        if final_state.workflow_complete:
            respond(f"✅ Workflow completed successfully!")
        else:
            respond(f"✅ Workflow resumed and completed.")

    except Exception as e:
        print(f"Error resuming workflow: {e}")
        import traceback

        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        respond(f"❌ Error resuming workflow: {str(e)}")
