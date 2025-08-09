from flask import Flask, request, jsonify
from slack_bolt import App as SlackApp

from src.utils.load_env import load_dotenv_helper
from src.gmail.GmailReader import GmailReader
from src.gmail.GmailWriter import GmailWriter
from src.slack.DraftApprovalHandler import DraftApprovalHandler, get_draft_handler
from src.LangGraph.workflow import EmailProcessingWorkflow
from src.LangGraph.state_manager import (
    load_state_from_store,
    save_state_to_store,
    extract_langgraph_state,
)
from src.models.agent import GmailAgentState
from openai import OpenAI
import os
import uuid

app = Flask(__name__)
load_dotenv_helper(path="/Users/ksharma6/Documents/projects/inbox_zero/")

# Global slack app instance
slack_app = SlackApp(
    token=os.getenv("SLACK_BOT_TOKEN"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
)

# Global draft handler instance
draft_handler = get_draft_handler(slack_app)


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


def get_workflow():
    """Initialize EmailProcessingWorkflow with all dependencies and return to user

    Returns:
        EmailProcessingWorkflow: A configured workflow instance with all dependencies
    """
    gmail_token = os.getenv("TOKENS_PATH")
    gmail_writer = GmailWriter(gmail_token)
    gmail_reader = GmailReader(gmail_token)

    # # Use the same draft handler instance
    # draft_handler = get_draft_handler(slack_app)

    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return EmailProcessingWorkflow(
        gmail_reader=gmail_reader,
        gmail_writer=gmail_writer,
        draft_handler=draft_handler,
        openai_client=openai_client,
    )


@app.route("/start_workflow", methods=["POST"])
def start_workflow():
    # Extract user_id from the POST request JSON body
    user_id = request.json["user_id"]

    # Get a configured workflow instance with all dependencies (GMail reader, writer, draft handler, openai client)
    workflow = get_workflow()
    # Generate a unique thread ID for this workflow run
    thread_id = str(uuid.uuid4())
    # Create initial workflow state with user and thread IDs
    initial_state = GmailAgentState(user_id=user_id, thread_id=thread_id)
    # Start the workflow execution as a generator, yielding states at each step
    result_gen = workflow.workflow.stream(initial_state)
    # Iterate through each state yielded by the workflow
    for state in result_gen:

        # Handle both dict and GmailAgentState objects
        if isinstance(state, dict):
            # LangGraph returns nested dict structure, extract the actual state
            actual_state = extract_langgraph_state(state)
            state = GmailAgentState(**actual_state)

        # Check for pause condition
        if state.awaiting_approval:  # Check if workflow is waiting for human approval
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


@app.route("/resume_workflow", methods=["POST"])
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


@slack_app.action("approve_draft")
def approve_draft_action(ack, body, respond):
    """Handle approve draft button click using DraftApprovalHandler"""
    print(f"DEBUG: approve_draft action received: {body}")
    print(
        f"DEBUG: Action value: {body.get('actions', [{}])[0].get('value', 'No value')}"
    )

    # Use the DraftApprovalHandler to handle the action
    # draft_handler = get_draft_handler(slack_app)
    print(f"DEBUG: About to call draft_handler.handle_approval_action")
    draft_handler.handle_approval_action(ack, body, respond)
    print(f"DEBUG: Finished draft_handler.handle_approval_action")

    # After handling the draft action, resume the workflow
    user_id = body["user"]["id"]
    print(f"DEBUG: About to resume workflow for user: {user_id}")
    resume_workflow_after_action(user_id, respond)
    print(f"DEBUG: Finished resume_workflow_after_action")


@slack_app.action("reject_draft")
def reject_draft_action(ack, body, respond):
    """Handle reject draft button click using DraftApprovalHandler"""
    print(f"DEBUG: reject_draft action received: {body}")

    # Use the DraftApprovalHandler to handle the action
    # draft_handler = get_draft_handler(slack_app)
    draft_handler.handle_approval_action(ack, body, respond)

    # After handling the draft action, resume the workflow
    user_id = body["user"]["id"]
    resume_workflow_after_action(user_id, respond)


@slack_app.action("save_draft")
def save_draft_action(ack, body, respond):
    """Handle save draft button click using DraftApprovalHandler"""
    print(f"DEBUG: save_draft action received: {body}")

    # Use the DraftApprovalHandler to handle the action
    # draft_handler = get_draft_handler(slack_app )
    draft_handler.handle_approval_action(ack, body, respond)

    # After handling the draft action, resume the workflow
    user_id = body["user"]["id"]
    resume_workflow_after_action(user_id, respond)


@app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle all Slack events including interactive components"""
    print(f"DEBUG: Received Slack event request")
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: Request headers: {dict(request.headers)}")
    print(f"DEBUG: Request URL: {request.url}")
    print(f"DEBUG: Request remote addr: {request.remote_addr}")
    print(
        f"DEBUG: Slack signing secret exists: {bool(os.getenv('SLACK_SIGNING_SECRET'))}"
    )
    print(f"DEBUG: Content-Type: {request.headers.get('Content-Type', 'Not set')}")
    print(f"DEBUG: User-Agent: {request.headers.get('User-Agent', 'Not set')}")

    # Handle different content types
    content_type = request.headers.get("Content-Type", "")

    # Handle Slack URL verification challenge (JSON)
    if "application/json" in content_type and request.json:
        print(f"DEBUG: Processing JSON request: {request.json}")
        if request.json.get("type") == "url_verification":
            challenge = request.json.get("challenge", "")
            print(f"DEBUG: Handling URL verification challenge")
            print(f"DEBUG: Challenge value: {challenge}")
            print(f"DEBUG: Returning challenge response")
            return challenge

    # Handle form data (interactive components)
    if "application/x-www-form-urlencoded" in content_type and request.form:
        print(f"DEBUG: Processing form data: {dict(request.form)}")
        if "payload" in request.form:
            import json

            payload = json.loads(request.form["payload"])
            print(f"DEBUG: Parsed payload: {payload}")

            # Handle interactive components manually
            if "actions" in payload and payload["actions"]:
                action = payload["actions"][0]
                action_id = action.get("action_id")
                print(f"DEBUG: Action ID: {action_id}")

                # Call the appropriate action handler directly
                if action_id == "approve_draft":
                    print(f"DEBUG: Calling approve_draft_action")
                    approve_draft_action(
                        lambda: None, payload, lambda text: print(f"Response: {text}")
                    )
                    return jsonify({"response_action": "ack"})
                elif action_id == "reject_draft":
                    print(f"DEBUG: Calling reject_draft_action")
                    reject_draft_action(
                        lambda: None, payload, lambda text: print(f"Response: {text}")
                    )
                    return jsonify({"response_action": "ack"})
                elif action_id == "save_draft":
                    print(f"DEBUG: Calling save_draft_action")
                    save_draft_action(
                        lambda: None, payload, lambda text: print(f"Response: {text}")
                    )
                    return jsonify({"response_action": "ack"})

    # Handle other Slack events (including interactive components)
    try:
        print(f"DEBUG: About to call slack_app handler")
        from slack_bolt.adapter.flask import SlackRequestHandler

        handler = SlackRequestHandler(slack_app)
        result = handler.handle(request)
        print(f"DEBUG: Slack app handler result: {result}")
        return result
    except Exception as e:
        print(f"DEBUG: Error in slack_app handler: {e}")
        print(f"DEBUG: Exception type: {type(e)}")
        import traceback

        print(f"DEBUG: Full traceback: {traceback.format_exc()}")

        # Try manual handling as fallback
        try:
            print(f"DEBUG: Trying manual handling as fallback")
            if request.form and "payload" in request.form:
                import json

                payload = json.loads(request.form["payload"])
                print(f"DEBUG: Parsed payload: {payload}")

                # Extract action details
                if "actions" in payload and payload["actions"]:
                    action = payload["actions"][0]
                    action_id = action.get("action_id")
                    print(f"DEBUG: Action ID: {action_id}")

                    # Call the appropriate action handler directly
                    if action_id == "approve_draft":
                        from slack_bolt.context.ack import Ack
                        from slack_bolt.context.say import Say

                        def ack():
                            return jsonify({"response_action": "ack"})

                        def respond(text):
                            return jsonify({"text": text})

                        approve_draft_action(ack, payload, respond)
                        return jsonify({"response_action": "ack"})

            return jsonify({"error": "Manual handling failed"}), 500
        except Exception as manual_error:
            print(f"DEBUG: Manual handling also failed: {manual_error}")
            return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def root():
    return jsonify(
        {
            "message": "Flask app is running",
            "status": "ok",
            "timestamp": "2024-01-01T00:00:00Z",
        }
    )


@app.route("/test", methods=["GET"])
def test():
    return jsonify(
        {
            "status": "ok",
            "slack_token_exists": bool(os.getenv("SLACK_BOT_TOKEN")),
            "slack_token_length": len(os.getenv("SLACK_BOT_TOKEN", "")),
            "slack_signing_secret_exists": bool(os.getenv("SLACK_SIGNING_SECRET")),
            "app_running": True,
        }
    )


@app.route("/slack/actions", methods=["POST"])
def slack_actions():
    """Handle Slack interactive components (button clicks)"""
    print(f"DEBUG: Received Slack action request")
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: Request headers: {dict(request.headers)}")
    print(f"DEBUG: Request URL: {request.url}")
    print(f"DEBUG: Content-Type: {request.headers.get('Content-Type', 'Not set')}")
    print(
        f"DEBUG: Slack signing secret exists: {bool(os.getenv('SLACK_SIGNING_SECRET'))}"
    )
    print(
        f"DEBUG: Slack signing secret length: {len(os.getenv('SLACK_SIGNING_SECRET', ''))}"
    )
    print(f"DEBUG: Slack bot token exists: {bool(os.getenv('SLACK_BOT_TOKEN'))}")
    print(f"DEBUG: Slack bot token length: {len(os.getenv('SLACK_BOT_TOKEN', ''))}")

    # Print form data if it exists
    if request.form:
        print(f"DEBUG: Form data: {dict(request.form)}")
        payload = request.form.get("payload", "{}")
        print(f"DEBUG: Payload: {payload}")

    # Handle Slack interactive components using the same handler
    try:
        print(f"DEBUG: About to call slack_app handler for actions")
        from slack_bolt.adapter.flask import SlackRequestHandler

        # Create handler with signature verification disabled for debugging
        handler = SlackRequestHandler(slack_app)
        result = handler.handle(request)
        print(f"DEBUG: Slack app handler result for actions: {result}")
        return result
    except Exception as e:
        print(f"DEBUG: Error in slack_app handler for actions: {e}")
        print(f"DEBUG: Exception type: {type(e)}")
        import traceback

        print(f"DEBUG: Full traceback: {traceback.format_exc()}")

        # Try manual handling as fallback
        try:
            print(f"DEBUG: Trying manual handling as fallback")
            if request.form and "payload" in request.form:
                import json

                payload = json.loads(request.form["payload"])
                print(f"DEBUG: Parsed payload: {payload}")

                # Extract action details
                if "actions" in payload and payload["actions"]:
                    action = payload["actions"][0]
                    action_id = action.get("action_id")
                    print(f"DEBUG: Action ID: {action_id}")

                    # Call the appropriate action handler directly
                    if action_id == "approve_draft":
                        from slack_bolt.context.ack import Ack
                        from slack_bolt.context.say import Say

                        def ack():
                            return jsonify({"response_action": "ack"})

                        def respond(text):
                            return jsonify({"text": text})

                        approve_draft_action(ack, payload, respond)
                        return jsonify({"response_action": "ack"})

            return jsonify({"error": "Manual handling failed"}), 500
        except Exception as manual_error:
            print(f"DEBUG: Manual handling also failed: {manual_error}")
            return jsonify({"error": str(e)}), 500


@app.route("/slack/health", methods=["GET"])
def slack_health():
    """Health check endpoint for Slack integration"""
    return jsonify(
        {
            "status": "healthy",
            "slack_token_exists": bool(os.getenv("SLACK_BOT_TOKEN")),
            "slack_token_length": len(os.getenv("SLACK_BOT_TOKEN", "")),
            "slack_token_prefix": (
                os.getenv("SLACK_BOT_TOKEN", "")[:10] + "..."
                if os.getenv("SLACK_BOT_TOKEN")
                else "None"
            ),
            "slack_signing_secret_exists": bool(os.getenv("SLACK_SIGNING_SECRET")),
            "slack_signing_secret_length": len(os.getenv("SLACK_SIGNING_SECRET", "")),
            "slack_signing_secret_prefix": (
                os.getenv("SLACK_SIGNING_SECRET", "")[:10] + "..."
                if os.getenv("SLACK_SIGNING_SECRET")
                else "None"
            ),
            "endpoints": {
                "events": "/slack/events",
                "actions": "/slack/actions",
                "start_workflow": "/start_workflow",
                "resume_workflow": "/resume_workflow",
                "health": "/slack/health",
            },
        }
    )


if __name__ == "__main__":
    app.run(port=5002, debug=True)
