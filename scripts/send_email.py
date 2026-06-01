#!/usr/bin/env python3
"""Send the daily KnowledgeFeeder email via SMTP."""

import argparse
import smtplib
import sys
from datetime import date
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import markdown as md
import yaml


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--body-file", required=True)
    p.add_argument("--subject-name", default="")
    return p.parse_args()


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


_EMAIL_CSS = """
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
         line-height: 1.7; color: #222; max-width: 680px; margin: 0 auto; padding: 24px; }
  h1, h2, h3, h4 { color: #111; margin-top: 1.6em; margin-bottom: 0.4em; }
  h2 { font-size: 1.3em; border-bottom: 1px solid #e0e0e0; padding-bottom: 0.3em; }
  h3 { font-size: 1.1em; }
  code { font-family: 'SF Mono', Consolas, 'Courier New', monospace;
         background: #f3f3f3; padding: 2px 5px; border-radius: 3px; font-size: 0.88em; }
  pre { background: #f3f3f3; border: 1px solid #e0e0e0; border-radius: 6px;
        padding: 14px 16px; overflow-x: auto; }
  pre code { background: none; padding: 0; font-size: 0.87em; }
  table { border-collapse: collapse; width: 100%; margin: 1em 0; }
  th, td { border: 1px solid #ddd; padding: 7px 12px; text-align: left; }
  th { background: #f3f3f3; font-weight: 600; }
  blockquote { border-left: 4px solid #ccc; margin: 1em 0; padding: 4px 16px; color: #555; }
  hr { border: none; border-top: 1px solid #e0e0e0; margin: 2em 0; }
  ul, ol { padding-left: 1.5em; }
  li { margin: 0.25em 0; }
"""


def text_to_html(text):
    import re
    # Convert === Subject === section headers to markdown ## headings
    processed = re.sub(r"^=== (.+) ===$", r"## \1", text, flags=re.MULTILINE)
    body = md.markdown(processed, extensions=["fenced_code", "tables"])
    return f"<html><head><style>{_EMAIL_CSS}</style></head><body>\n{body}\n</body></html>"


def build_message(cfg, subject_line, body_text, today):
    size_limit = cfg.get("body_size_limit_kb", 50) * 1024
    over_limit = len(body_text.encode("utf-8")) > size_limit

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject_line
    msg["From"] = cfg["address"]
    msg["To"] = cfg["address"]

    if over_limit:
        notice = (
            f"Your KnowledgeFeeder content for {today} is attached "
            f"(body was too large for inline display)."
        )
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(notice, "plain"))
        alt.attach(MIMEText(f"<html><body><p>{notice}</p></body></html>", "html"))
        msg.attach(alt)

        part = MIMEBase("application", "octet-stream")
        part.set_payload(body_text.encode("utf-8"))
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="kf-{today}.md"')
        msg.attach(part)
    else:
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(body_text, "plain"))
        alt.attach(MIMEText(text_to_html(body_text), "html"))
        msg.attach(alt)

    return msg, over_limit


def main():
    args = parse_args()

    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"ERROR: failed to load config: {e}", file=sys.stderr)
        sys.exit(1)

    with open(args.body_file) as f:
        body_text = f.read()

    cfg = config["email"]
    today = date.today().isoformat()
    if args.subject_name:
        subject_line = f"KnowledgeFeeder — {args.subject_name} — {today}"
    else:
        subject_line = f"KnowledgeFeeder — {today}"

    msg, attached = build_message(cfg, subject_line, body_text, today)

    try:
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as smtp:
            smtp.starttls()
            smtp.login(cfg["address"], cfg["password"])
            smtp.send_message(msg)
    except Exception as e:
        print(f"ERROR: failed to send email: {e}", file=sys.stderr)
        sys.exit(1)

    mode = "attachment" if attached else "inline"
    print(f"Email sent: {subject_line} ({mode})")


if __name__ == "__main__":
    main()
