import base64

from bs4 import BeautifulSoup

from googleapiclient.discovery import build

from src.gmail.GmailAuthenticator import auth_user


class GmailReader:
    """Class performs reading operations using the Gmail API"""

    def __init__(self, path):
        self.path = path
        self.creds = auth_user(self.path)
        self.service = build("gmail", "v1", credentials=self.creds)

    def read_email(self, count=5):
        formatted_emails = []

        # List the user's messages
        results = (
            self.service.users()
            .messages()
            .list(userId="me", maxResults=count)
            .execute()
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
                    self.service.users()
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
                from_email = self._get_header(headers, "From")
                to_email = self._get_header(headers, "To")
                date_str = self._get_header(headers, "Date")

                # get email body (forwarded email)
                raw_body = self._get_email_body(payload)
                body = self._html_parser(raw_body)

                if subject:
                    formatted_emails.append(
                        {
                            "id": message_id,
                            "subject": subject,
                            "from": from_email,
                            "to": to_email,
                            "date": date_str,
                            "body": body,
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

    def _html_parser(self, data: str):
        """
        Removes HTML tags from a string using BS4

        Args:
            data (str): string you would like parser applied to

        Returns:
            cleaned_data (str): parsed input data string
        """
        if not data or data == "":
            print("string not found")
            return ""

        soup = BeautifulSoup(data, "html.parser")

        # remove script/style tags
        for tag in soup(["script", "style"]):
            tag.decompose()

        # aggregate remaining text
        cleaned_data = soup.get_text(separator=" ", strip=True)

        return cleaned_data

    def _get_email_body(self, payload):
        """
        Helper to extract email body including multipart messages (e.g. forwarded emails).

        Args:
            payload (dict): payload received from gmail service object

        Returns:
            body (string): concatenated string of all readable parts of payload.
        """

        body = ""

        if "parts" in payload:
            for part in payload["parts"]:
                # recursive call for each part in payload
                body += self._get_email_body(part)
        # base case - part w/ body
        elif "body" in payload and "data" in payload["body"]:
            part_body = payload["body"]["data"]

            if payload.get("mimeType") == "text/plain":
                body += base64.urlsafe_b64decode(part_body).decode("utf-8")
            elif payload.get("mimeType") == "text/html":
                html_content = base64.urlsafe_b64decode(part_body).decode("utf-8")
                soup = BeautifulSoup(html_content, "html.parser")
                body += soup.get_text()

        return body
