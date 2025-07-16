import os
from typing import Dict, Optional
from slack_bolt import App
from slack_sdk.errors import SlackApiError

from src.gmail.GmailWriter import GmailWriter


class SlackGmailBridge:
    """
    Bridge class that handles communication between Gmail and Slack.
    This maintains separation of concerns while providing integration functionality.
    """

    def __init__(self, gmail_writer: GmailWriter, slack_app: App):
        """
        Initialize the bridge with Gmail and Slack instances.

        Args:
            gmail_writer: Initialized GmailWriter instance
            slack_app: Initialized Slack App instance
        """
        self.gmail_writer = gmail_writer
        self.slack_app = slack_app

    def send_draft_to_slack(
        self, draft: Dict, user_id: str, channel_id: Optional[str] = None
    ) -> bool:
        """
        Send a Gmail draft preview to Slack for review.

        Args:
            draft: Gmail draft dictionary from create_draft()
            user_id: Slack user ID to send the message to
            channel_id: Optional channel ID (if not provided, sends DM)

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            # Decode the draft for Slack display
            decoded_draft = self.gmail_writer.send_draft_slack(draft)

            # Format the message for Slack
            message = self._format_draft_for_slack(decoded_draft)

            # Send to Slack
            target = channel_id if channel_id else user_id
            self.slack_app.client.chat_postMessage(channel=target, text=message)

            return True

        except SlackApiError as e:
            print(f"Error sending draft to Slack: {e.response['error']}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

    def _format_draft_for_slack(self, decoded_draft: Dict) -> str:
        """
        Format decoded draft data for Slack display.

        Args:
            decoded_draft: Decoded draft dictionary from send_draft_slack()

        Returns:
            str: Formatted message for Slack
        """
        lines = [
            "*Email Draft Preview*",
            f"*From:* {decoded_draft.get('sender', 'N/A')}",
            f"*To:* {decoded_draft.get('recipient', 'N/A')}",
            f"*Subject:* {decoded_draft.get('subject', 'N/A')}",
            f"*Body:* {decoded_draft.get('body', 'N/A')}",
        ]

        # Add attachments if any
        attachments = decoded_draft.get("attachment", [])
        if attachments:
            attachment_list = ", ".join(attachments)
            lines.append(f"*Attachments:* {attachment_list}")

        return "\n".join(lines)

    def create_and_preview_draft(
        self,
        sender: str,
        recipient: str,
        subject: str,
        message: str,
        user_id: str,
        attachment_path: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Create a Gmail draft and immediately send preview to Slack.

        Args:
            sender: Email sender address
            recipient: Email recipient address
            subject: Email subject
            message: Email body
            user_id: Slack user ID for preview
            attachment_path: Optional attachment path

        Returns:
            Optional[Dict]: The created draft dictionary, or None if creation failed
        """
        # Create the draft
        draft = self.gmail_writer.create_draft(
            sender=sender,
            recipient=recipient,
            subject=subject,
            message=message,
            attachment_path=attachment_path,
        )

        if draft:
            # Send preview to Slack
            self.send_draft_to_slack(draft, user_id)

        return draft
