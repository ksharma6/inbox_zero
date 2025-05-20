import os.path
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.gmail.GmailAuthenticator import auth_user

class GmailReader:
  """Class performs reading operations using the Gmail API
  """
  def __init__(self, path):
    self.path = path
    self.creds = auth_user(self.path)
    print(self.creds)

  def read_labels(self):
    """Lists the user's Gmail labels

    Args:
        path (string): path to directory where user's gmail token.json file exists
    """
    try:
      # Call the Gmail API
      service = build("gmail", "v1", credentials=self.creds)
      results = service.users().labels().list(userId="me").execute()
      labels = results.get("labels", [])

      if not labels:
        print("No labels found.")
        return
      print("Labels:")
      for label in labels:
        print(label["name"])

    except HttpError as error:
      # TODO(developer) - Handle errors from gmail API.
      print(f"An error occurred: {error}")

  def read_emails(self):
    service = build('gmail', 'v1', credentials=self.creds)
    
    # List the user's messages
    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])

    if not messages:
        print('No messages found.')
    else:
        print('Messages:')
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format = 'raw').execute()
            raw_message = base64.urlsafe_b64decode(msg['raw']).decode('utf-8')
            print(f"Message ID: {message['id']}")
            print(f"Raw Message:\n{raw_message}\n")