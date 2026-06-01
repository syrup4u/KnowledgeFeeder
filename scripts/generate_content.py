#!/usr/bin/env python3
"""Generate learning content for a subject using the Claude API."""

import argparse
import os
import sys
from datetime import date, datetime

import subprocess
import tempfile

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


def save_plan(subject_dir, plan):
    plan_path = os.path.join(subject_dir, "plan.md")
    with open(plan_path, "w") as f:
        f.write("---\n")
        yaml.dump(plan, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        f.write("---\n")


def apply_feedback_to_plan(model, plan, feedback):
    """Ask Claude to update plan fields based on feedback. Returns updated plan dict."""
    plan_yaml = yaml.dump(plan, default_flow_style=False, allow_unicode=True, sort_keys=False)
    system = (
        "You are a learning plan configurator. Given a YAML learning plan and user feedback, "
        "update the relevant plan fields to incorporate the feedback permanently. "
        "Valid frequency values: daily, every_2_days, every_3_days, weekly, biweekly, never. "
        "Use 'never' to disable/unsubscribe a subject. "
        "Return ONLY valid YAML with no markdown fences or extra text."
    )
    user = (
        f"Current learning plan:\n\n{plan_yaml}\n\n"
        f"User feedback:\n{feedback}\n\n"
        "Update the plan fields to reflect this feedback. Keep all existing fields; "
        "only modify what the feedback requires. Return the complete updated YAML."
    )
    raw = run_claude(system, user, model).strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        end = -1 if lines[-1].strip() == "```" else len(lines)
        raw = "\n".join(lines[1:end])
    return yaml.safe_load(raw)


def load_file(path):
    if not os.path.exists(path):
        return ""
    with open(path) as f:
        return f.read().strip()


_FREQUENCY_DAYS = {
    "daily": 1,
    "every_2_days": 2,
    "every_3_days": 3,
    "weekly": 7,
    "biweekly": 14,
}


def last_entry_date(history):
    for line in reversed(history.splitlines()):
        if line.startswith("## Entry "):
            try:
                return datetime.fromisoformat(line[9:].strip()).date()
            except ValueError:
                continue
    return None


def is_due(plan, history):
    freq = plan.get("frequency", "daily")
    if freq == "never":
        return False
    interval = _FREQUENCY_DAYS.get(freq, 1)
    if interval <= 1:
        return True
    last = last_entry_date(history)
    if last is None:
        return True
    return (date.today() - last).days >= interval


def extract_covered_topics(history):
    """Return a list of topic strings logged in ## Entry blocks."""
    topics = []
    lines = history.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("## Entry "):
            for j in range(i + 1, len(lines)):
                text = lines[j].strip()
                if text and text != "---" and not text.startswith("#"):
                    topics.append(text)
                    break
        i += 1
    return topics


def build_prompts(plan, history):
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
    else:
        user_parts.append(
            "This is the first session for this subject. Start from the very beginning."
        )

    user_parts.append(
        f"Generate the next {plan.get('format', 'tutorial')} session content for this subject."
    )

    return system, "\n\n".join(user_parts)


def run_claude(system, user, model):
    result = subprocess.run(
        ["claude", "--model", model,
         "--system-prompt", system,
         "--tools", "",
         "--no-session-persistence",
         "-p", user],
        capture_output=True, text=True, timeout=120,
        cwd=tempfile.gettempdir(),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "claude CLI exited with non-zero status")
    return result.stdout.strip()


def extract_topic(content):
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
        if line:
            return line[:80] + ("..." if len(line) > 80 else "")
    return "Learning session"


def format_entry(timestamp, topic):
    return f"## Entry {timestamp}\n\n{topic}\n\n---\n"


def main():
    args = parse_args()

    try:
        config = load_config(args.config)
        plan = load_plan(args.subject_dir)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    history = load_file(os.path.join(args.subject_dir, "history.md"))

    if not is_due(plan, history):
        sys.exit(2)  # signal to kf.sh: not due today, skip silently

    feedback = load_file(os.path.join(args.subject_dir, "feedback.md"))

    model_generation = config["anthropic"]["model_generation"]
    model_utility = config["anthropic"]["model_utility"]

    if feedback:
        try:
            plan = apply_feedback_to_plan(model_utility, plan, feedback)
            save_plan(args.subject_dir, plan)
            with open(os.path.join(args.subject_dir, "feedback.md"), "w") as f:
                f.write("")
        except Exception as e:
            print(f"WARNING: failed to apply feedback to plan, using original: {e}", file=sys.stderr)

    system, user = build_prompts(plan, history)

    try:
        content = run_claude(system, user, model_generation)
    except Exception as e:
        print(f"ERROR: claude CLI call failed: {e}", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.now().isoformat(timespec="seconds")
    entry = format_entry(timestamp, extract_topic(content))
    new_history = (history + "\n\n" + entry).lstrip() if history else entry

    with open(os.path.join(args.subject_dir, "history.md"), "w") as f:
        f.write(new_history)

    subject_name = plan.get("subject", os.path.basename(args.subject_dir))
    print(f"=== {subject_name} ===\n")
    print(content)
    print()


if __name__ == "__main__":
    main()
