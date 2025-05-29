import os.path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

def auth_user(path):
    """Authenticate user's Gmail account access.

    Args:
        path (string): path to directory where user's gmail token.json file 
        exists. The file token.json stores the user's access and refresh tokens, and is
        created automatically when the authorization flow completes for the first time.
    
    Returns:
        creds: Authenticated token from user
    """
    # Check for token.json in path for valid credentials\
    creds = None
    if os.path.exists(path + "token.json"):
      creds = Credentials.from_authorized_user_file(path + "token.json", SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
      if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
      else:
        flow = InstalledAppFlow.from_client_secrets_file(
            path + "credentials.json", SCOPES
        )
        creds = flow.run_local_server(port=0)
      
      # Save the credentials for the next run
      with open(path + "token.json", "w") as token:
        token.write(creds.to_json())

    return creds