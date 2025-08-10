from src.gmail.GmailReader import GmailReader
from src.gmail.GmailWriter import GmailWriter
from src.slack.DraftApprovalHandler import get_draft_handler
from src.LangGraph.workflow import EmailProcessingWorkflow
from openai import OpenAI
import os
from slack_bolt import App


def get_workflow(slack_app: App):
    """Initialize EmailProcessingWorkflow with all dependencies and return to user

    Returns:
        EmailProcessingWorkflow: A configured workflow instance with all dependencies
    """
    gmail_token = os.getenv("TOKENS_PATH")
    gmail_writer = GmailWriter(gmail_token)
    gmail_reader = GmailReader(gmail_token)

    # # Use the same draft handler instance
    draft_handler = get_draft_handler(slack_app)

    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return EmailProcessingWorkflow(
        gmail_reader=gmail_reader,
        gmail_writer=gmail_writer,
        draft_handler=draft_handler,
        openai_client=openai_client,
    )
