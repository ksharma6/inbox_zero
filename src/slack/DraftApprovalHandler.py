import os
import json
import uuid
from typing import Dict, Optional, Callable
from datetime import datetime, timedelta

from slack_bolt import App
from slack_sdk.errors import SlackApiError
from slack_bolt.context.ack import Ack
from slack_bolt.context.say import Say

from src.gmail.GmailWriter import GmailWriter


class DraftApprovalHandler:
    """
    Handles email draft approvals through Slack interactive components.
    Manages draft storage, approval/rejection workflows, and user notifications.
    """

    def __init__(self, gmail_writer: GmailWriter, slack_app: App):
        """
        Initialize the draft approval handler.

        Args:
            gmail_writer: Initialized GmailWriter instance
            slack_app: Initialized Slack App instance
        """
        self.gmail_writer = gmail_writer
        self.slack_app = slack_app
        self.pending_drafts = {}  # Store pending drafts: {draft_id: draft_data}
        self.draft_timeouts = {}  # Store timeout info: {draft_id: expiry_time}
        self.DRAFT_TIMEOUT_HOURS = 24  # Drafts expire after 24 hours

    def send_draft_for_approval(
        self, draft: Dict, user_id: str, channel_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Send a draft email for approval with interactive buttons.

        Args:
            draft: Gmail draft dictionary from create_draft()
            user_id: Slack user ID to send approval request to
            channel_id: Optional channel ID (if not provided, sends DM)

        Returns:
            Optional[str]: The draft ID for tracking, or None if failed
        """
        try:
            # Generate unique draft ID
            draft_id = str(uuid.uuid4())

            # Decode the draft for display
            decoded_draft = self.gmail_writer.send_draft_slack(draft)

            # Store the draft data
            self.pending_drafts[draft_id] = {
                "draft": draft,
                "decoded_draft": decoded_draft,
                "user_id": user_id,
                "created_at": datetime.now(),
                "status": "pending",
            }

            # Set timeout
            self.draft_timeouts[draft_id] = datetime.now() + timedelta(
                hours=self.DRAFT_TIMEOUT_HOURS
            )

            # Create approval message with buttons
            approval_message = self._create_approval_message(decoded_draft, draft_id)

            # Send to Slack
            target = channel_id if channel_id else user_id
            response = self.slack_app.client.chat_postMessage(
                channel=target,
                text=approval_message["text"],
                blocks=approval_message["blocks"],
            )

            # Store the Slack message timestamp for updates
            self.pending_drafts[draft_id]["slack_message_ts"] = response["ts"]
            self.pending_drafts[draft_id]["slack_channel"] = target

            return draft_id

        except SlackApiError as e:
            print(f"Error sending draft for approval: {e.response['error']}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    def _create_approval_message(self, decoded_draft: Dict, draft_id: str) -> Dict:
        """
        Create the approval message with interactive buttons.

        Args:
            decoded_draft: Decoded draft data
            draft_id: Unique draft identifier

        Returns:
            Dict: Message text and blocks for Slack
        """
        # Create the main text
        text = f"*Email Draft for Approval*\n\n"
        text += f"*From:* {decoded_draft.get('sender', 'N/A')}\n"
        text += f"*To:* {decoded_draft.get('recipient', 'N/A')}\n"
        text += f"*Subject:* {decoded_draft.get('subject', 'N/A')}\n"
        text += f"*Body:* {decoded_draft.get('body', 'N/A')}\n"

        attachments = decoded_draft.get("attachment", [])
        if attachments:
            attachment_list = ", ".join(attachments)
            text += f"*Attachments:* {attachment_list}\n"

        # Create interactive blocks
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
            {
                "type": "actions",
                "block_id": f"draft_approval_{draft_id}",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Approve & Send",
                            "emoji": True,
                        },
                        "style": "primary",
                        "value": f"approve_{draft_id}",
                        "action_id": "approve_draft",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ Reject",
                            "emoji": True,
                        },
                        "style": "danger",
                        "value": f"reject_{draft_id}",
                        "action_id": "reject_draft",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✏️ Edit Draft",
                            "emoji": True,
                        },
                        "value": f"edit_{draft_id}",
                        "action_id": "edit_draft",
                    },
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Draft ID:* {draft_id[:8]}... | *Expires:* {self.draft_timeouts[draft_id].strftime('%Y-%m-%d %H:%M')}",
                    }
                ],
            },
        ]

        return {"text": text, "blocks": blocks}

    def handle_approval_action(self, ack: Ack, body: Dict, say: Say) -> None:
        """
        Handle approval/rejection button clicks.

        Args:
            ack: Slack acknowledgment function
            body: Request body containing action details
            say: Slack say function for responses
        """
        try:
            # Acknowledge the action immediately
            ack()

            # Extract action details
            action = body["actions"][0]
            action_id = action["action_id"]
            value = action["value"]
            user_id = body["user"]["id"]

            # Parse the action
            action_type, draft_id = value.split("_", 1)

            # Check if draft exists and is still pending
            if draft_id not in self.pending_drafts:
                say(text="❌ This draft has expired or doesn't exist.")
                return

            draft_data = self.pending_drafts[draft_id]

            # Check if draft has expired
            if datetime.now() > self.draft_timeouts[draft_id]:
                say(text="❌ This draft has expired.")
                self._cleanup_draft(draft_id)
                return

            # Handle different actions
            if action_type == "approve":
                self._handle_approve(draft_id, user_id, say)
            elif action_type == "reject":
                self._handle_reject(draft_id, user_id, say)
            elif action_type == "edit":
                self._handle_edit(draft_id, user_id, say)
            else:
                say(text="❌ Unknown action.")

        except Exception as e:
            print(f"Error handling approval action: {e}")
            say(text="❌ An error occurred while processing your request.")

    def _handle_approve(self, draft_id: str, user_id: str, say: Say) -> None:
        """Handle draft approval."""
        try:
            draft_data = self.pending_drafts[draft_id]
            draft = draft_data["draft"]

            # Send the email
            result = self.gmail_writer.send_draft(draft)

            if result:
                # Update the original message
                self._update_original_message(
                    draft_id, "✅ *APPROVED & SENT*", "success"
                )

                # Send confirmation
                say(
                    text=f"✅ Email approved and sent successfully!\n*Message ID:* {result.get('id', 'N/A')}"
                )

                # Update status
                draft_data["status"] = "approved"
                draft_data["approved_by"] = user_id
                draft_data["approved_at"] = datetime.now()

            else:
                say(text="❌ Failed to send email. Please try again.")

        except Exception as e:
            print(f"Error approving draft: {e}")
            say(text="❌ An error occurred while sending the email.")

    def _handle_reject(self, draft_id: str, user_id: str, say: Say) -> None:
        """Handle draft rejection."""
        try:
            draft_data = self.pending_drafts[draft_id]

            # Update the original message
            self._update_original_message(draft_id, "❌ *REJECTED*", "danger")

            # Send confirmation
            say(text="❌ Email draft rejected.")

            # Update status
            draft_data["status"] = "rejected"
            draft_data["rejected_by"] = user_id
            draft_data["rejected_at"] = datetime.now()

        except Exception as e:
            print(f"Error rejecting draft: {e}")
            say(text="❌ An error occurred while rejecting the draft.")

    def _handle_edit(self, draft_id: str, user_id: str, say: Say) -> None:
        """Handle draft edit request."""
        try:
            draft_data = self.pending_drafts[draft_id]
            decoded_draft = draft_data["decoded_draft"]

            # Send edit instructions
            edit_text = f"✏️ *Edit Draft Request*\n\n"
            edit_text += (
                f"To edit this draft, please provide the updated information:\n"
            )
            edit_text += (
                f"• Current recipient: {decoded_draft.get('recipient', 'N/A')}\n"
            )
            edit_text += f"• Current subject: {decoded_draft.get('subject', 'N/A')}\n"
            edit_text += f"• Current body: {decoded_draft.get('body', 'N/A')}\n\n"
            edit_text += (
                f"Reply to this message with your changes, or create a new draft."
            )

            say(text=edit_text)

            # Update status
            draft_data["status"] = "edit_requested"
            draft_data["edit_requested_by"] = user_id
            draft_data["edit_requested_at"] = datetime.now()

        except Exception as e:
            print(f"Error handling edit request: {e}")
            say(text="❌ An error occurred while processing edit request.")

    def _update_original_message(
        self, draft_id: str, status_text: str, color: str
    ) -> None:
        """Update the original approval message with status."""
        try:
            draft_data = self.pending_drafts[draft_id]

            if "slack_message_ts" in draft_data and "slack_channel" in draft_data:
                # Update the original message
                self.slack_app.client.chat_update(
                    channel=draft_data["slack_channel"],
                    ts=draft_data["slack_message_ts"],
                    text=f"{status_text}\n\n*Original draft has been processed.*",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"{status_text}\n\n*Original draft has been processed.*",
                            },
                        }
                    ],
                )
        except Exception as e:
            print(f"Error updating original message: {e}")

    def _cleanup_draft(self, draft_id: str) -> None:
        """Remove draft from storage."""
        if draft_id in self.pending_drafts:
            del self.pending_drafts[draft_id]
        if draft_id in self.draft_timeouts:
            del self.draft_timeouts[draft_id]

    def cleanup_expired_drafts(self) -> None:
        """Remove expired drafts from storage."""
        current_time = datetime.now()
        expired_drafts = [
            draft_id
            for draft_id, expiry_time in self.draft_timeouts.items()
            if current_time > expiry_time
        ]

        for draft_id in expired_drafts:
            self._cleanup_draft(draft_id)
            print(f"Cleaned up expired draft: {draft_id}")

    def get_draft_status(self, draft_id: str) -> Optional[Dict]:
        """Get the status of a specific draft."""
        if draft_id in self.pending_drafts:
            return self.pending_drafts[draft_id]
        return None

    def list_pending_drafts(self) -> Dict:
        """List all pending drafts."""
        return {
            draft_id: {
                "status": data["status"],
                "created_at": data["created_at"],
                "recipient": data["decoded_draft"].get("recipient"),
                "subject": data["decoded_draft"].get("subject"),
            }
            for draft_id, data in self.pending_drafts.items()
        }
