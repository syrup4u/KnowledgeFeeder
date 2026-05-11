# KnowledgeFeeder — project notes for Claude

## Architecture in one paragraph

`kf.sh run` drives the full pipeline: (1) `check_email.py` fetches inbox replies and uses Claude (utility model) to classify feedback by subject, writing each chunk to `subjects/<name>/feedback.md`; (2) for each subject that is due today, `generate.sh` calls `generate_content.py`; (3) `send_email.py` assembles and sends one combined email (or .md attachment if it exceeds the size limit).

## Key files

| File | Role |
|---|---|
| `scripts/generate_content.py` | Core generation loop: load plan → apply feedback → generate → append history → compact |
| `scripts/check_email.py` | IMAP fetch + Claude-based feedback classification |
| `scripts/send_email.py` | SMTP send; renders markdown to HTML |
| `subjects/<name>/plan.md` | YAML front matter only; the single source of truth for how content is generated |
| `subjects/<name>/history.md` | Append log of past sessions; compacted by Claude when entry count hits threshold |
| `subjects/<name>/feedback.md` | One-shot queue; cleared after feedback is applied to plan.md |

## Feedback flow (permanent, not one-shot)

When `feedback.md` is non-empty, `generate_content.py` calls `apply_feedback_to_plan()` (utility model) before generating. Claude reads the current `plan.md` YAML and the feedback, then returns updated YAML. The updated YAML is written back to `plan.md` and `feedback.md` is cleared. Content is then generated purely from the updated plan — feedback never appears in the generation prompt directly.

Side-effect: PyYAML round-trip drops inline comments from `plan.md` after the first feedback application.

## Config

`config.yaml` (not committed). Fields: `email.*` (SMTP/IMAP creds) and `anthropic.model_generation` / `anthropic.model_utility`. Generation uses Sonnet; utility tasks (feedback application, compaction, classification) use Haiku.

## Frequency gating

Each plan has a `frequency` field. `is_due()` in `generate_content.py` reads the last `## Entry <timestamp>` line from `history.md` and skips generation if not enough days have passed. Exit code 2 = not due (silent skip in `kf.sh`).

## History compaction

When `count_entries(history) >= compaction_threshold`, the full history is summarized by Claude (utility model) into a single `## Compacted Summary` block. The threshold and summary length are set per-subject in `plan.md`.

## Claude Code commands

Defined in `.claude/commands/`: `kf-setup.md`, `kf-add.md`, `kf-schedule.md`. These are the primary onboarding surface — users run `/kf-setup`, `/kf-add`, `/kf-schedule` inside Claude Code.
