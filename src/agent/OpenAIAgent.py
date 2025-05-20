from openai import OpenAI

import os

from src.utils.load_dotenv import load_dotenv_helper

load_dotenv_helper()

api_key = os.environ.get("MY_OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

class Agent:
    def __init__(self, api_key=api_key, model = "gpt-4.1",  name= "OpenAIAgent",
                 instructions = "", tools = None):
        """Initialize an agent with OpenAI API key and model

        Args:
            api_key (string): API key from OpenAI API platform
            model (str, optional): OpenAI model you would like agent to use. 
            Defaults to "gpt-4.1".
            name (str, optional): Name of agent. Defaults to "OpenAIAgent".
        """
        self.api_key = api_key
        self.model = model
        self.name = name
        self.instructions = instructions #specific instructions you want agent
                                         #to follow
        self.tools = tools #what api tools do you want agent to use

        self.assistant = client.beta.assistants.create(
            name = self.name,
            instructions= self.instructions,
            tools= self.tools,
            model= self.model
        )


    def command(self, role, prompt, temp = .7, max_tokens = 150):


        response = client.responses.create(
            model= self.model,
            input=[{"role":role,
                    "content":prompt,
                    }],
            tools = self.tools,
            temperature=temp, 
            max_tokens= max_tokens
        )