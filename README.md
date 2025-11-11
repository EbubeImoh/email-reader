# email-reader

Small helper package that turns Gmail API message payloads into a convenient `ParsedEmail` dataclass so clients can inspect subject, sender, text/HTML bodies, and attachments.

## Developing with `uv`

1. Install dependencies into a virtual env aligned with the pinned lock file:
   ```bash
   uv sync --dev
   ```
2. Run the test suite (uses `pytest`, but the tests themselves rely on `unittest` so they stay lightweight):
   ```bash
   uv run pytest
   ```
3. (Optional) List or download real Gmail messages via OAuth:
   ```bash
   uv run python scripts/fetch_message.py --list            # show latest IDs
   uv run python scripts/fetch_message.py --message-id <ID> # download to message.json
   ```
   The script expects your Google OAuth `client_secret.json` in the project root. It stores tokens in `token.json` so you only authorize once.
4. Parse any Gmail message response (from the script above or any saved API response):
   ```bash
   uv run python main.py path/to/message.json
   # or pipe from stdin:
   cat message.json | uv run python main.py -
   # fetch + parse without writing a file:
   uv run python scripts/fetch_message.py --message-id <ID> --output - | uv run python main.py -
   ```
   The CLI prints just the Subject, From, To, CC, and a best-effort body preview.
5. Call the reusable agent helper directly from Python if you only want the structured summary:
   ```python
   from email_parser.tool import read_message_summary

   summary = read_message_summary(
       "19a724d70fc3fe08",
       token_path="token.json",
       client_secret_path="client_secret.json",
   )
   print(summary["subject"], summary["body"][:120])
   ```
   You can reuse an existing Gmail service with `build_gmail_service(...)` and pass it via the `gmail_service` parameter to avoid repeated OAuth prompts.

`uv` reads dependencies from `pyproject.toml` and keeps an isolated cache, so no manual virtualenv management is required.
