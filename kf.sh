#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
SUBJECTS_DIR="$REPO_ROOT/subjects"
CONFIG="$REPO_ROOT/config.yaml"
LOG="$REPO_ROOT/kf.log"
PYTHON="$REPO_ROOT/.venv/bin/python3"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

# ── add ───────────────────────────────────────────────────────────────────────

cmd_add() {
    local name="${1:-}"
    if [[ -z "$name" ]]; then
        echo "Usage: $0 add \"Subject Name\""
        exit 1
    fi

    # Slugify: lowercase, spaces → underscores, strip non-alphanumeric
    local slug
    slug="$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -cd '[:alnum:]_')"

    local subject_dir="$SUBJECTS_DIR/$slug"
    if [[ -d "$subject_dir" ]]; then
        echo "ERROR: subject folder already exists: $subject_dir"
        exit 1
    fi

    mkdir -p "$subject_dir"

    cat > "$subject_dir/plan.md" << EOF
---
subject: $name
frequency: daily                  # daily | every_2_days | every_3_days | weekly | biweekly | never
format: tutorial                  # tutorial | flashcards | qa | summary | mixed
depth: intermediate               # beginner | intermediate | advanced
content_length: medium            # short (~300w) | medium (~600w) | long (~1200w)
focus_topics:
  - # FILL IN: e.g. "core concepts"
  - # FILL IN: e.g. "practical examples"
language: English
extra_instructions: |
  # FILL IN: any extra instructions, or remove this field
---

## Notes
Add personal notes about your learning goals here.
EOF

    touch "$subject_dir/history.md"
    touch "$subject_dir/feedback.md"

    cat > "$subject_dir/generate.sh" << 'GENEOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${1:?Usage: generate.sh <REPO_ROOT>}"
SUBJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$REPO_ROOT/.venv/bin/python3" "$REPO_ROOT/scripts/generate_content.py" \
    --subject-dir "$SUBJECT_DIR" \
    --config "$REPO_ROOT/config.yaml"
GENEOF
    chmod +x "$subject_dir/generate.sh"

    echo "Created: $subject_dir"
    echo "Next step: edit $subject_dir/plan.md to configure your learning plan."
}

# ── list ──────────────────────────────────────────────────────────────────────

cmd_list() {
    if [[ ! -d "$SUBJECTS_DIR" ]]; then
        echo "No subjects yet. Add one with: $0 add \"Subject Name\""
        return
    fi
    local found=false
    for d in "$SUBJECTS_DIR"/*/; do
        [[ -d "$d" ]] || continue
        echo "  $(basename "$d")"
        found=true
    done
    if [[ "$found" == "false" ]]; then
        echo "No subjects yet. Add one with: $0 add \"Subject Name\""
    fi
}

# ── update ────────────────────────────────────────────────────────────────────

cmd_update() {
    log "Fetching feedback from inbox..."
    "$PYTHON" "$REPO_ROOT/scripts/check_email.py" \
        --config "$CONFIG" \
        --subjects-dir "$SUBJECTS_DIR"
}

# ── run ───────────────────────────────────────────────────────────────────────

cmd_run() {
    local filter="${1:-}"
    log "=== KnowledgeFeeder run started ==="

    if [[ ! -f "$CONFIG" ]]; then
        log "ERROR: config.yaml not found. Copy config.yaml.example and fill in your credentials."
        exit 1
    fi

    if [[ ! -d "$SUBJECTS_DIR" ]] || [[ -z "$(ls -A "$SUBJECTS_DIR" 2>/dev/null)" ]]; then
        log "ERROR: no subjects found. Add one with: $0 add \"Subject Name\""
        exit 1
    fi

    # Step 1: pull in any queued feedback
    log "Step 1: Fetching feedback..."
    "$PYTHON" "$REPO_ROOT/scripts/check_email.py" \
        --config "$CONFIG" \
        --subjects-dir "$SUBJECTS_DIR" 2>>"$LOG" || log "WARNING: feedback fetch failed, continuing"

    # Step 2: generate and send one email per subject
    log "Step 2: Generating and sending content..."

    for subject_dir in "$SUBJECTS_DIR"/*/; do
        [[ -d "$subject_dir" ]] || continue
        local slug
        slug="$(basename "$subject_dir")"

        if [[ -n "$filter" && "$slug" != "$filter" ]]; then
            continue
        fi

        log "  Processing: $slug"

        local body_file
        body_file="$(mktemp /tmp/kf_body_XXXXXX)"

        local content gen_exit
        content="$(bash "$subject_dir/generate.sh" "$REPO_ROOT" 2>>"$LOG")" && gen_exit=0 || gen_exit=$?
        case $gen_exit in
            0)
                printf "%s\n" "$content" > "$body_file"
                "$PYTHON" "$REPO_ROOT/scripts/send_email.py" \
                    --config "$CONFIG" \
                    --body-file "$body_file" \
                    --subject-name "$slug" 2>>"$LOG" \
                    && log "  Sent: $slug" \
                    || log "  ERROR: failed to send email for $slug"
                ;;
            2)
                log "  Skipping: $slug (not due today)"
                ;;
            *)
                log "  ERROR: generation failed for $slug (exit $gen_exit)"
                ;;
        esac
        rm -f "$body_file"
    done

    log "=== Run complete ==="
}

# ── dispatch ──────────────────────────────────────────────────────────────────

case "${1:-}" in
    add)    cmd_add "${2:-}" ;;
    run)    cmd_run "${2:-}" ;;
    update) cmd_update ;;
    list)   cmd_list ;;
    *)
        cat << 'USAGE'
Usage: kf.sh <command> [args]

Commands:
  add "Subject Name"   Create a new subject folder with template files
  run [slug]           Full pipeline: fetch feedback → generate → send email (all subjects, or one)
  update               Fetch inbox and dispatch feedback only
  list                 List all subjects
USAGE
        exit 1
        ;;
esac
