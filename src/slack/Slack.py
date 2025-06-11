import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from src.slack.SlackAuthenticator import authenticate_slack


class SlackBot:
    def __init__(self, token: str):
        self.token = token
        client = authenticate_slack(token)
        self.client = client

    def send_message(self, channel: str, message: str):
        self.channel = channel

        try:
            result = self.client.chat_postMessage(channel=self.channel, text=message)
            print("message sent")

        except SlackApiError:
            if SlackApiError.response["error"] == "channel_not_found":
                print("Please ensure the user ID is correct or the bot has permission.")
            elif SlackApiError.response["error"] == "invalid_auth":
                print("The Slack token is invalid. Please verify it.")
