import os
import sys
from email import message_from_bytes

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from src.agent.OpenAIAgent import Agent
from src.gmail.GmailReader import GmailReader
from src.gmail.GmailWriter import GmailWriter
from src.models.agent import AgentSchema, ProcessRequestSchema
from src.models.slack import SlackToolFunction
from src.slack.DraftApprovalHandler import DraftApprovalHandler
from src.slack.actions import register_actions
from src.utils.load_env import load_dotenv_helper

sys.path.append("/Users/ksharma6/Documents/projects/inbox_zero")


# load keys + paths
load_dotenv_helper(path="/Users/ksharma6/Documents/projects/inbox_zero/")
gmail_token = os.getenv("TOKENS_PATH")

slackbot_token = os.getenv("SLACK_BOT_TOKEN")
slackapp_token = os.getenv("SLACK_APP_TOKEN")


# Initialize tools
gmail_writer = GmailWriter(gmail_token)
app = App(token=slackbot_token)

# Initialize the bridge and approval handler
draft_approval_handler = DraftApprovalHandler(gmail_writer, app)
gmail_writer = GmailWriter(gmail_token)
gmail_reader = GmailReader(gmail_token)

register_actions(app, draft_approval_handler)

user_id = "U090QS5DDEE"

cute_email = (
    "Write an endearing message to my girlfriend Becky.\
Start the email off with 'Dearest Becky' and sign off the email message with 'Only yours, \nBB'. Her email "
    "is beckyhui3@gmail.com , be sure write in the subject "
    "'If you're reading this, my agent is playing nice'' with a few kiss emojies. \
Limit the email to 400 characters. The sender is kishen.codes@gmail.com. \
Make sure you DM the draft on slack to user id U090QS5DDEE to review first before sending it out"
)

# Start your app
if __name__ == "__main__":
    # Example usage with the new approval system

    available_tools = {
        "gmail_writer": gmail_writer,
        "gmail_reader": gmail_reader,  # if you have this
        # "slack_gmail_bridge": slack_gmail_bridge,
        "draft_approval_handler": draft_approval_handler,
    }

    agent_schema = AgentSchema(
        api_key=os.getenv("OPENAI_API_KEY") or "",
        model="gpt-4",
        available_tools=available_tools,
    )

    agent = Agent(agent_schema)

    # Create comprehensive tool schemas for both Gmail and Slack functions
    from src.models.toolfunction import ToolFunction, ToolParams, ParamProperties
    from src.models.gmail import GmailToolFunction

    create_draft_schema = GmailToolFunction.generate_create_draft_schema()
    # send_draft_to_slack_schema = SlackToolFunction.generate_send_draft_to_slack_schema()
    send_draft_for_approval_schema = (
        SlackToolFunction.generate_send_draft_for_approval_schema()
    )

    # Use a list of tool schemas instead of just one
    tool_schemas = [create_draft_schema, send_draft_for_approval_schema]

    request = ProcessRequestSchema(
        user_prompt=cute_email,
        llm_tool_schema=tool_schemas,  # Pass multiple schemas
        system_message="You are a helpful AI agent that writes romantic emails and can send drafts to Slack for review. IMPORTANT: Always follow this workflow: 1) First call create_draft() to create the email, 2) Then call send_draft_for_approval() with the draft object returned from step 1. Never call Slack functions without first creating a draft.",
    )

    agent.process_request(request)
    # # Create a draft
    # draft = gmail_writer.create_draft(
    #     sender="kishen.codes@gmail.com",
    #     recipient="kishen.r.sharma@gmail.com",
    #     subject="test",
    #     message="some words on worshds. a few words",
    #     attachment_path="/Users/ksharma6/Documents/SMCH_Zoom_Background_The-Yogi.jpg",
    # )

    # if draft:
    #     # Send for approval with interactive buttons
    #     draft_id = draft_approval_handler.send_draft_for_approval(draft, user_id)

    #     if draft_id:
    #         print(f"Draft sent for approval with ID: {draft_id}")
    #     else:
    #         print("Failed to send draft for approval")

    handler = SocketModeHandler(app, slackapp_token)
    handler.start()
