from googleapiclient.discovery import build


from src.gmail.GmailAuthenticator import auth_user


class GCalendar:

    def __init__(self, token: str):
        self.token = token
        self.creds = auth_user(self.token)

    def get_availability(self, start_time, end_time):
        service = build("calendar", "v3", credentials=self.creds)

        body = {
            "timeMin": start_time,
            "timeMax": end_time,
            "items": [{"id": "primary"}],
        }

        events = service.freebusy().query(body=body).execute()

        return events
