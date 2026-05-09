# KnowledgeFeeder

A personal learning system that generates daily AI-powered content for any subject you want to study and delivers it to your inbox. Reply to the email with freeform feedback — the system reads it, figures out which subjects you're talking about, and applies it the next time content is generated.

Content is generated via the `claude` CLI — no API key required, auth is handled by your existing Claude Code login. Sonnet is used for content generation; Haiku for lighter tasks (feedback classification and history compaction).

## How it works

1. Each subject lives in its own folder under `subjects/` with a `plan.md` that controls format, depth, and topics.
2. Running `./kf.sh run` fetches any feedback from your inbox, generates new content for every subject, and sends one combined email.
3. Reply to the email in plain English. The next run classifies your reply by subject and queues it as feedback.
4. Once feedback is incorporated into generation, it is cleared automatically.
5. After a configurable number of entries, `history.md` is compacted by Claude so the context stays lean.

## Setup

**1. Install the `claude` CLI and log in**

Download [Claude Code](https://claude.ai/code) and authenticate. The scripts call `claude` as a subprocess — no API key needed in config.

**2. Install Python dependencies**

```bash
pip3 install -r requirements.txt
```

**3. Configure credentials**

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` with your email address and app password.  
For Gmail, generate an [App Password](https://support.google.com/accounts/answer/185833) — do not use your main account password.

**4. Add your first subject**

```bash
./kf.sh add "Rust Programming"
```

Then edit `subjects/rust_programming/plan.md` to set your learning goals, format, and depth.

**5. Run**

```bash
./kf.sh run
```

## CLI

| Command | Description |
|---|---|
| `./kf.sh add "Subject Name"` | Scaffold a new subject folder with a template `plan.md` |
| `./kf.sh run` | Full pipeline: fetch feedback → generate content → send email |
| `./kf.sh update` | Fetch inbox and dispatch feedback only (no generation) |
| `./kf.sh list` | List all subjects |

## Subject folder structure

```
subjects/rust_programming/
├── plan.md       # learning plan: format, depth, topics, compaction settings
├── history.md    # append log of all generated content; compacted automatically
├── feedback.md   # queued feedback from your email replies; cleared after use
└── generate.sh   # called by kf.sh run — invokes the claude CLI for this subject
```

### config.yaml structure

```yaml
email:
  smtp_host: smtp.gmail.com
  smtp_port: 587
  imap_host: imap.gmail.com
  imap_port: 993
  address: you@example.com
  password: "your-app-password"
  body_size_limit_kb: 50       # send as attachment if body exceeds this

anthropic:
  model_generation: claude-sonnet-4-6        # content generation
  model_utility: claude-haiku-4-5-20251001   # compaction and feedback classification
```

### plan.md fields

```yaml
---
subject: Rust Programming
format: tutorial          # tutorial | flashcards | qa | summary | mixed
depth: intermediate       # beginner | intermediate | advanced
content_length: medium    # short (~300w) | medium (~600w) | long (~1200w)
compaction_threshold: 20  # compact history.md after this many entries
compaction_summary_length: short  # short | medium
focus_topics:
  - ownership and borrowing
  - async/await
language: English
extra_instructions: |
  Always include a runnable code example.
---
```

## Scheduling (macOS)

Add to your crontab to run every morning at 9:00 AM:

```bash
crontab -e
# add this line:
0 9 * * * /bin/zsh /path/to/KnowledgeFeeder/kf.sh run >> /path/to/KnowledgeFeeder/kf.log 2>&1
```

Or use a launchd plist in `~/Library/LaunchAgents/` for more reliable macOS scheduling.

## File layout

```
KnowledgeFeeder/
├── config.yaml.example   # credential template (copy to config.yaml)
├── kf.sh                 # main CLI
├── requirements.txt      # pip dependencies
├── scripts/
│   ├── generate_content.py   # claude CLI: generate content, manage history and compaction
│   ├── send_email.py         # SMTP: send combined email or .md attachment
│   └── check_email.py        # IMAP: fetch replies, classify feedback via claude CLI
└── subjects/
    └── <subject_name>/
        ├── plan.md
        ├── history.md
        ├── feedback.md
        └── generate.sh
```
