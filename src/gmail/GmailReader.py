import base64
from typing import List, Dict, Optional

from bs4 import BeautifulSoup

from googleapiclient.discovery import build

from src.gmail.GmailAuthenticator import auth_user
from src.models.gmail import EmailMessage, EmailSummary


class GmailReader:
    """Class performs reading operations using the Gmail API"""

    def __init__(self, path):
        self.path = path
        self.creds = auth_user(self.path)
        self.service = build("gmail", "v1", credentials=self.creds)

    def read_emails(
        self,
        count: int = 5,
        unread_only: bool = False,
        include_body: bool = True,
        primary_only: bool = True,
        thread_id: Optional[str] = None,
    ) -> List[EmailMessage]:
        """
        Read emails with enhanced functionality matching the schema.

        Args:
            count: Number of emails to retrieve (max 25)
            unread_only: Whether to retrieve only unread emails
            include_body: Whether to include full email body content
            primary_only: Whether to retrieve only emails from Primary inbox category

        Returns:
            List of EmailMessage objects
        """
        # Build query to specifically target inbox emails
        query_parts = ["in:inbox"]  # Only inbox emails

        if primary_only:
            query_parts.append("category:primary")  # Only Primary category emails

        if unread_only:
            query_parts.append("is:unread")

        query = " ".join(query_parts)

        # List the user's messages, cap at 25 messages
        list_params = {"userId": "me", "maxResults": min(count, 25), "q": query}

        results = self.service.users().messages().list(**list_params).execute()
        messages = results.get("messages", [])

        if not messages:
            print("No messages found.")
            return []

        email_messages = []
        for message in messages:
            email_msg = self._get_email_message(message["id"], include_body)
            if email_msg:
                email_messages.append(email_msg)

        return email_messages

    def get_recent_emails_in_thread(
        self, thread_id: str, count: int = 4
    ) -> List[EmailMessage]:
        """
        Get the most recent emails in a thread.
        """
        return self.read_emails(count=count, thread_id=thread_id)

    def get_email_by_id(
        self, email_id: str, include_body: bool = True
    ) -> Optional[EmailMessage]:
        """
        Retrieve a specific email by its Gmail message ID.

        Args:
            email_id: Gmail message ID
            include_body: Whether to include full email body content

        Returns:
            EmailMessage object or None if not found
        """
        try:
            message_detail = (
                self.service.users()
                .messages()
                .get(userId="me", id=email_id, format="full")
                .execute()
            )

            return self._get_email_message(email_id, include_body, message_detail)
        except Exception as e:
            print(f"Error retrieving email {email_id}: {e}")
            return None

    def search_emails(
        self, query: str, max_results: int = 10, include_body: bool = False
    ) -> List[EmailMessage]:
        """
        Search emails using Gmail search query syntax.

        Args:
            query: Gmail search query (e.g., 'from:example@gmail.com', 'subject:meeting')
            max_results: Maximum number of results to return
            include_body: Whether to include full email body content

        Returns:
            List of EmailMessage objects
        """
        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=min(max_results, 50))
                .execute()
            )

            messages = results.get("messages", [])
            if not messages:
                return []

            email_messages = []
            for message in messages:
                email_msg = self._get_email_message(message["id"], include_body)
                if email_msg:
                    email_messages.append(email_msg)

            return email_messages
        except Exception as e:
            print(f"Error searching emails with query '{query}': {e}")
            return []

    def _get_email_message(
        self,
        message_id: str,
        include_body: bool = True,
        message_detail: Optional[Dict] = None,
    ) -> Optional[EmailMessage]:
        """
        Helper method to create EmailMessage object from Gmail API response.

        Args:
            message_id: Gmail message ID
            include_body: Whether to include full email body content
            message_detail: Pre-fetched message detail (optional)

        Returns:
            EmailMessage object or None if error
        """
        try:
            if not message_detail:
                message_detail = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=message_id, format="full")
                    .execute()
                )

            if not message_detail:
                return None

            payload = message_detail.get("payload")
            if not payload:
                return None

            headers = payload.get("headers", [])
            subject = self._get_header(headers, "Subject") or "No Subject"
            from_email = self._get_header(headers, "From") or "Unknown"
            to_email = self._get_header(headers, "To") or "Unknown"
            date_str = self._get_header(headers, "Date") or "Unknown"

            # Get email body if requested
            body = ""
            if include_body:
                raw_body = self._get_email_body(payload)
                body = self._html_parser(raw_body)

            # Get additional Gmail-specific fields
            label_ids = message_detail.get("labelIds", [])
            is_read = "UNREAD" not in label_ids
            is_important = "IMPORTANT" in label_ids
            thread_id = message_detail.get("threadId", "")

            return EmailMessage(
                id=message_id,
                subject=subject,
                from_email=from_email,
                to_email=to_email,
                date=date_str,
                body=body,
                is_read=is_read,
                is_important=is_important,
                thread_id=thread_id,
            )

        except Exception as e:
            print(f"Error processing email {message_id}: {e}")
            return None

    def _generate_activity_summary(
        self, emails: List[EmailMessage], summary_by_sender: Dict
    ) -> str:
        """
        Generate a human-readable summary of recent email activity.

        Args:
            emails: List of email messages
            summary_by_sender: Dictionary grouping emails by sender

        Returns:
            String summary of recent activity
        """
        if not emails:
            return "No recent email activity."

        # Count emails by sender
        sender_counts = {
            sender: len(email_list) for sender, email_list in summary_by_sender.items()
        }

        # Get top senders
        top_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[
            :3
        ]

        # Count urgent emails
        urgent_count = len([e for e in emails if e.is_important])

        summary_parts = [
            f"You have {len(emails)} unread emails.",
            f"Top senders: {', '.join([f'{sender} ({count})' for sender, count in top_senders])}.",
        ]

        if urgent_count > 0:
            summary_parts.append(f"{urgent_count} emails are marked as important.")

        return " ".join(summary_parts)

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
