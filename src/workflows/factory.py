import os

from openai import OpenAI
from slack_bolt import App as SlackApp
from src.gmail import GmailReader, GmailWriter
from src.slack_handlers.draft_approval_handler import DraftApprovalHandler
from src.workflows.workflow import EmailProcessingWorkflow


def get_workflow():
    """Initializes workflow object with dependencies in user environment .env file.

    Function creates and configures an EmailProcessingWorkflow instance with all
    necessary dependencies including GmailReader, GmailWriter, Slack integration, and OpenAI client.

    Environment Variables Required:
        - TOKENS_PATH: Path to Gmail authentication tokens
        - SLACK_BOT_TOKEN: Slack bot token for integration
        - OPENAI_API_KEY: OpenAI API key for AI processing

    Returns:
        EmailProcessingWorkflow: A configured workflow instance with all dependencies

    Example:
        workflow = get_workflow()
        workflow.run()
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
