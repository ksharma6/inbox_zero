import os

from src.agent.OpenAIAgent import Agent
from src.gmail.GmailReader import GmailReader
from src.utils.load_env import load_dotenv_helper

#load keys + paths
load_dotenv_helper()
token_path = os.getenv("TOKENS_PATH")
api_path=os.getenv("OPENAI_API_KEY")

#Init objects
reader = GmailReader(token_path)

tools = [{
    "type": "function",

    "name": "gmail_reader_read_labels",
    "description": "Get current labels from gmail email account.",
    "parameters": {
        # "type": "object",
        # "properties": {
        #     "location": {
        #         "type": "string",
        #         "description": "City and country e.g. Bogotá, Colombia"
            }
        ,
    "additionalProperties": False}]
    
available_tools = {
    "gmail_reader_read_labels": reader.read_labels
}

agent = Agent(api_key=token_path,
              instructions="You are a helpful AI agent",
              tools=tools)

