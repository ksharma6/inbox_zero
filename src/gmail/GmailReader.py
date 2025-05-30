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

    def read_emails(self):
        service = build("gmail", "v1", credentials=self.creds)

        # List the user's messages
        results = service.users().messages().list(userId="me", maxResults=10).execute()
        messages = results.get("messages", [])

        if not messages:
            print("No messages found.")
        else:
            print("Messages:")
            for message in messages:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=message["id"], format="raw")
                    .execute()
                )
                raw_message = base64.urlsafe_b64decode(msg["raw"]).decode("utf-8")
                print(f"Message ID: {message['id']}")
                print(f"Raw Message:\n{raw_message}\n")
