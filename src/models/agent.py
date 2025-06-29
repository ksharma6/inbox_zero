from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


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
    llm_tool_schema: List[Dict[str, Any]]
    user_prompt: str = Field(..., description="Prompt from user")
    system_message: Optional[str] = Field(
        None,
        description="An optional system-level"
        "instruction to guide the LLM's behavior (e.g., persona,"
        "tone, specific rules).",
    )
