import base64
from email.message import EmailMessage
import mimetypes

import google.auth
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

    def write_email_draft(self,
                          sender:str, 
                          recipient:str, 
                          subject:str, 
                          message:str,
                          attachment_path = None) -> dict:
        service = build("gmail", "v1", credentials=self.creds)

        email=EmailMessage()

        email.set_content(message)

        email["To"] = recipient
        email["From"] = sender
        email["Subject"] = subject

        if attachment_path:
            #guess the MIME type of the attachment
            type_subtype, _ = mimetypes.guess_type(attachment_path)
            main_type, sub_type = type_subtype.split('/')

            with open(attachment_path, 'rb') as fp:
                attachment_data = fp.read()
            
            email.add_attachment(attachment_data, main_type, sub_type)

        #encode message
        encoded_email = base64.urlsafe_b64encode(email.as_bytes()).decode()

        create_email = {"message": {"raw": encoded_email}}

        draft = (
            service.users()
            .drafts()
            .create(userId= "me", body = create_email)
            .execute()
        )
        return draft



    
    def write_email_with_attachment(self):
        pass

    def send_message(self):
        pass