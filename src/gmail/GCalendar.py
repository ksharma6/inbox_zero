from googleapiclient.discovery import build

from .GmailAuthenticator import auth_user


class GCalendar:
    def __init__(self, path):
        self.path = path
        self.creds = auth_user(self.path)
        self.service = build("gmail", "v1", credentials=self.creds)

    def get_availability(self, start_date: str, end_date: str):
        """"""
        pass
