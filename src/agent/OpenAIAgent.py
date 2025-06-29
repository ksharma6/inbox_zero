import os
import json
from typing import Optional

from openai import OpenAI

from src.gmail.GmailWriter import GmailWriter
from src.gmail.GmailReader import GmailReader
from src.models.agent import AgentSchema, ProcessRequestSchema


class Agent:
    def __init__(self, schema: AgentSchema):
        """Initializes the Agent

        Args:
            api_key (str): The API key for authenticating with the OpenAI API.
            model (str, optional): OpenAI model to be used. Defaults to "gpt-4.1".
            available_tools (Optional[dict], optional): A dictionary of tools
                that the agent can use. Keys are tool names and values are
                tool instances. Defaults to None.
        """
        self.client = OpenAI(api_key=schema.api_key)
        self.model = schema.model
        self.available_tools = schema.available_tools
        self.function_map = {}  # map function names to methods

        for tool_name, instance in self.available_tools.items():
            if isinstance(instance, GmailWriter):
                self.function_map["send_email"] = instance.send_email
            if isinstance(instance, GmailReader):
                self.function_map["read_email"] = instance.read_email

    def process_request(self, schema: ProcessRequestSchema):
        """Processes user's request by interacting with OpenAI model.

        Args:
            user_prompt (str): Prompt from the user.
            llm_tool_schema (list): A list of tool schemas that the LLM can
                choose to call.
            system_message (Optional[str], optional): An optional system-level
                instruction to guide the LLM's behavior (e.g., persona,
                tone, specific rules). For example: "You are a helpful AI agent".
                Defaults to None.

        Returns:
            _type_: _description_
        """
        self.llm_tool_schema = schema.llm_tool_schema
        self.user_prompt = schema.user_prompt

        messages = []
        if schema.system_message:
            messages.append({"role": "system", "content": schema.system_message})
        messages.append({"role": "user", "content": schema.user_prompt})

        print("Prompt received: ", schema.user_prompt)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.llm_tool_schema,
            tool_choice="auto",
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            print("Agent decided to use tool.")
            # add agent's reply
            messages.append(response_message)

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args_str = tool_call.function.arguments

                print(f"Function to call: {function_name}")
                print(f"Function arguments: {function_args_str}")

                function_to_call = self.function_map.get(function_name)

                if function_to_call:
                    # Handle missing keys in function_args if they are optional
                    try:
                        function_args = json.loads(function_args_str)
                        result = function_to_call(**function_args)
                    except TypeError as e:
                        print(
                            f"Error calling {function_name} with args {function_args_str}: {e}"
                        )
                        result = f"Error: Could not call {function_name} due to argument mismatch."
                    except json.JSONDecodeError:
                        print(
                            f"Error decoding arguments for {function_name}. Trying to call without arguments or with defaults."
                        )
                        # Attempt to call with no args if appropriate, or handle default
                        if (
                            function_name == "read_email"
                        ):  # Example: read_email might default
                            result = function_to_call()
                        else:
                            result = f"Error: Invalid arguments for {function_name}."

                    print(f"Tool '{function_name}' executed. Result: {result}")
                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": str(result),  # Ensure content is a string
                        }
                    )
                else:
                    print(f"Unknown function '{function_name}' requested by LLM.")
                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": f"Error: Function '{function_name}' is not available.",
                        }
                    )

            print("\nAgent processing tool result... (Second call to OpenAI)")
            second_response = self.client.chat.completions.create(
                model=self.model, messages=messages
            )
            final_response = second_response.choices[0].message.content
            print(f"\nAgent final response:\n{final_response}")
            return final_response
        else:
            final_response = response_message.content
            print(f"\nAgent direct response (no tool used):\n{final_response}")
            return final_response
