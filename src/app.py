import os

from flask import Flask, request, jsonify
import pickle

from src.LangGraph.workflow import EmailProcessingWorkflow
from src.gmail.GmailReader import GmailReader
from src.gmail.GmailWriter import GmailWriter
from src.slack.DraftApprovalHandler import DraftApprovalHandler
from openai import OpenAI

# In-memory cache for demo purposes
WORKFLOW_STATE = {}

app = Flask(__name__)


@app.route("/start_workflow", methods=["POST"])
def start_workflow():
    user_id = request.json["user_id"]
    # Initialize dependencies
    gmail_reader = GmailReader(os.getenv("TOKENS_PATH"))
    gmail_writer = GmailWriter(os.getenv("TOKENS_PATH"))
    draft_handler = DraftApprovalHandler(os.getenv("SLACK_BOT_TOKEN"))
    openai_client = OpenAI()
    workflow = EmailProcessingWorkflow(
        gmail_reader, gmail_writer, draft_handler, openai_client
    )
    state = workflow.run(user_id)  # This should pause after sending the first draft
    WORKFLOW_STATE[user_id] = pickle.dumps(state)
    return jsonify({"status": "Workflow started and waiting for user action."})


# Add your /slack_event route here as well

if __name__ == "__main__":
    app.run(debug=True)
