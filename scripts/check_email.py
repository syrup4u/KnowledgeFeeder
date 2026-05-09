#!/usr/bin/env python3
"""Fetch unread feedback replies via IMAP, classify with Claude, dispatch to subject feedback.md files."""

import argparse
import email
import imaplib
import json
import os
import sys
from datetime import datetime
from email.header import decode_header

import subprocess

import yaml


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--subjects-dir", required=True)
    return p.parse_args()


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def decode_header_str(raw):
    parts = decode_header(raw or "")
    result = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            result.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(chunk)
    return "".join(result)


def get_plain_text(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode("utf-8", errors="replace")
    return ""


def get_subject_map(subjects_dir):
    """Return {folder_name: display_name} by reading plan.md subject fields."""
    result = {}
    if not os.path.isdir(subjects_dir):
        return result
    for folder in os.listdir(subjects_dir):
        folder_path = os.path.join(subjects_dir, folder)
        if not os.path.isdir(folder_path):
            continue
        display = folder
        plan_path = os.path.join(folder_path, "plan.md")
        if os.path.exists(plan_path):
            try:
                with open(plan_path) as f:
                    content = f.read()
                parts = content.split("---\n", 2)
                if len(parts) >= 3:
                    plan = yaml.safe_load(parts[1])
                    display = plan.get("subject", folder)
            except Exception:
                pass
        result[folder] = display
    return result


def classify_feedback(model, body, subject_map):
    """Ask Claude to split the feedback body into per-subject pieces.

    Returns a dict {folder_name: feedback_text}.
    """
    subject_list = "\n".join(
        f'  - "{display}" (folder: {folder})' for folder, display in subject_map.items()
    )
    system = (
        "You are a feedback classifier. Given a user's freeform feedback email and a list of "
        "learning subjects, split the feedback into per-subject items. Return valid JSON only — "
        "no explanation, no markdown fences."
    )
    user = (
        f"Available subjects:\n{subject_list}\n\n"
        f"User feedback email:\n{body}\n\n"
        "Return a JSON object where keys are folder names and values are the relevant feedback "
        "text for that subject. Only include subjects that are mentioned or clearly relevant. "
        "If feedback is general (applies to all subjects), include it under every folder key. "
        "Return only valid JSON."
    )
    prompt = f"{system}\n\n---\n\n{user}"
    result = subprocess.run(
        ["claude", "--model", model, "-p", prompt],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "claude CLI exited with non-zero status")
    raw = result.stdout.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)


def append_feedback(subjects_dir, folder, text, timestamp):
    path = os.path.join(subjects_dir, folder, "feedback.md")
    entry = f"## Feedback {timestamp}\n\n{text.strip()}\n\n---\n"
    with open(path, "a") as f:
        f.write(entry)


def main():
    args = parse_args()

    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"ERROR: failed to load config: {e}", file=sys.stderr)
        sys.exit(0)  # non-fatal — generation should still proceed

    subject_map = get_subject_map(args.subjects_dir)
    if not subject_map:
        print("No subjects found, skipping feedback check.")
        sys.exit(0)

    cfg = config["email"]
    model = config["anthropic"]["model_utility"]

    try:
        conn = imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"])
        conn.login(cfg["address"], cfg["password"])
        conn.select("INBOX")
    except Exception as e:
        print(f"WARNING: IMAP connection failed: {e}", file=sys.stderr)
        sys.exit(0)

    try:
        # Look for unread messages sent from the user's own address
        _, data = conn.search(None, "UNSEEN", f'FROM "{cfg["address"]}"')
        msg_ids = data[0].split()

        if not msg_ids:
            print("No unread feedback emails found.")
            return

        print(f"Found {len(msg_ids)} unread feedback email(s).")
        timestamp = datetime.now().isoformat(timespec="seconds")

        for mid in msg_ids:
            try:
                _, raw = conn.fetch(mid, "(RFC822)")
                msg = email.message_from_bytes(raw[0][1])
                body = get_plain_text(msg)

                if not body.strip():
                    print(f"  Skipping message {mid.decode()}: empty body")
                    conn.store(mid, "+FLAGS", "\\Seen")
                    continue

                classified = classify_feedback(model, body, subject_map)

                dispatched = 0
                for folder, text in classified.items():
                    if folder in subject_map and text.strip():
                        append_feedback(args.subjects_dir, folder, text, timestamp)
                        print(f"  → subjects/{folder}/feedback.md")
                        dispatched += 1

                if dispatched == 0:
                    print(f"  WARNING: could not match feedback to any known subject")

                conn.store(mid, "+FLAGS", "\\Seen")

            except json.JSONDecodeError as e:
                print(f"  ERROR: Claude returned invalid JSON for message {mid.decode()}: {e}", file=sys.stderr)
                conn.store(mid, "+FLAGS", "\\Seen")
            except Exception as e:
                print(f"  ERROR processing message {mid.decode()}: {e}", file=sys.stderr)

    finally:
        try:
            conn.logout()
        except Exception:
            pass


if __name__ == "__main__":
    main()
