from __future__ import annotations
from typing import Dict, List, Optional
import re
from email import message_from_bytes
from email.utils import parsedate_to_datetime
from .types import ParsedEmail, Attachment
from .decoder import b64url_decode, decode_header_str, parse_addr_list

# ------------------ Public API ------------------

def parse_message(msg: Dict, prefer_raw: bool = False) -> ParsedEmail:
    """
    Parse a Gmail API message dict returned by:
      gmail.users().messages().get(userId="me", id=..., format="full"|"raw")
    Set prefer_raw=True if you fetched format="raw" and want Python's email parser.
    """
    if prefer_raw and "raw" in msg:
        return _parse_raw(msg)
    return _parse_full(msg)

def fetch_attachment_bytes(gmail_service, user_id: str, message_id: str, attachment_id: str) -> bytes:
    """
    Download attachment bytes when a part only contains body.attachmentId.
    Usage:
      data = fetch_attachment_bytes(gmail, "me", parsed.message_id, att.attachment_id)
    """
    resp = gmail_service.users().messages().attachments().get(
        userId=user_id, messageId=message_id, id=attachment_id
    ).execute()
    data = resp.get("data", "")
    return b64url_decode(data)

# ------------------ FULL format path ------------------

def _parse_full(msg: Dict) -> ParsedEmail:
    payload = msg.get("payload", {}) or {}

    # Normalize headers to a case-insensitive map
    headers = {(h.get("name", "") or "").lower(): h.get("value", "") for h in payload.get("headers", [])}

    subject = decode_header_str(headers.get("subject"))
    from_   = decode_header_str(headers.get("from"))
    to      = parse_addr_list(decode_header_str(headers.get("to")))
    cc      = parse_addr_list(decode_header_str(headers.get("cc")))
    bcc     = parse_addr_list(decode_header_str(headers.get("bcc")))
    date_hdr= decode_header_str(headers.get("date"))

    date_iso: Optional[str] = None
    try:
        if date_hdr:
            date_iso = parsedate_to_datetime(date_hdr).isoformat()
    except Exception:
        date_iso = date_hdr or None  # keep raw if parsing fails

    texts: List[str] = []
    htmls: List[str] = []
    atts: List[Attachment] = []

    # Walk all parts (flat list) so we can pick out text/html and attachments
    for part in _walk_parts(payload):
        mime = part.get("mimeType", "") or ""
        body = part.get("body", {}) or {}
        data = b""
        if "data" in body and body["data"]:
            data = b64url_decode(body["data"])

        filename = part.get("filename") or ""
        p_headers = {(h.get("name", "") or "").lower(): h.get("value", "") for h in part.get("headers", [])}
        disp = p_headers.get("content-disposition", "").lower()
        cid  = (p_headers.get("content-id") or "").strip("<>") or None
        charset = _charset_from(p_headers.get("content-type", "") or mime)

        # If filename present, or disposition says attachment, or Gmail gave an attachmentId → treat as attachment
        if filename or "attachment" in disp or body.get("attachmentId"):
            atts.append(Attachment(
                filename=decode_header_str(filename),
                mime_type=mime or p_headers.get("content-type", "") or "application/octet-stream",
                content_id=cid,
                size=body.get("size"),
                data=(data if data else None),
                attachment_id=body.get("attachmentId")
            ))
        elif mime.startswith("text/plain"):
            texts.append(_decode_to_text(data, charset))
        elif mime.startswith("text/html"):
            htmls.append(_decode_to_text(data, charset))

    return ParsedEmail(
        message_id=msg.get("id", ""),
        thread_id=msg.get("threadId", ""),
        subject=subject, from_=from_, to=to, cc=cc, bcc=bcc,
        date=date_iso,
        text=_best(texts),
        html=_best(htmls),
        headers=headers,
        attachments=atts
    )

# ------------------ RAW format path ------------------

def _parse_raw(msg: Dict) -> ParsedEmail:
    raw = b64url_decode(msg.get("raw", ""))
    em = message_from_bytes(raw)

    headers = {k.lower(): decode_header_str(v) for k, v in em.items()}
    subject = headers.get("subject", "")
    from_   = headers.get("from", "")
    to      = parse_addr_list(headers.get("to"))
    cc      = parse_addr_list(headers.get("cc"))
    bcc     = parse_addr_list(headers.get("bcc"))

    date_iso: Optional[str] = None
    try:
        if headers.get("date"):
            date_iso = parsedate_to_datetime(headers["date"]).isoformat()
    except Exception:
        date_iso = headers.get("date")

    texts: List[str] = []
    htmls: List[str] = []
    atts: List[Attachment] = []

    for part in em.walk():
        if part.is_multipart():
            continue
        mime = part.get_content_type()
        cid  = (part.get("Content-ID") or "").strip("<>") or None
        fn   = part.get_filename() or ""
        disp = (part.get("Content-Disposition") or "").lower()
        payload = part.get_payload(decode=True) or b""
        charset = part.get_content_charset()

        if fn or "attachment" in disp:
            atts.append(Attachment(
                filename=decode_header_str(fn),
                mime_type=mime,
                content_id=cid,
                size=len(payload) if payload else None,
                data=payload
            ))
        elif mime.startswith("text/plain"):
            texts.append(_decode_to_text(payload, charset))
        elif mime.startswith("text/html"):
            htmls.append(_decode_to_text(payload, charset))

    return ParsedEmail(
        message_id=msg.get("id", ""),
        thread_id=msg.get("threadId", ""),
        subject=subject, from_=from_, to=to, cc=cc, bcc=bcc,
        date=date_iso,
        text=_best(texts),
        html=_best(htmls),
        headers=headers,
        attachments=atts
    )

# ------------------ utilities ------------------

def _walk_parts(payload: Dict) -> List[Dict]:
    """
    Flatten the Gmail MIME tree (payload + parts[]) into a simple list of parts.
    """
    stack = [payload]
    out: List[Dict] = []
    while stack:
        p = stack.pop()
        out.append(p)
        for ch in (p.get("parts") or []):
            stack.append(ch)
    return out

def _charset_from(ct: str | None) -> Optional[str]:
    if not ct:
        return None
    m = re.search(r'charset="?([A-Za-z0-9_\-]+)"?', ct, flags=re.I)
    return m.group(1) if m else None

def _decode_to_text(b: bytes, charset: Optional[str]) -> str:
    """
    Decode bytes into text with a safe fallback order.
    """
    for enc in ([charset] if charset else []) + ["utf-8", "latin-1"]:
        try:
            return b.decode(enc, errors="replace")
        except Exception:
            continue
    return b.decode("utf-8", "replace")

def _best(items: List[str]) -> str:
    """
    Choose the longest non-empty variant (e.g., from multipart/alternative).
    """
    items = [i for i in items if i and i.strip()]
    return max(items, key=len) if items else ""
