"""Helpers for decoding Gmail message payloads and headers."""

from __future__ import annotations

import base64
from email.header import decode_header
from email.utils import formataddr, getaddresses
from typing import Iterable, List, Tuple


def b64url_decode(data: str | bytes | None) -> bytes:
    """
    Decode the URL-safe base64 blobs Gmail returns (without guaranteed padding).
    """
    if not data:
        return b""
    if isinstance(data, str):
        raw = data.encode()
    else:
        raw = data
    padding = (-len(raw)) % 4
    if padding:
        raw += b"=" * padding
    try:
        return base64.urlsafe_b64decode(raw)
    except Exception:
        return b""


def decode_header_str(value: str | bytes | None) -> str:
    """
    Decode RFC 2047 encoded words into a single Unicode string.
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    try:
        parts = decode_header(value)
    except Exception:
        return value

    out: List[str] = []
    for text, charset in parts:
        if isinstance(text, bytes):
            enc = charset or "utf-8"
            try:
                out.append(text.decode(enc, "replace"))
            except Exception:
                out.append(text.decode("utf-8", "replace"))
        else:
            out.append(text)
    return "".join(out)


def parse_addr_list(value: str | None) -> List[str]:
    """
    Parse a comma-separated list of addresses into formatted strings.
    """
    if not value:
        return []
    formatted: List[str] = []
    for name, addr in getaddresses([value]):
        addr = addr.strip()
        if not addr:
            continue
        clean_name = decode_header_str(name).strip()
        formatted.append(formataddr((clean_name, addr)).strip())
    return formatted


__all__ = ["b64url_decode", "decode_header_str", "parse_addr_list"]
