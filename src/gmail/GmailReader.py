import os.path
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.gmail.GmailAuthenticator import auth_user


class GmailReader:
    """Class performs reading operations using the Gmail API"""

    def __init__(self, path):
        self.path = path
        self.creds = auth_user(self.path)
        print(self.creds)

    def read_emails(self, count=5):
        formatted_emails = []

        # init gmail service object
        service = build("gmail", "v1", credentials=self.creds)

        # List the user's messages
        results = (
            service.users().messages().list(userId="me", maxResults=count).execute()
        )

        messages = results.get("messages", [])

        if not messages:
            print("No messages found.")
            return []
        else:
            print("Messages:")
            for message in messages:
                message_id = message["id"]

                message_detail = (
                    service.users()
                    .messages()
                    .get(userId="me", id=message_id, format="full")
                    .execute()
                )

                payload = message_detail.get("payload")

                if not payload:
                    print(f"No payload found for message ID: {message_id}")
                    continue

                headers = payload.get("headers", [])
                subject = self._get_header(headers, "Subject")
                print("subject:", subject)
                from_email = results._get_header(headers, "From")
                to_email = results._get_header(headers, "To")
                date_str = results._get_header(headers, "Date")

                # get email body
                body_plain, body_html = self._read_email_body(payload)

                if subject:
                    formatted_emails.append(
                        {
                            "id": message_id,
                            "subject": subject,
                            "from": from_email,
                            "to": to_email,
                            "date": date_str,
                            "body_plain": body_plain,
                            "body_html": body_html,
                        }
                    )

        return formatted_emails

    def _get_header(self, headers: list, name: str):
        """
        Retrieves the value from a specified email header from list of headers

        Args:
            headers (list): list of header dictionaries
            name (str): name of the header to find (e.g., 'Subject','From)
        """

        if headers:
            for header in headers:
                if header.get("name") == name:
                    return header.get("value")

        return None

    def _read_email_body(self, payload: dict):
        """
        Extracts email body from email message payload

        Args:
            payload (dict): payload received from gmail service object
        """

        body_plain = None
        body_html = None

        if "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType")
                part_body = part.get("body")

                # check for part containers with no direct body
                if not part_body:
                    continue

                data = part_body.get("data")
                # check for empty data
                if not data:
                    continue

                # check if partis a container type and use recursion to find actual content
                if (
                    mime_type == "multipart/alternative"
                    or mime_type == "multipart/related"
                    or mime_type == "multipart/mixed"
                ):

                    nested_plain, nested_html = self._get_email_body(part)
                    if nested_plain and not body_plain:
                        body_plain = nested_plain
                    if nested_html and not body_html:
                        body_html = nested_html
                elif mime_type == "text/plain":
                    if not body_plain:
                        decoded_data = base64.urlsafe_b64decode(
                            data.encode("UTF-8")
                        ).decode("UTF-8", errors="replace")
                        body_plain = decoded_data
                elif mime_type == "text/html":
                    if not body_html:  # Take the first HTML found
                        decoded_data = base64.urlsafe_b64decode(
                            data.encode("UTF-8")
                        ).decode("UTF-8", errors="replace")
                        body_html = decoded_data
        # body is directly in payload
        elif "body" in payload and "data" in payload["body"]:
            data = payload["body"]["data"]
            mime_type = payload.get("mimeType")
            if data:
                decoded_data = base64.urlsafe_b64decode(data.encode("UTF-8")).decode(
                    "UTF-8", errors="replace"
                )
                if mime_type == "text/plain":
                    body_plain = decoded_data
                elif mime_type == "text/html":
                    body_html = decoded_data

        return body_plain, body_html
