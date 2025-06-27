from typing import Optional

from pydantic import BaseModel, Field


class OpenAISchema(BaseModel):
    model: str = Field(
        "gpt-4.1", description="OpenAI model you would like to use to create agent"
    )
    available_tools: dict = Field(
        None,
        description="A dictionary of tools "
        "that the agent can use. Keys "
        "are tool names and values are tool instances.",
    )
    llm_tool_schema: list = Field(
        None, description="A list of tool schemas that the LLM can choose to call"
    )
    user_prompt: str = Field(..., description="Prompt from user")
