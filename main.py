#!/usr/bin/env python3
"""
Example usage of the LangGraph Email Processing Workflow

This script demonstrates how to use the EmailProcessingWorkflow to:
1. Read unread emails from Gmail
2. Generate high-level summaries
3. Create draft responses
4. Send drafts to Slack for approval
"""

import os
from openai import OpenAI

from src.gmail.GmailReader import GmailReader
from src.gmail.GmailWriter import GmailWriter
from src.slack.DraftApprovalHandler import DraftApprovalHandler
from src.LangGraph.workflow import EmailProcessingWorkflow
from src.utils.load_env import load_dotenv_helper


def main():
    """Main function to run the email processing workflow"""

    # Load environment variables
    load_dotenv_helper()

    # Initialize OpenAI client
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Initialize Gmail components
    load_dotenv_helper(path="/Users/ksharma6/Documents/projects/inbox_zero/")
    gmail_token = os.getenv("TOKENS_PATH")

    gmail_writer = GmailWriter(gmail_token)
    gmail_reader = GmailReader(gmail_token)

    # Initialize Slack component
    from slack_bolt import App

    slack_app = App(token=os.getenv("SLACK_BOT_TOKEN"))

    draft_handler = DraftApprovalHandler(slack_app=slack_app, gmail_writer=gmail_writer)

    # Create the workflow
    workflow = EmailProcessingWorkflow(
        gmail_reader=gmail_reader,
        gmail_writer=gmail_writer,
        draft_handler=draft_handler,
        openai_client=openai_client,
    )

    # Run the workflow
    # Replace with actual Slack user ID and optional channel ID
    user_id = "U090QS5DDEE"  # Your Slack user ID
    # channel_id = "C090QS5DDEE"  # Optional: specific channel ID

    print("Starting email processing workflow...")

    try:
        result = workflow.run(user_id=user_id)

        print("\n=== Workflow Results ===")
        if isinstance(result, dict):
            # Old style, access as dict
            print(result.get("success"))
            print(result.get("summary"))
            print(result.get("drafts_created"))
            print(result.get("pending_approvals"))
            if result.get("success"):
                print("\n✅ Workflow completed successfully!")
        else:
            # New style, access as object
            print(result.workflow_complete and not result.error_message)
            print(result.final_summary)
            print(len(result.draft_responses))
            print(len(result.pending_approvals))
            if result.workflow_complete:
                print("\n✅ Workflow completed successfully!")

    except Exception as e:
        print(f"Error running workflow: {e}")


if __name__ == "__main__":
    main()

# import os
# import sys
# from email import message_from_bytes

# from slack_bolt import App
# from slack_bolt.adapter.socket_mode import SocketModeHandler

# from src.agent.OpenAIAgent import Agent
# from src.gmail.GmailReader import GmailReader
# from src.gmail.GmailWriter import GmailWriter
# from src.models.gmail import GmailToolFunction, GmailReaderToolFunction
# from src.models.agent import AgentSchema, ProcessRequestSchema
# from src.models.slack import SlackToolFunction
# from src.slack.DraftApprovalHandler import DraftApprovalHandler
# from src.slack.actions import register_actions
# from src.utils.load_env import load_dotenv_helper

# sys.path.append("/Users/ksharma6/Documents/projects/inbox_zero")


# # load keys + paths
# load_dotenv_helper(path="/Users/ksharma6/Documents/projects/inbox_zero/")
# gmail_token = os.getenv("TOKENS_PATH")

# slackbot_token = os.getenv("SLACK_BOT_TOKEN")
# slackapp_token = os.getenv("SLACK_APP_TOKEN")


# # Initialize tools
# gmail_writer = GmailWriter(gmail_token)
# app = App(token=slackbot_token)

# # Initialize the bridge and approval handler
# draft_approval_handler = DraftApprovalHandler(gmail_writer, app)
# gmail_writer = GmailWriter(gmail_token)
# gmail_reader = GmailReader(gmail_token)

# register_actions(app, draft_approval_handler)

# user_id = "U090QS5DDEE"

# read_and_create_draft = ("Please summarize the 5 most recent emails I have received. Be\
#     sure to include the subject of each email as well as sender.")

# cute_email = (
#     "Write an endearing message to my girlfriend Becky.\
# Start the email off with 'Dearest Becky' and sign off the email message with 'Only yours, \nBB'. Her email "
#     "is beckyhui3@gmail.com , be sure write in the subject "
#     "'If you're reading this, my agent is playing nice'' with a few kiss emojies. \
# Limit the email to 400 characters. The sender is kishen.codes@gmail.com. \
# Make sure you DM the draft on slack to user id U090QS5DDEE to review first before sending it out"
# )

# # Start your app
# if __name__ == "__main__":
#     # Example usage with the new approval system

#     available_tools = {
#         "gmail_writer": gmail_writer,
#         "gmail_reader": gmail_reader,
#         "draft_approval_handler": draft_approval_handler,
#     }

#     agent_schema = AgentSchema(
#         api_key=os.getenv("OPENAI_API_KEY") or "",
#         model="gpt-4",
#         available_tools=available_tools,
#     )

#     agent = Agent(agent_schema)


#     create_draft_schema = GmailToolFunction.generate_create_draft_schema()
#     read_emails_schema = GmailReaderToolFunction.generate_read_emails_schema()
#     send_draft_for_approval_schema = (
#         SlackToolFunction.generate_send_draft_for_approval_schema()
#     )

#     # Use a list of tool schemas instead of just one
#     tool_schemas = [create_draft_schema, read_emails_schema, send_draft_for_approval_schema]

#     request = ProcessRequestSchema(
#         user_prompt=read_and_create_draft,
#         llm_tool_schema=tool_schemas,  # Pass multiple schemas
#         system_message="You are a helpful AI agent that reads/summarizes emails and can send drafts to Slack for review."
#     )

#     agent.process_request(request)


#     handler = SocketModeHandler(app, slackapp_token)
#     handler.start()
