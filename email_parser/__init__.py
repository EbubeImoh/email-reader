# Public API surface for convenience
from .types import ParsedEmail, Attachment
from .parser import parse_message as parse_gmail_message, fetch_attachment_bytes
