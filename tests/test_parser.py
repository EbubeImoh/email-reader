import base64, unittest
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from email_parser import parse_gmail_message

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
                    {"name": "From", "value": "HR <[email protected]>"},
                    {"name": "To", "value": "you <[email protected]>"},
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
        self.assertEqual(parsed.from_, "HR <[email protected]>")

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
        m["From"] = "Team <[email protected]>"
        m["To"] = "[email protected]"
        m["Date"] = formatdate(localtime=True)
        m.attach(MIMEText("Hello from raw", "plain", "utf-8"))
        raw = m.as_bytes()
        msg = {"id": "m3", "threadId": "t3", "raw": b64url(raw)}
        p = parse_gmail_message(msg, prefer_raw=True)
        self.assertEqual(p.subject, "Welcome")
        self.assertIn("Hello from raw", p.text)

if __name__ == "__main__":
    unittest.main()
