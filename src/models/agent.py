import datetime
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from src.models.gmail import EmailMessage, EmailSummary


class AgentSchema(BaseModel):
    """Schema for agent configuration"""

    api_key: str = Field(..., description="OpenAI API key")
    model: str = Field(default="gpt-4", description="OpenAI model to use")
    available_tools: Dict[str, Any] = Field(
        default={}, description="Available tools for the agent"
    )


class ProcessRequestSchema(BaseModel):
    """Schema for processing requests"""

    user_prompt: str = Field(..., description="User's request prompt")
    llm_tool_schema: Any = Field(..., description="Tool schema for LLM")
    system_message: Optional[str] = Field(
        default=None, description="System message for the agent"
    )


class GmailAgentState(BaseModel):
    """State for Gmail processing workflow"""

    # Input
    user_id: str = Field(..., description="Slack user ID requesting email processing")
    thread_id: str = Field(..., description="Unique ID for the email processing thread")

    # Email data
    unread_emails: List[EmailMessage] = Field(
        default=[], description="List of unread emails"
    )
    email_summary: Optional[EmailSummary] = Field(
        default=None, description="Summary of emails"
    )

    # Processing state
    current_email_index: int = Field(
        default=0, description="Index of current email being processed"
    )
    processed_emails: List[Dict] = Field(
        default=[], description="List of processed email results"
    )

    # Draft responses
    draft_responses: List[Dict] = Field(
        default=[], description="List of draft responses created"
    )
    pending_approvals: List[Dict] = Field(
        default=[], description="Drafts pending Slack approval"
    )
    current_draft_index: int = Field(
        default=0, description="Index of the draft currently being reviewed"
    )
    awaiting_approval: bool = Field(
        default=False, description="Whether waiting for Slack approval"
    )
    awaiting_approval_since: Optional[datetime.datetime] = Field(
        default=None, description="Time when waiting for approval started"
    )

    # Workflow control
    should_continue: bool = Field(
        default=True, description="Whether to continue processing emails"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if any"
    )

    # Final output
    final_summary: Optional[str] = Field(
        default=None, description="Final summary sent to user"
    )
    workflow_complete: bool = Field(
        default=False, description="Whether workflow is complete"
    )
