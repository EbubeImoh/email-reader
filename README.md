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
3. Execute the sample script if you want to experiment with a Gmail API client:
   ```bash
   uv run python main.py
   ```

`uv` reads dependencies from `pyproject.toml` and keeps an isolated cache, so no manual virtualenv management is required.
