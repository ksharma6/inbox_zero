from openai import OpenAI

client = OpenAI()

class Agent:
    def __init__(self, api_key, model = "gpt-4.1",  name= "OpenAIAgent",
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
        self.instructions = instructions
        self.tools = tools

        self.assistant = client.beta.assistants.create(
            name = self.name,
            instructions= self.instructions,
            tools= self.tools,
            model= self.model
        )


    def get_response(self, prompt,role, temp = .7, max_tokens = 150):

        response = OpenAI.ChatC