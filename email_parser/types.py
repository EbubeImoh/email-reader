from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class Attachment:
    """
    Metadata for an attachment or inline part.
    - If Gmail returned inline data, `data` is bytes.
    - If Gmail returned only `attachment_id`, use `fetch_attachment_bytes(...)` to download.
    """
    filename: str = ""
    mime_type: str = "application/octet-stream"
    content_id: Optional[str] = None          # e.g., for inline images (cid:)
    size: Optional[int] = None                # reported size (may be approximate)
    data: Optional[bytes] = None              # raw bytes if included in the part
    attachment_id: Optional[str] = None       # Gmail body.attachmentId when data omitted

@dataclass
class ParsedEmail:
    """
    Canonical, minimal view of an email message.
    """
    message_id: str
    thread_id: str
    subject: str
    from_: str
    to: List[str] = field(default_factory=list)
    cc: List[str] = field(default_factory=list)
    bcc: List[str] = field(default_factory=list)
    date: Optional[str] = None                # ISO8601 if parsed
    text: str = ""                            # best-effort plain text
    html: str = ""                            # best-effort HTML
    headers: Dict[str, str] = field(default_factory=dict)
    attachments: List[Attachment] = field(default_factory=list)
