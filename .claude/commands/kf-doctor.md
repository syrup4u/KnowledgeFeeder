Diagnose and fix errors from the last KnowledgeFeeder run.

1. Read `kf.log` from the project root.
   - If the file is empty or missing, tell the user the last run was clean and stop.
   - Otherwise, extract and summarise every ERROR line, grouping by subject slug and error type.

2. For each distinct error, investigate the root cause:
   - Generation failure (`generate_content.py` crashed): read the script and the affected subject's `plan.md` to find what went wrong.
   - Email send failure (`send_email.py` failed): check config.yaml for SMTP credentials and the script for bugs.
   - Feedback fetch failure (`check_email.py` failed): check IMAP credentials and the script.
   - Any Python traceback in the log: read the relevant script and fix the bug.

3. Apply fixes directly (edit scripts, fix plan.md issues, etc.). Explain each fix briefly.

4. After fixing, offer to re-run the affected subjects:
   - If one subject failed: `./kf.sh run <slug>`
   - If multiple failed: `./kf.sh run` (full run)
   - Ask the user before running.
