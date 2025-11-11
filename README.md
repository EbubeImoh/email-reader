# email-reader

Utilities for turning Gmail API message responses into a convenient Python dataclass or a lightweight summary that agent-style tools can consume. The project includes:

- `email_parser` package with the low-level parser (`parse_gmail_message`) and a high-level helper (`read_message_summary`).
- CLI scripts to fetch Gmail messages and print human-readable summaries.

---

## 1. Prerequisites

| Requirement | Why |
|-------------|-----|
| Python 3.11 | Managed via `.python-version` so tooling stays consistent. |
| `uv`        | Dependency management (`uv sync`, `uv run`, etc.). |
| Google Cloud project with Gmail API enabled | Needed to obtain OAuth credentials for your mailbox. |

Make sure `uv` is on your PATH. On macOS with Homebrew: `brew install uv`.

---

## 2. Install dependencies

```bash
uv sync --dev
```

- Creates/updates `.venv/` with everything defined in `pyproject.toml`.
- Installs testing tools (`pytest`), Gmail client libraries (`google-api-python-client`, `google-auth`, `google-auth-oauthlib`), and `html2text` for HTML→plain-text conversion.

If you run commands from outside the repo, prefix with `UV_CACHE_DIR=/path/to/cache` to reuse the local cache we’ve been using.

---

## 3. Configure Gmail OAuth credentials

1. **Enable the Gmail API**
   - Visit [Google Cloud Console](https://console.cloud.google.com/).
   - Select your project (or create one).
   - APIs & Services → Library → enable **Gmail API**.

2. **Set up the OAuth consent screen**
   - APIs & Services → OAuth consent screen.
   - Fill in the required details; for personal testing, add your Google account as a test user.

3. **Create OAuth client credentials**
   - APIs & Services → Credentials → “Create Credentials” → **OAuth client ID**.
   - Application type: **Desktop app**.
   - Download the JSON file and save it in the repo root as `client_secret.json`.

4. **First authorization**
   - The first time you run any Gmail command below, a browser window opens so you can approve access.
   - A `token.json` file (already git-ignored) stores the refresh/access token for future runs.

---

## 4. CLI tutorial

All commands below should be executed from the repository root.

### 4.1 List recent message IDs

```bash
uv run python scripts/fetch_message.py --list
```

`--max-results 10` and `--labels INBOX` are available if you want more control.

### 4.2 Download a message to disk

```bash
uv run python scripts/fetch_message.py --message-id <ID> --output message.json
```

- Defaults to Gmail’s `format="full"`.
- Use `--format raw` if you want the raw RFC 822 payload (remember to pass `--prefer-raw` when parsing later).

### 4.3 Parse and summarize a saved message

```bash
uv run python main.py message.json
```

Output includes:
- Subject
- From
- To / CC
- Body text (plain text preferred; falls back to HTML)

### 4.4 Stream directly without writing a file

```bash
uv run python scripts/fetch_message.py --message-id <ID> --output - \
  | uv run python main.py -
```

That pipeline fetches the message via Gmail, writes JSON to stdout, and pipes it into the parser CLI.

---

## 5. Python API / agent quickstart

### 5.1 Fetch, parse, summarize in one call

```python
from email_parser.tool import read_message_summary

summary = read_message_summary(
    "19a724d70fc3fe08",
    token_path="token.json",
    client_secret_path="client_secret.json",
    # format="raw", prefer_raw=True  # if you fetched with format="raw"
)

print(summary["subject"])
print(summary["from"])
print(summary["body"][:200])
```

The returned dict only contains `subject`, `from`, `to`, `cc`, and `body`. `body` favors MIME `text/plain`, but when an email only includes HTML the project runs it through [`html2text`](https://github.com/Alir3z4/html2text) so you still get readable plain text without tags.

### 5.2 Reuse an existing Gmail client

```python
from email_parser.tool import build_gmail_service, read_message_summary

gmail = build_gmail_service(token_path="token.json", client_secret_path="client_secret.json")
summary = read_message_summary("19a724d70fc3fe08", gmail_service=gmail)
```

Pass the `gmail_service` parameter to avoid repeated OAuth prompts and to batch multiple lookups efficiently.

### 5.3 Work with raw parser output

```python
from email_parser.tool import fetch_message_json, summarize_message_json
from email_parser import parse_gmail_message

gmail = build_gmail_service()

# Full Gmail payload
msg = fetch_message_json(gmail, "19a724d70fc3fe08", format="full")

# Dataclass (subject, from_, to, cc, date, text/html, attachments, etc.)
parsed = parse_gmail_message(msg)

# Minimal summary (what read_message_summary returns internally)
summary = summarize_message_json(msg)
```

Additional helpers:

| Helper | Description |
|--------|-------------|
| `build_gmail_service(...)` | Creates an authenticated Gmail API service (handles tokens). |
| `list_message_ids(...)`    | Returns recent message IDs, optionally filtered by label. |
| `fetch_message_json(...)`  | Downloads a message (`format="full"` or `"raw"`). |
| `summarize_message_json(...)` | Converts a Gmail payload into `{subject, from, to, cc, body}`. |
| `summarize_parsed_email(...)` | Same as above but works with the `ParsedEmail` dataclass. |
| `read_message_summary(...)` | High-level helper for agent tooling (fetch + summarize). |

---

## 6. Running tests

```bash
uv run pytest
```

Tests live in `tests/test_parser.py` and cover:
- Parsing Gmail “full” and “raw” payloads.
- Attachment handling.
- Summarizer behavior (plain text preference plus html2text-based fallback when only HTML is available).

---

## 7. Tips & troubleshooting

- **Python warnings**: we pin Python 3.11 to avoid Google’s “unsupported Python” warnings clogging stdout during streaming.
- **Missing credentials**: If `client_secret.json` or `token.json` is missing, the scripts explain how to regenerate them. Both files are listed in `.gitignore`.
- **No message data**: When streaming (`--output -`), ensure the consumer (e.g., `main.py -`) reads stdin immediately. Any stray prints before the JSON (warnings, logs) can break the parser—keep the environment clean or upgrade your Python version as we did here.

That’s it—install deps, drop in your `client_secret.json`, run `uv run python scripts/fetch_message.py --list` to grab IDs, and either pipe into the CLI or call `read_message_summary()` from your agent. When in doubt, re-run `uv sync --dev` to refresh the virtualenv.***
