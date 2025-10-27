"""Gmail package public API.

Expose the commonly used classes/functions for cleaner imports:

    from src.gmail import GmailReader, GmailWriter, auth_user
"""

from .gmail_authenticator import auth_user
from .gmail_reader import GmailReader
from .gmail_writer import GmailWriter

__all__ = [
    "GmailReader",
    "GmailWriter",
    "auth_user",
]
