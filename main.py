import os

from flask import Flask
from slack_bolt import App as SlackApp
from src.utils.load_env import load_dotenv_helper
from src.LangGraph.workflow_factory import get_workflow
from src.routes.flask_routes import register_flask_routes
from src.routes.slack.slack_routes import register_slack_routes

app = Flask(__name__)
load_dotenv_helper(path="/Users/ksharma6/Documents/projects/inbox_zero/")

slack_app = SlackApp(
    token=os.getenv("SLACK_BOT_TOKEN"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
)
# initialize workflow (singleton) and register routes that depend on it
workflow = get_workflow(slack_app)
register_flask_routes(app, workflow)
register_slack_routes(app, slack_app, workflow)

## moved slack routes and actions to src/routes/slack/slack_routes.register_slack_routes


if __name__ == "__main__":
    app.run(port=5002, debug=True)
