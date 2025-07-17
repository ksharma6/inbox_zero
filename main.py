import os

from email import message_from_bytes
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from src.slack.actions import register_actions


import sys

sys.path.append("/Users/ksharma6/Documents/projects/inbox_zero")
from src.gmail.GmailWriter import GmailWriter
from src.slack.SlackGmailBridge import SlackGmailBridge
from src.slack.DraftApprovalHandler import DraftApprovalHandler

from src.utils.load_env import load_dotenv_helper

# load keys + paths
load_dotenv_helper(path="/Users/ksharma6/Documents/projects/inbox_zero/")
gmail_token = os.getenv("TOKENS_PATH")

slackbot_token = os.getenv("SLACK_BOT_TOKEN")
slackapp_token = os.getenv("SLACK_APP_TOKEN")


# Initialize tools
gmail_writer = GmailWriter(gmail_token)
app = App(token=slackbot_token)

# Initialize the bridge and approval handler
slack_gmail_bridge = SlackGmailBridge(gmail_writer, app)
draft_approval_handler = DraftApprovalHandler(gmail_writer, app)
register_actions(app, draft_approval_handler)


# Start your app
if __name__ == "__main__":
    # Example usage with the new approval system
    user_id = "U090QS5DDEE"

    # Create a draft
    draft = gmail_writer.create_draft(
        sender="kishen.codes@gmail.com",
        recipient="kishen.r.sharma@gmail.com",
        subject="test",
        message="some words on worshds. a few words",
        attachment_path="/Users/ksharma6/Documents/SMCH_Zoom_Background_The-Yogi.jpg",
    )

    if draft:
        # Send for approval with interactive buttons
        draft_id = draft_approval_handler.send_draft_for_approval(draft, user_id)

        if draft_id:
            print(f"Draft sent for approval with ID: {draft_id}")
        else:
            print("Failed to send draft for approval")

    handler = SocketModeHandler(app, slackapp_token)
    handler.start()
