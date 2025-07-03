from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from src.models.gmail import ToolFunction


class AgentSchema(BaseModel):
    api_key: str = Field(
        ..., description="The API key for authenticating with the OpenAI API."
    )
    model: str = Field(
        "gpt-4.1", description="OpenAI model you would like to use to create agent"
    )
    available_tools: dict = Field(
        None,
        description="A dictionary of tools "
        "that the agent can use. Keys "
        "are tool names and values are tool instances.",
    )


class ProcessRequestSchema(BaseModel):
    user_prompt: str = Field(..., description="Prompt from user")
    llm_tool_schema: ToolFunction = Field(
        ..., description="Pydantic LLM Schema for tools"
    )
    system_message: Optional[str] = Field(
        None,
        description="An optional system-level"
        "instruction to guide the LLM's behavior (e.g., persona,"
        "tone, specific rules).",
    )
