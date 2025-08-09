from slack_bolt import App as SlackApp

from src.LangGraph.workflow import EmailProcessingWorkflow
from src.gmail.GmailReader import GmailReader
from src.gmail.GmailWriter import GmailWriter
from src.slack.DraftApprovalHandler import DraftApprovalHandler
from openai import OpenAI
import os


def get_workflow():
    """Initializes workflow object with dependencies in user environment

    Function creates and configures an EmailProcessingWorkflow instance with all
    necessary dependencies including Gmail reader/writer, Slack integration, and OpenAI client.
    It automatically loads configuration from environment variables.

    Environment Variables Required:
        - TOKENS_PATH: Path to Gmail authentication tokens
        - SLACK_BOT_TOKEN: Slack bot token for integration
        - OPENAI_API_KEY: OpenAI API key for AI processing

    Returns:
        EmailProcessingWorkflow: A configured workflow instance with all dependencies
    """
    gmail_token = os.getenv("TOKENS_PATH")
    gmail_writer = GmailWriter(gmail_token)
    gmail_reader = GmailReader(gmail_token)

    slack_app = SlackApp(token=os.getenv("SLACK_BOT_TOKEN"))
    draft_handler = DraftApprovalHandler(slack_app=slack_app, gmail_writer=gmail_writer)
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    return EmailProcessingWorkflow(
        gmail_reader=gmail_reader,
        gmail_writer=gmail_writer,
        draft_handler=draft_handler,
        openai_client=openai_client,
    )
