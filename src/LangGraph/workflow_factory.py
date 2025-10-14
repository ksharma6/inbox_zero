import os

from openai import OpenAI
from slack_bolt import App

from src.gmail import GmailReader, GmailWriter
from src.langgraph.workflow import EmailProcessingWorkflow
from src.slack.draft_approval_handler import get_draft_handler


def get_workflow(slack_app: App):
    """Initialize EmailProcessingWorkflow with all dependencies outlined in .env file and return to user

    Returns:
        EmailProcessingWorkflow: A configured workflow instance

    Example:
        workflow = get_workflow(slack_app)
        workflow.run()
    """
    gmail_token = os.getenv("TOKENS_PATH")
    gmail_writer = GmailWriter(gmail_token)
    gmail_reader = GmailReader(gmail_token)

    draft_handler = get_draft_handler(slack_app)

    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return EmailProcessingWorkflow(
        gmail_reader=gmail_reader,
        gmail_writer=gmail_writer,
        draft_handler=draft_handler,
        openai_client=openai_client,
    )
