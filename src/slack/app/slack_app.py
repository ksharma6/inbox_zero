import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Initializes your app with your bot token and socket mode handler
slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
slack_app_token = os.environ.get("SLACK_APP_TOKEN")

app = App(token=slack_bot_token)


@app.message("")
def message_hello(message, say):
    say(f"Hi there <@{message['user']}> :)")

    if message.get("channel_type") == "im":
        # The user's message text is in the 'text' field of the message payload.
        received_text = message["text"]
        user_id = message["user"]  # ID of the user who sent the message

        # Log to the console that a message was received
        print(f"Received a DM from user {user_id}: '{received_text}'")

        # The `say()` function sends a message back to the same channel
        # where the original message was received.
        say(f"You sent me: '{received_text}'")


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, slack_app_token).start()
