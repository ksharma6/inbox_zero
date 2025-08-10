from flask import Flask, request, jsonify
from slack_bolt import App as SlackApp

from src.utils.load_env import load_dotenv_helper

from src.slack.workflow_bridge import resume_workflow_after_action
from src.LangGraph.workflow_factory import get_workflow
from src.LangGraph.state_manager import (
    load_state_from_store,
    save_state_to_store,
    extract_langgraph_state,
)

from src.routes.flask_routes import register_flask_routes

from src.models.agent import GmailAgentState
import os
import uuid

app = Flask(__name__)
load_dotenv_helper(path="/Users/ksharma6/Documents/projects/inbox_zero/")

# Global slack app instance
slack_app = SlackApp(
    token=os.getenv("SLACK_BOT_TOKEN"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
)


# initialize workflow (singleton) and register routes that depend on it
workflow = get_workflow(slack_app)
register_flask_routes(app, workflow)


@slack_app.action("approve_draft")
def approve_draft_action(ack, body, respond):
    """Handle approve draft button click using DraftApprovalHandler"""
    print(f"DEBUG: approve_draft action received: {body}")
    print(
        f"DEBUG: Action value: {body.get('actions', [{}])[0].get('value', 'No value')}"
    )

    # Use the DraftApprovalHandler to handle the action
    # draft_handler = get_draft_handler(slack_app)
    print(f"DEBUG: About to call workflow.draft_handler.handle_approval_action")
    workflow.draft_handler.handle_approval_action(ack, body, respond)
    print(f"DEBUG: Finished workflow.draft_handler.handle_approval_action")

    # After handling the draft action, resume the workflow
    user_id = body["user"]["id"]
    print(f"DEBUG: About to resume workflow for user: {user_id}")
    resume_workflow_after_action(user_id, respond, workflow)
    print(f"DEBUG: Finished resume_workflow_after_action")


@slack_app.action("reject_draft")
def reject_draft_action(ack, body, respond):
    """Handle reject draft button click using DraftApprovalHandler"""
    print(f"DEBUG: reject_draft action received: {body}")

    # Use the shared workflow's DraftApprovalHandler to handle the action
    workflow.draft_handler.handle_approval_action(ack, body, respond)

    # After handling the draft action, resume the workflow
    user_id = body["user"]["id"]
    resume_workflow_after_action(user_id, respond, workflow)


@slack_app.action("save_draft")
def save_draft_action(ack, body, respond):
    """Handle save draft button click using DraftApprovalHandler"""
    print(f"DEBUG: save_draft action received: {body}")

    # Use the shared workflow's DraftApprovalHandler to handle the action
    workflow.draft_handler.handle_approval_action(ack, body, respond)

    # After handling the draft action, resume the workflow
    user_id = body["user"]["id"]
    resume_workflow_after_action(user_id, respond, workflow)


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


if __name__ == "__main__":
    app.run(port=5002, debug=True)
