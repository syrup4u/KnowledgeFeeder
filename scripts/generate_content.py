#!/usr/bin/env python3
"""Generate learning content for a subject using the Claude API."""

import argparse
import os
import sys
from datetime import datetime

import subprocess

import yaml


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--subject-dir", required=True)
    p.add_argument("--config", required=True)
    return p.parse_args()


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def load_plan(subject_dir):
    plan_path = os.path.join(subject_dir, "plan.md")
    if not os.path.exists(plan_path):
        raise FileNotFoundError(f"plan.md not found in {subject_dir}")
    with open(plan_path) as f:
        content = f.read()
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError(f"plan.md in {subject_dir} is missing YAML front matter (expected --- delimiters)")
    return yaml.safe_load(parts[1])


def load_file(path):
    if not os.path.exists(path):
        return ""
    with open(path) as f:
        return f.read().strip()


def count_entries(history):
    return history.count("## Entry ")


def extract_covered_topics(history):
    """Return a list of topic strings logged in ## Entry blocks."""
    topics = []
    capture = False
    for line in history.splitlines():
        if line.strip() == "### Topic":
            capture = True
            continue
        if capture:
            text = line.strip()
            if text and not text.startswith("#"):
                topics.append(text)
            capture = False
    return topics


def recent_entries(history, n=3):
    """Return up to n most recent ## Entry blocks plus any compacted summary prefix."""
    chunks = history.split("\n## Entry ")
    prefix = chunks[0].strip()          # compacted summary if present, else empty
    entries = ["\n## Entry " + c for c in chunks[1:]]
    parts = []
    if prefix:
        parts.append(prefix)
    parts.extend(entries[-n:])
    return "\n\n".join(parts)


def build_prompts(plan, history, feedback):
    length_map = {"short": "~300 words", "medium": "~600 words", "long": "~1200 words"}
    word_count = length_map.get(plan.get("content_length", "medium"), "~600 words")

    system = (
        f"You are a personalized learning assistant generating educational content.\n"
        f"Subject: {plan['subject']}\n"
        f"Format: {plan.get('format', 'tutorial')}\n"
        f"Depth: {plan.get('depth', 'intermediate')}\n"
        f"Target length: {word_count}\n"
        f"Language: {plan.get('language', 'English')}"
    )

    if plan.get("focus_topics"):
        topics = "\n".join(f"  - {t}" for t in plan["focus_topics"])
        system += f"\nFocus topics (prioritize but do not limit to these):\n{topics}"

    if plan.get("extra_instructions"):
        system += f"\n\nAdditional instructions:\n{plan['extra_instructions']}"

    user_parts = []

    if history:
        covered = extract_covered_topics(history)
        if covered:
            topic_list = "\n".join(f"  - {t}" for t in covered)
            user_parts.append(f"Topics already covered — do not repeat these:\n{topic_list}")
        context = recent_entries(history, n=3)
        if context:
            user_parts.append(f"Recent sessions (for progression context):\n\n{context}")
    else:
        user_parts.append(
            "This is the first session for this subject. Start from the very beginning."
        )

    if feedback:
        user_parts.append(f"User feedback and requests to incorporate:\n\n{feedback}")

    user_parts.append(
        f"Generate the next {plan.get('format', 'tutorial')} session content for this subject."
    )

    return system, "\n\n".join(user_parts)


def run_claude(system, user, model):
    prompt = f"{system}\n\n---\n\n{user}" if system else user
    result = subprocess.run(
        ["claude", "--model", model, "-p", prompt],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "claude CLI exited with non-zero status")
    return result.stdout.strip()


def compact_history(model, plan, history):
    length_map = {"short": "concise (3–5 paragraphs)", "medium": "moderate (5–8 paragraphs)"}
    summary_len = length_map.get(plan.get("compaction_summary_length", "short"), "concise (3–5 paragraphs)")

    system = (
        "You are a learning history summarizer. Distill a log of past learning sessions "
        "into a structured summary that preserves key concepts, examples, and progression."
    )
    user = (
        f"Subject: {plan['subject']}\n"
        f"Depth level: {plan.get('depth', 'intermediate')}\n"
        f"Summary length: {summary_len}\n\n"
        f"Full learning history to compact:\n\n{history}\n\n"
        "Produce a summary suitable for informing a tutor what this student has already "
        "covered, so they do not repeat material unnecessarily."
    )
    return run_claude(system, user, model)


def extract_topic(content):
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
        if line:
            return line[:80] + ("..." if len(line) > 80 else "")
    return "Learning session"


def format_entry(timestamp, topic, content):
    return f"## Entry {timestamp}\n\n### Topic\n{topic}\n\n### Content\n{content}\n\n---\n"


def main():
    args = parse_args()

    try:
        config = load_config(args.config)
        plan = load_plan(args.subject_dir)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    history = load_file(os.path.join(args.subject_dir, "history.md"))
    feedback = load_file(os.path.join(args.subject_dir, "feedback.md"))

    model_generation = config["anthropic"]["model_generation"]
    model_utility = config["anthropic"]["model_utility"]

    system, user = build_prompts(plan, history, feedback)

    try:
        content = run_claude(system, user, model_generation)
    except Exception as e:
        print(f"ERROR: claude CLI call failed: {e}", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.now().isoformat(timespec="seconds")
    entry = format_entry(timestamp, extract_topic(content), content)
    new_history = (history + "\n\n" + entry).lstrip() if history else entry

    threshold = int(plan.get("compaction_threshold", 20))
    if count_entries(new_history) >= threshold:
        try:
            n = count_entries(new_history)
            summary = compact_history(model_utility, plan, new_history)
            new_history = (
                f"## Compacted Summary (as of {timestamp}, covering {n} entries)\n\n"
                f"{summary}\n\n---\n"
            )
        except Exception as e:
            print(f"WARNING: compaction failed, keeping full history: {e}", file=sys.stderr)

    with open(os.path.join(args.subject_dir, "history.md"), "w") as f:
        f.write(new_history)

    if feedback:
        with open(os.path.join(args.subject_dir, "feedback.md"), "w") as f:
            f.write("")

    subject_name = plan.get("subject", os.path.basename(args.subject_dir))
    print(f"=== {subject_name} ===\n")
    print(content)
    print()


if __name__ == "__main__":
    main()
