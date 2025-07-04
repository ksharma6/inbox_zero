import os
from typing import Optional
import base64
from email.message import EmailMessage
import mimetypes

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

    def send_email(
        self,
        sender: str,
        recipient: str,
        subject: str,
        message: str,
        attachment_path: Optional[str] = None,
    ) -> Optional[dict]:
        try:
            service = build("gmail", "v1", credentials=self.creds)

            email = EmailMessage()

            email.set_content(message)

            email["To"] = recipient
            email["From"] = sender
            email["Subject"] = subject

            if attachment_path:
                # guess the MIME type of the attachment
                type_subtype, _ = mimetypes.guess_type(attachment_path)
                main_type, sub_type = type_subtype.split("/")

                # get filename
                filename = os.path.basename(attachment_path)
                print(filename)

                with open(attachment_path, "rb") as fp:
                    email.add_attachment(
                        fp.read(),
                        maintype=main_type,
                        subtype=sub_type,
                        filename=filename,
                    )

            # encode message
            encoded_email = base64.urlsafe_b64encode(email.as_bytes()).decode()

            create_email = {"raw": encoded_email}

            send_message = (
                service.users()
                .messages()
                .send(userId="me", body=create_email)
                .execute()
            )

            print(f'Message Id: {send_message["id"]}')

        except HttpError as error:
            print(f"An error occurred: {error}")
            send_message = None

        print("Message successfully sent to: " + recipient)
        return send_message
