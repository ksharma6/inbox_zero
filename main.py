import os

from flask import Flask
from slack_bolt import App as SlackApp

from src.LangGraph.workflow_factory import get_workflow
from src.routes.flask.flask_routes import register_flask_routes
from src.routes.slack.slack_routes import register_slack_routes
from src.utils.load_env import load_dotenv_helper

app = Flask(__name__)

load_dotenv_helper()

slack_app = SlackApp(
    token=os.getenv("SLACK_BOT_TOKEN"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
)
# initialize workflow, register flask and slack routes
workflow = get_workflow(slack_app)
register_flask_routes(app, workflow)
register_slack_routes(app, slack_app, workflow)

if __name__ == "__main__":
    app.run(port=5002, debug=True)
