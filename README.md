# KnowledgeFeeder

A personal learning system that generates daily AI-powered content for any subject you want to study and delivers it to your inbox. Reply to the email in plain English to give feedback — the system figures out which subjects you mean and applies it next time.

Content is generated via the `claude` CLI using Sonnet for content and Haiku for lighter tasks (feedback classification, history compaction).

---

## Quick Start

### 1. Prerequisites

- Install [Claude Code](https://claude.ai/code) and log in — no API key needed, auth is handled by the CLI.
- Copy `config.yaml.example` to `config.yaml` and fill in your email address and app password.  
  For Gmail: use an [App Password](https://support.google.com/accounts/answer/185833), not your main password.

### 2. Open in Claude Code and use these commands

| Command | What it does |
|---|---|
| `/kf-setup` | Install dependencies, verify environment, check your config |
| `/kf-add` | Add a new learning subject interactively |
| `/kf-schedule` | Set up a daily scheduled run on macOS |

That's it. Claude Code handles the rest.

---

## How it works

1. Each subject lives in its own folder under `subjects/` with a `plan.md` defining format, depth, frequency, and topics.
2. `./kf.sh run` fetches feedback from your inbox, generates content for every subject that is due today, and sends one combined email.
3. Reply to the email in plain English. The next run uses Claude to classify your reply by subject and queues it as feedback.
4. Before generating, feedback is applied by Claude to permanently update the relevant fields in `plan.md` (depth, focus topics, extra instructions, etc.), then cleared. All future sessions reflect the change.
5. After a configurable number of entries, `history.md` is compacted by Claude to keep context lean.

---

## Reference

### config.yaml

```yaml
email:
  smtp_host: smtp.gmail.com
  smtp_port: 587
  imap_host: imap.gmail.com
  imap_port: 993
  address: you@example.com
  password: "your-app-password"
  body_size_limit_kb: 50       # send as .md attachment if body exceeds this

anthropic:
  model_generation: claude-sonnet-4-6        # content generation
  model_utility: claude-haiku-4-5-20251001   # compaction and feedback classification
```

### plan.md fields

```yaml
---
subject: Japanese Learning
frequency: daily              # daily | every_2_days | every_3_days | weekly | biweekly
format: tutorial              # tutorial | flashcards | qa | summary | mixed
depth: intermediate           # beginner | intermediate | advanced
content_length: medium        # short (~300w) | medium (~600w) | long (~1200w)
compaction_threshold: 20      # compact history.md after this many entries
compaction_summary_length: short  # short | medium
focus_topics:
  - grammar patterns
  - vocabulary in context
language: English
extra_instructions: |
  Always include example sentences with translation.
---
```

### CLI

| Command | Description |
|---|---|
| `./kf.sh add "Subject Name"` | Scaffold a new subject folder with a template `plan.md` |
| `./kf.sh run` | Full pipeline: fetch feedback → generate due subjects → send email |
| `./kf.sh update` | Fetch inbox and dispatch feedback only |
| `./kf.sh list` | List all subjects |

### File layout

```
KnowledgeFeeder/
├── config.yaml.example          # copy to config.yaml and fill in credentials
├── kf.sh                        # main CLI
├── requirements.txt             # pip dependencies (pyyaml, markdown)
├── .claude/commands/
│   ├── kf-setup.md              # /kf-setup command
│   ├── kf-add.md                # /kf-add command
│   └── kf-schedule.md           # /kf-schedule command
├── scripts/
│   ├── generate_content.py      # claude CLI: generate content, manage history
│   ├── send_email.py            # SMTP: send combined email or .md attachment
│   └── check_email.py           # IMAP: fetch replies, classify feedback via claude CLI
└── subjects/
    └── <subject_name>/
        ├── plan.md              # learning plan and settings
        ├── history.md           # append log of generated sessions; compacted automatically
        ├── feedback.md          # queued feedback from email replies; cleared after use
        └── generate.sh          # per-subject wrapper, called by kf.sh run
```
