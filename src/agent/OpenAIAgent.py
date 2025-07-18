import json
from typing import Dict, Any, Callable

from openai import OpenAI

from src.gmail.GmailWriter import GmailWriter
from src.gmail.GmailReader import GmailReader
from src.slack.DraftApprovalHandler import DraftApprovalHandler
from src.models.agent import AgentSchema, ProcessRequestSchema


class Agent:
    def __init__(self, schema: AgentSchema):
        """Initializes the Agent

        Args:
            schema (AgentSchema): Configuration schema containing API key, model, and available tools
        """
        self.client = OpenAI(api_key=schema.api_key)
        self.model = schema.model
        self.available_tools = schema.available_tools
        self.function_map: Dict[str, Callable] = {}

        # Map available tools to their methods
        self._setup_function_map()

    def _setup_function_map(self):
        """Setup the function mapping based on available tools"""
        if not self.available_tools:
            return
        for tool_name, instance in self.available_tools.items():
            if isinstance(instance, GmailWriter):
                # Map GmailWriter methods to function names
                self.function_map["create_draft"] = instance.create_draft
                self.function_map["send_draft"] = instance.send_draft
                self.function_map["save_draft"] = instance.save_draft
                self.function_map["send_reply"] = instance.send_reply
            elif isinstance(instance, GmailReader):
                # Map GmailReader methods to function names
                self.function_map["read_email"] = instance.read_email
            elif isinstance(instance, DraftApprovalHandler):
                # Map DraftApprovalHandler methods to function names
                self.function_map["send_draft_for_approval"] = (
                    instance.send_draft_for_approval
                )
            else:
                # Handle other tool types if needed
                print(f"Unknown tool type: {type(instance)} for tool: {tool_name}")

    def process_request(self, schema: ProcessRequestSchema, max_iterations: int = 5):
        """Processes user's request by interacting with OpenAI model.

        Args:
            schema (ProcessRequestSchema): Request schema containing user prompt, tool schema, and system message
            max_iterations (int): Maximum number of tool call rounds (default: 5)

        Returns:
            str: The final response from the agent
        """
        self.llm_tool_schema = schema.llm_tool_schema
        self.user_prompt = schema.user_prompt

        messages = []
        if schema.system_message:
            messages.append({"role": "system", "content": schema.system_message})
        messages.append({"role": "user", "content": schema.user_prompt})

        print("Prompt received: ", schema.user_prompt)

        # Convert tool schema(s) to proper OpenAI format
        # Handle both single ToolFunction and list of ToolFunctions
        if isinstance(self.llm_tool_schema, list):
            tools_payload = [
                {
                    "type": "function",
                    "function": tool_schema.model_dump(),
                }
                for tool_schema in self.llm_tool_schema
            ]
        else:
            tools_payload = [
                {
                    "type": "function",
                    "function": self.llm_tool_schema.model_dump(),
                }
            ]

        iteration = 0
        while iteration < max_iterations:
            print(f"\n--- Iteration {iteration + 1}/{max_iterations} ---")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools_payload,  # type: ignore
                tool_choice="auto",
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                print(f"Agent decided to use {len(tool_calls)} tool(s).")
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

                            # Special handling for Slack functions that need draft
                            if function_name in ["send_draft_for_approval"]:
                                if (
                                    "draft" not in function_args
                                    or not function_args["draft"]
                                ):
                                    result = f"Error: {function_name} requires a draft object. You must call create_draft() first to get a draft, then pass that draft to this function."
                                else:
                                    result = function_to_call(**function_args)
                            else:
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
                                result = (
                                    f"Error: Invalid arguments for {function_name}."
                                )

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
                        print(f"Available functions: {list(self.function_map.keys())}")
                        messages.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": f"Error: Function '{function_name}' is not available. Available functions: {list(self.function_map.keys())}",
                            }
                        )

                # Continue to next iteration for more tool calls
                iteration += 1

            else:
                # No more tool calls, get final response
                final_response = response_message.content
                print(
                    f"\nAgent final response (no more tools needed):\n{final_response}"
                )
                return final_response

        # If we reach max iterations, get a final response
        print(
            f"\nReached maximum iterations ({max_iterations}). Getting final response..."
        )
        final_response = (
            self.client.chat.completions.create(model=self.model, messages=messages)
            .choices[0]
            .message.content
        )
        print(f"\nAgent final response:\n{final_response}")
        return final_response
