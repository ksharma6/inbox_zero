from flask import Flask
from slack_bolt import App as SlackApp
from src.utils.load_env import load_dotenv_helper
from src.gmail.GmailWriter import GmailWriter
from src.routes.flask_routes import start_workflow, resume_workflow
from src.routes.slack_handlers import (
    approve_draft_action,
    reject_draft_action,
    save_draft_action,
    slack_events,
)
from src.slack.DraftApprovalHandler import DraftApprovalHandler

import os

app = Flask(__name__)
load_dotenv_helper(path="/Users/ksharma6/Documents/projects/inbox_zero/")

slack_app = SlackApp(
    token=os.getenv("SLACK_BOT_TOKEN"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
)


# Global draft handler instance reused across all Slack actions/routes
draft_handler = DraftApprovalHandler(
    gmail_writer=GmailWriter(os.getenv("TOKENS_PATH")),
    slack_app=slack_app,
)


@app.route("/start_workflow", methods=["POST"])
def start_workflow_route():
    return start_workflow()


@app.route("/resume_workflow", methods=["POST"])
def resume_workflow_route():
    return resume_workflow()


@slack_app.action("approve_draft")
def approve_draft_action_slack(ack, body, respond):
    approve_draft_action(ack, body, respond, draft_handler)


@slack_app.action("reject_draft")
def reject_draft_action_slack(ack, body, respond):
    reject_draft_action(ack, body, respond, draft_handler)


@slack_app.action("save_draft")
def save_draft_action_slack(ack, body, respond):
    save_draft_action(ack, body, respond, draft_handler)


@app.route("/slack/events", methods=["POST"])
def slack_events_route():
    return slack_events(draft_handler, slack_app)


if __name__ == "__main__":
    app.run(port=5002, debug=True)
