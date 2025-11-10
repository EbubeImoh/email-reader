from email_parser import parse_gmail_message, fetch_attachment_bytes

# Suppose you already have a Gmail API client `gmail` and a message id `mid`
m = gmail.users().messages().get(userId="me", id=mid, format="full").execute()
parsed = parse_gmail_message(m)

print(parsed.subject, parsed.from_)
print(parsed.text)

# Download attachment bytes if needed:
for att in parsed.attachments:
    if att.attachment_id and not att.data:
        data = fetch_attachment_bytes(gmail, "me", parsed.message_id, att.attachment_id)
        print(att.filename, len(data))
