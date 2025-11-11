import base64, unittest
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from email_parser import parse_gmail_message
from email_parser.tool import summarize_message_json

def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

class TestParser(unittest.TestCase):
    def test_parse_full_text_and_html(self):
        msg = {
            "id": "mid123",
            "threadId": "tid456",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Offer Discussion"},
                    {"name": "From", "value": "HR <hr@example.com>"},
                    {"name": "To", "value": "you <you@example.com>"},
                    {"name": "Date", "value": formatdate(localtime=True)},
                ],
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": b64url(b"Hello\\nThis is plain.")}},
                    {"mimeType": "text/html", "body": {"data": b64url(b"<p>Hello <b>HTML</b></p>")}},
                ],
            },
        }
        parsed = parse_gmail_message(msg)
        self.assertEqual(parsed.subject, "Offer Discussion")
        self.assertIn("Hello", parsed.text)
        self.assertIn("<b>HTML</b>", parsed.html)
        self.assertEqual(parsed.from_, "HR <hr@example.com>")

    def test_parse_full_with_attachment_id(self):
        msg = {
            "id": "m2",
            "threadId": "t2",
            "payload": {
                "headers": [{"name": "Subject", "value": "With Attachment"}],
                "mimeType": "multipart/mixed",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": b64url(b"See attached")}},
                    {
                        "filename": "contract.pdf",
                        "mimeType": "application/pdf",
                        "headers": [{"name": "Content-Disposition", "value": "attachment"}],
                        "body": {"attachmentId": "ATTACH123", "size": 1234},
                    },
                ],
            },
        }
        p = parse_gmail_message(msg)
        self.assertTrue(p.attachments)
        att = p.attachments[0]
        self.assertEqual(att.filename, "contract.pdf")
        self.assertEqual(att.attachment_id, "ATTACH123")
        self.assertIsNone(att.data)  # bytes not included; use fetch_attachment_bytes later

    def test_parse_raw_simple(self):
        m = MIMEMultipart()
        m["Subject"] = "Welcome"
        m["From"] = "Team <team@example.com>"
        m["To"] = "you@example.com"
        m["Date"] = formatdate(localtime=True)
        m.attach(MIMEText("Hello from raw", "plain", "utf-8"))
        raw = m.as_bytes()
        msg = {"id": "m3", "threadId": "t3", "raw": b64url(raw)}
        p = parse_gmail_message(msg, prefer_raw=True)
        self.assertEqual(p.subject, "Welcome")
        self.assertIn("Hello from raw", p.text)

    def test_summarize_message_json_prefers_plain_text(self):
        msg = {
            "id": "mid123",
            "threadId": "tid456",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Offer Discussion"},
                    {"name": "From", "value": "HR <hr@example.com>"},
                    {"name": "To", "value": "you <you@example.com>"},
                    {"name": "Cc", "value": "ally@example.com"},
                ],
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": b64url(b"Hello plain body")}},
                    {"mimeType": "text/html", "body": {"data": b64url(b"<p>HTML body</p>")}},
                ],
            },
        }
        summary = summarize_message_json(msg)
        self.assertEqual(summary["subject"], "Offer Discussion")
        self.assertEqual(summary["from"], "HR <hr@example.com>")
        self.assertIn("you <you@example.com>", summary["to"][0])
        self.assertEqual(summary["cc"][0], "ally@example.com")
        self.assertIn("Hello plain body", summary["body"])

    def test_summarize_message_json_falls_back_to_html(self):
        msg = {
            "id": "mid123",
            "threadId": "tid456",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "No Text"},
                    {"name": "From", "value": "Bot <bot@example.com>"},
                    {"name": "To", "value": "you <you@example.com>"},
                ],
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/html", "body": {"data": b64url(b"<p>HTML only</p>")}},
                ],
            },
        }
        summary = summarize_message_json(msg)
        self.assertIn("HTML only", summary["body"])

if __name__ == "__main__":
    unittest.main()
