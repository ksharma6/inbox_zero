"""Gmail package public API.

Expose the commonly used classes/functions for cleaner imports:

    from src.gmail import GmailReader, GmailWriter, auth_user
"""

from .GmailAuthenticator import auth_user
from .GmailReader import GmailReader
from .GmailWriter import GmailWriter

__all__ = [
    "GmailReader",
    "GmailWriter",
    "auth_user",
]
