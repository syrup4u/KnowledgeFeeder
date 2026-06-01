# KnowledgeFeeder — project notes for Claude

## Architecture in one paragraph

`kf.sh run` drives the full pipeline: (1) `check_email.py` fetches inbox replies and uses Claude (utility model) to classify feedback by subject, writing each chunk to `subjects/<name>/feedback.md`; (2) for each subject that is due today, `generate.sh` calls `generate_content.py`; (3) `send_email.py` sends one email per subject. `kf.sh run <slug>` runs a single subject only.

## Key files

| File | Role |
|---|---|
| `scripts/generate_content.py` | Core generation loop: load plan → apply feedback → generate → append history |
| `scripts/check_email.py` | IMAP fetch + Claude-based feedback classification |
| `scripts/send_email.py` | SMTP send; renders markdown to HTML |
| `subjects/<name>/plan.md` | YAML front matter only; the single source of truth for how content is generated |
| `subjects/<name>/history.md` | Append log of past sessions — one line per session (topic only, no full content) |
| `subjects/<name>/feedback.md` | One-shot queue; cleared after feedback is applied to plan.md |

## Feedback flow (permanent, not one-shot)

When `feedback.md` is non-empty, `generate_content.py` calls `apply_feedback_to_plan()` (utility model) before generating. Claude reads the current `plan.md` YAML and the feedback, then returns updated YAML. The updated YAML is written back to `plan.md` and `feedback.md` is cleared. Content is then generated purely from the updated plan — feedback never appears in the generation prompt directly.

Side-effect: PyYAML round-trip drops inline comments from `plan.md` after the first feedback application.

## Config

`config.yaml` (not committed). Fields: `email.*` (SMTP/IMAP creds) and `anthropic.model_generation` / `anthropic.model_utility`. Generation uses Sonnet; utility tasks (feedback application, classification) use Haiku.

## Frequency gating

Each plan has a `frequency` field. Valid values: `daily`, `every_2_days`, `every_3_days`, `weekly`, `biweekly`, `never`. `is_due()` in `generate_content.py` reads the last `## Entry <timestamp>` line from `history.md` and skips generation if not enough days have passed. `never` always returns not-due (effectively disables/unsubscribes the subject). Exit code 2 = not due (silent skip in `kf.sh`).

## History format

Each entry in `history.md` is a single line recording just the topic covered:

```
## Entry 2026-05-31T10:00:00

Introduction to Python decorators

---
```

`extract_covered_topics()` reads these to build the "do not repeat" list for the generation prompt.

## Claude Code commands

Defined in `.claude/commands/`: `kf-setup.md`, `kf-add.md`. These are the primary onboarding surface — users run `/kf-setup` and `/kf-add` inside Claude Code.
