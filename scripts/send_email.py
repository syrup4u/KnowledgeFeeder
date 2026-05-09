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

import yaml


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--body-file", required=True)
    return p.parse_args()


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def text_to_html(text):
    lines = []
    for line in text.splitlines():
        if line.startswith("=== ") and line.endswith(" ==="):
            lines.append(f"<h2>{line[4:-4]}</h2>")
        elif line.startswith("# "):
            lines.append(f"<h3>{line[2:]}</h3>")
        elif line.startswith("## "):
            lines.append(f"<h4>{line[3:]}</h4>")
        elif line == "---":
            lines.append("<hr>")
        elif line == "":
            lines.append("<p></p>")
        else:
            lines.append(f"<p>{line}</p>")
    return "<html><body>\n" + "\n".join(lines) + "\n</body></html>"


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
