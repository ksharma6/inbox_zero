from flask import jsonify, request
from slack_bolt import App as SlackApp

from src.slack.workflow_bridge import resume_workflow_after_action


def register_slack_routes(app, slack_app: SlackApp, workflow):
    @slack_app.action("approve_draft")
    def approve_draft_action(ack, body, respond):
        print(f"DEBUG: approve_draft action received: {body}")
        print(
            f"DEBUG: Action value: {body.get('actions', [{}])[0].get('value', 'No value')}"
        )

        # Handle action via shared workflow's DraftApprovalHandler
        workflow.draft_handler.handle_approval_action(ack, body, respond)

        # After handling the draft action, resume the workflow
        user_id = body["user"]["id"]
        resume_workflow_after_action(user_id, respond, workflow)

    @slack_app.action("reject_draft")
    def reject_draft_action(ack, body, respond):
        print(f"DEBUG: reject_draft action received: {body}")
        workflow.draft_handler.handle_approval_action(ack, body, respond)
        user_id = body["user"]["id"]
        resume_workflow_after_action(user_id, respond, workflow)

    @slack_app.action("save_draft")
    def save_draft_action(ack, body, respond):
        print(f"DEBUG: save_draft action received: {body}")
        workflow.draft_handler.handle_approval_action(ack, body, respond)
        user_id = body["user"]["id"]
        resume_workflow_after_action(user_id, respond, workflow)

    @app.route("/slack/events", methods=["POST"])
    def slack_events():
        print(f"DEBUG: Received Slack event request")
        print(f"DEBUG: Request method: {request.method}")
        print(f"DEBUG: Request headers: {dict(request.headers)}")
        print(f"DEBUG: Request URL: {request.url}")
        print(f"DEBUG: Request remote addr: {request.remote_addr}")
        print(
            f"DEBUG: Slack signing secret exists: {bool(app.config.get('SLACK_SIGNING_SECRET'))}"
        )
        print(f"DEBUG: Content-Type: {request.headers.get('Content-Type', 'Not set')}")
        print(f"DEBUG: User-Agent: {request.headers.get('User-Agent', 'Not set')}")

        content_type = request.headers.get("Content-Type", "")

        if "application/json" in content_type and request.json:
            print(f"DEBUG: Processing JSON request: {request.json}")
            if request.json.get("type") == "url_verification":
                challenge = request.json.get("challenge", "")
                return challenge

        if "application/x-www-form-urlencoded" in content_type and request.form:
            print(f"DEBUG: Processing form data: {dict(request.form)}")
            if "payload" in request.form:
                import json

                payload = json.loads(request.form["payload"])
                print(f"DEBUG: Parsed payload: {payload}")
                if "actions" in payload and payload["actions"]:
                    action = payload["actions"][0]
                    action_id = action.get("action_id")
                    print(f"DEBUG: Action ID: {action_id}")
                    if action_id == "approve_draft":
                        approve_draft_action(
                            lambda: None,
                            payload,
                            lambda text: print(f"Response: {text}"),
                        )
                        return jsonify({"response_action": "ack"})
                    elif action_id == "reject_draft":
                        reject_draft_action(
                            lambda: None,
                            payload,
                            lambda text: print(f"Response: {text}"),
                        )
                        return jsonify({"response_action": "ack"})
                    elif action_id == "save_draft":
                        save_draft_action(
                            lambda: None,
                            payload,
                            lambda text: print(f"Response: {text}"),
                        )
                        return jsonify({"response_action": "ack"})

        try:
            from slack_bolt.adapter.flask import SlackRequestHandler

            handler = SlackRequestHandler(slack_app)
            return handler.handle(request)
        except Exception as e:
            print(f"DEBUG: Error in slack_app handler: {e}")
            import traceback

            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/slack/actions", methods=["POST"])
    def slack_actions():
        print(f"DEBUG: Received Slack action request")
        print(f"DEBUG: Request method: {request.method}")
        print(f"DEBUG: Request headers: {dict(request.headers)}")
        print(f"DEBUG: Request URL: {request.url}")
        print(f"DEBUG: Content-Type: {request.headers.get('Content-Type', 'Not set')}")

        if request.form:
            print(f"DEBUG: Form data: {dict(request.form)}")
            payload = request.form.get("payload", "{}")
            print(f"DEBUG: Payload: {payload}")

        try:
            from slack_bolt.adapter.flask import SlackRequestHandler

            handler = SlackRequestHandler(slack_app)
            return handler.handle(request)
        except Exception as e:
            print(f"DEBUG: Error in slack_app handler for actions: {e}")
            import traceback

            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500
