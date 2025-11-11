"""Utilities for fetching and summarizing Gmail messages for agent tooling."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from . import parse_gmail_message
from .types import ParsedEmail

SCOPES: Sequence[str] = ("https://www.googleapis.com/auth/gmail.readonly",)


def _body_text(parsed: ParsedEmail) -> str:
    """Prefer plain text, fall back to HTML."""
    for candidate in (parsed.text, parsed.html):
        if candidate and candidate.strip():
            return candidate.strip()
    return ""


def summarize_parsed_email(parsed: ParsedEmail) -> Dict[str, Any]:
    """
    Reduce a ParsedEmail down to the fields most agent tools usually need.
    """
    return {
        "subject": parsed.subject or "",
        "from": parsed.from_ or "",
        "to": parsed.to,
        "cc": parsed.cc,
        "body": _body_text(parsed),
    }


def summarize_message_json(msg: Dict[str, Any], *, prefer_raw: bool = False) -> Dict[str, Any]:
    """
    Parse a Gmail API message dict and return a minimal summary.
    """
    parsed = parse_gmail_message(msg, prefer_raw=prefer_raw)
    return summarize_parsed_email(parsed)


def _ensure_google_imports():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    return Request, Credentials, InstalledAppFlow, build


def build_gmail_service(
    *,
    token_path: str | Path = "token.json",
    client_secret_path: str | Path = "client_secret.json",
    scopes: Sequence[str] = SCOPES,
    cache_discovery: bool = False,
):
    """
    Create an authenticated Gmail API client, prompting the user if needed.
    """
    Request, Credentials, InstalledAppFlow, build = _ensure_google_imports()

    token_path = Path(token_path)
    client_secret_path = Path(client_secret_path)

    creds: Optional[Credentials] = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secret_path.exists():
                raise FileNotFoundError(
                    f"client_secret file not found at {client_secret_path}. "
                    "Download it from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), scopes)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds, cache_discovery=cache_discovery)


def list_message_ids(
    gmail_service,
    *,
    max_results: int = 5,
    label_ids: Iterable[str] | None = None,
) -> List[str]:
    """
    Return the most recent Gmail message IDs, optionally filtered by label.
    """
    resp = (
        gmail_service.users()
        .messages()
        .list(userId="me", maxResults=max_results, labelIds=list(label_ids or []))
        .execute()
    )
    return [m["id"] for m in resp.get("messages", [])]


def fetch_message_json(
    gmail_service,
    message_id: str,
    *,
    format: str = "full",
) -> Dict[str, Any]:
    """
    Download a single Gmail message as a JSON dict (full or raw).
    """
    return (
        gmail_service.users()
        .messages()
        .get(userId="me", id=message_id, format=format)
        .execute()
    )


def read_message_summary(
    message_id: str,
    *,
    gmail_service=None,
    token_path: str | Path = "token.json",
    client_secret_path: str | Path = "client_secret.json",
    format: str = "full",
    prefer_raw: bool | None = None,
) -> Dict[str, Any]:
    """
    High-level helper suitable for agent tools: fetch, parse, and summarize a message.
    Provide an authenticated gmail_service to reuse connections, or let this helper
    build one from the OAuth credentials on disk.
    """
    if gmail_service is None:
        gmail_service = build_gmail_service(
            token_path=token_path, client_secret_path=client_secret_path
        )
    prefer_raw = prefer_raw if prefer_raw is not None else format == "raw"
    msg = fetch_message_json(gmail_service, message_id, format=format)
    return summarize_message_json(msg, prefer_raw=prefer_raw)


__all__ = [
    "SCOPES",
    "build_gmail_service",
    "fetch_message_json",
    "list_message_ids",
    "read_message_summary",
    "summarize_message_json",
    "summarize_parsed_email",
]
