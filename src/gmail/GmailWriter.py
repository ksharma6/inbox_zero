import os
from typing import Optional
import base64
import mimetypes

from email.message import EmailMessage
from email.parser import BytesParser
from email import message_from_bytes, policy
from email.policy import default


from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.gmail.GmailAuthenticator import auth_user


class GmailWriter:
    def __init__(self, token_path):
        """Initialize GmailWriter instance

        Args:
            token_path (string): path to directory where user's gmail token.json file exists.
            The file token.json stores the user's access and refresh tokens, and is created
            automatically when the authorization flow completes for the first time.
        """
        self.token_path = token_path
        self.creds = auth_user(self.token_path)
        self.service = build("gmail", "v1", credentials=self.creds)

    def create_draft(
        self,
        sender: str,
        recipient: str,
        subject: str,
        message: str,
        attachment_path: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Create a draft email message.

        Args:
            sender (str): The email address of the sender.
            recipient (str): The email address of the recipient.
            subject (str): The subject of the email.
            message (str): The body of the email.
            attachment_path (Optional[str], optional): The path to the attachment. Defaults to None.

        Returns:
            Optional[dict]: The draft email message.
        """
        try:

            draft = EmailMessage()

            draft.set_content(message)

            draft["To"] = recipient
            draft["From"] = sender
            draft["Subject"] = subject

            if attachment_path:
                # guess the MIME type of the attachment
                type_subtype, _ = mimetypes.guess_type(attachment_path)
                if type_subtype is None:
                    # Default to application/octet-stream if type cannot be guessed
                    main_type, sub_type = "application", "octet-stream"
                else:
                    main_type, sub_type = type_subtype.split("/")

                # get filename
                filename = os.path.basename(attachment_path)
                print(filename)

                with open(attachment_path, "rb") as fp:
                    draft.add_attachment(
                        fp.read(),
                        maintype=main_type,
                        subtype=sub_type,
                        filename=filename,
                    )

            # encode message
            raw_bytes = base64.urlsafe_b64encode(draft.as_bytes())
            raw_str = raw_bytes.decode()

            return {"raw": raw_str}

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def send_draft_slack(self, draft):
        """
        Send a draft email message to Slack.

        Args:
            draft (dict): The draft email message with 'raw' field.

        Returns:
            dict: The sent message details.
        """
        return self._email_message_decoder(draft)

    def send_draft(self, draft):
        """
        Send a draft email message to recipient.

        Args:
            draft (dict): The draft email message with 'raw' field.

        Returns:
            dict: The sent message details.
        """
        send_message = (
            self.service.users().messages().send(userId="me", body=draft).execute()
        )
        print(f"Message issued successfully")

        return send_message

    def send_reply(self, original_message, reply_message):
        headers = original_message["payload"]["headers"]
        to_address = next(
            header["value"] for header in headers if header["name"] == "From"
        )
        subject = next(
            header["value"] for header in headers if header["name"] == "Subject"
        )
        message_id = next(
            header["value"] for header in headers if header["name"] == "Message-ID"
        )

        # Extracting the original recipient (your email) from the 'To' header of the original email
        # This assumes the original email was sent to 'me'.
        my_email_address = next(
            header["value"] for header in headers if header["name"] == "To"
        )

        # Constructing the reply subject
        if not subject.startswith("Re:"):
            reply_subject = f"Re: {subject}"
        else:
            reply_subject = subject

        # Create the email message
        message = EmailMessage()
        message["to"] = to_address
        message["from"] = my_email_address  # Your email address
        message["subject"] = reply_subject
        message["In-Reply-To"] = message_id
        message["References"] = message_id  # Important for threading

        # Add the reply text
        message.set_content(reply_message)

        # The threadId is crucial for keeping replies in the same conversation.
        # It comes from the original message.
        thread_id = original_message["threadId"]

        # Encode the message to base64url format
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # send message
        try:
            message = (
                self.service.users()
                .messages()
                .send(userId="me", body=raw_message)
                .execute()
            )
            print(f"Reply sent successfully! Message ID: {message['id']}")
            return message

        except HttpError as error:
            print(f"An error occurred while sending reply: {error}")
            return None

    def _get_unread_message_id(self):
        """
        Return message id's of unread emails messages in inbox

        Returns:
            list: list of unread email message id's
        """

        try:
            result = (
                self.service.users()
                .messages()
                .list(userId="me", q="is:unread in:inbox")
                .execute()
            )
            message = result.get("messages", [])
            unread_id = message["id"]
            return unread_id

        except HttpError as error:
            print(f"An error occurred while fetching unread messages: {error}")
            return None

    def save_draft(self, draft):
        """
        Saves a draft email message.

        Args:
            draft (dict): The draft email message with 'raw' field.
        """
        try:
            # The Gmail API expects the draft in this format:
            # {"message": {"raw": "base64_encoded_message"}}
            create_draft = {"message": {"raw": draft["raw"]}}

            saved_draft = (
                self.service.users()
                .drafts()
                .create(userId="me", body=create_draft)
                .execute()
            )
            print(f"Draft saved successfully with ID: {saved_draft.get('id', 'N/A')}")
            return saved_draft
        except HttpError as error:
            print(f"An error occurred while saving draft: {error}")
            return None

    def _get_message_details(self, message_id):
        """
        Retrieves message details of specified message

        Args:
            message_id (str): email message id

        Returns:
            dict: Full message details are returned as dict.
        """

        try:
            message_details = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            print(f"Successfully retrieved email with ID: {message_id}")
            return message_details

        except HttpError as error:
            print(f"An error occurred while retrieving email {message_id}: {error}")
            return None

    def _email_message_decoder(self, raw_str):
        """Decodes a base64 encoded email and extracts its plain text body.

        Args:
            raw_str: A URL-safe base64 encoded string representing the raw email.

        Returns:
            The plain text body of the email.
        """
        # 1. Decode the base64 string back to bytes.
        # The raw string is URL-safe, so we use urlsafe_b64decode.
        raw_bytes = base64.urlsafe_b64decode(raw_str["raw"])

        # 2. Parse the bytes into an EmailMessage object.
        # We use message_from_bytes to reconstruct the email structure.
        # The 'default' policy is a good choice for handling modern email formats.
        email_message = message_from_bytes(raw_bytes, policy=default)

        # Get the plain text body safely
        body_part = email_message.get_body(preferencelist=("plain",))
        body_content = body_part.get_content() if body_part is not None else ""

        details = {
            "sender": email_message["From"],
            "recipient": email_message["To"],
            "subject": email_message["Subject"],
            "body": body_content,
            "attachment": [],
        }

        for part in email_message.iter_attachments():
            # attachment_data = {
            #     "filename": part.get_filename(),
            #     # "content": part.get_payload(decode=True)
            # }
            details["attachment"].append(part.get_filename())

        return details
