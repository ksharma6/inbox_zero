from typing import Optional

from pydantic import BaseModel, EmailStr, Field, FilePath


class GmailWriterSchema(BaseModel):
    sender: EmailStr = Field(..., description="The email address of the sender.")
    recipient: EmailStr = Field(..., description="The email address of the recipient")
    subject: str = Field(..., description="Subject line of the email to send.")
    message: str = Field(
        ..., description="Text body of email you would like to send to recipient"
    )
    attachment_path: Optional[FilePath] = Field(
        None, description="Path to attachment - Optional"
    )
