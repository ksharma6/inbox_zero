from src.models.toolfunction import ToolFunction, ToolParams, ParamProperties


class GmailToolFunction:
    """
    Defines TooFunction schema for sending emails
    """

    @staticmethod
    def generate_send_email_schema() -> ToolFunction:
        """
        Returns Pydantic ToolFunction for `GmailWriter.send_email()`
        """

        return ToolFunction(
            name="send_email",
            description="Sends an email to a recipient with a subject and body.",  # Description matches
            parameters=ToolParams(
                type="object",
                properties={
                    "sender": ParamProperties(
                        type="string", description="The sender's email address."
                    ),
                    "recipient": ParamProperties(
                        type="string", description="The recipient's email address."
                    ),
                    "subject": ParamProperties(
                        type="string", description="The subject of the email."
                    ),
                    "message": ParamProperties(
                        type="string", description="The main content of the email."
                    ),
                    "attachment_path": ParamProperties(
                        type="string", description="Path to attachment - Optional"
                    ),
                },
                required=[
                    "sender",
                    "recipient",
                    "subject",
                    "message",
                ],
            ),
        )
