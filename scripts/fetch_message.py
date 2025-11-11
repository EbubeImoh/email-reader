# scripts/fetch_message.py
"""Utilities to list and download Gmail API messages to disk."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from email_parser.tool import (
    build_gmail_service,
    fetch_message_json,
    list_message_ids,
)

TOKEN = Path("token.json")
SECRET = Path("client_secret.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch Gmail messages via the Gmail API.")
    parser.add_argument(
        "--message-id",
        help="Explicit message ID to download. If omitted, downloads the newest message.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="message.json",
        help="Where to store the downloaded message (use '-' for stdout; default: %(default)s).",
    )
    parser.add_argument(
        "--format",
        choices=["full", "raw"],
        default="full",
        help="Gmail API message format to request.",
    )
    parser.add_argument(
        "--labels",
        nargs="*",
        default=None,
        help="Optional list of label IDs to filter when picking the newest message.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List recent message IDs instead of downloading (honors --max-results/--labels).",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="How many IDs to list when using --list (default: %(default)s).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argp = build_parser()
    args = argp.parse_args(argv)

    gmail = build_gmail_service(token_path=TOKEN, client_secret_path=SECRET)

    if args.list:
        ids = list_message_ids(gmail, max_results=args.max_results, label_ids=args.labels)
        if not ids:
            print("No messages returned.")
            return 0
        print("Recent message IDs:")
        for mid in ids:
            print(f"  {mid}")
        return 0

    message_id = args.message_id
    if not message_id:
        ids = list_message_ids(gmail, max_results=1, label_ids=args.labels)
        if not ids:
            raise SystemExit("No messages found to download. Try adjusting labels or mailbox contents.")
        message_id = ids[0]
        print(f"No --message-id provided; using newest message {message_id}.")

    message = fetch_message_json(gmail, message_id, format=args.format)
    if args.output == "-":
        json.dump(message, sys.stdout)
        sys.stdout.flush()
        return 0

    Path(args.output).write_text(json.dumps(message, indent=2))
    print(f"Saved {args.format} message to {args.output}")
    print("Run `uv run python main.py {file}` to inspect it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
