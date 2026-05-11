Set up a daily scheduled run of KnowledgeFeeder on macOS using launchd.

1. Ask the user what time they want the daily push delivered (default: 9:00 AM).
2. Ask whether they want to use launchd (recommended, more reliable on macOS) or crontab.

If launchd:
- Create a plist file at `~/Library/LaunchAgents/com.knowledgefeeder.plist` with the chosen time and the full absolute path to `kf.sh run`.
- Run `launchctl load ~/Library/LaunchAgents/com.knowledgefeeder.plist` to activate it.
- Run `launchctl list | grep knowledgefeeder` to confirm it is loaded.
- Schedule a daily pmset wake 5 minutes BEFORE the chosen time so the Mac is fully awake when launchd fires (launchd's StartCalendarInterval is unreliable if the system wakes at the exact same moment):
  `sudo pmset repeat wake MTWRFSU HH:MM:00` (subtract 5 minutes from the chosen time, zero-padded).
  IMPORTANT: pmset requires sudo and cannot be run by Claude. After completing all other steps, explicitly tell the user:
  "⚠️ One manual step required — run this in your terminal to finish setup:
  sudo pmset repeat wake MTWRFSU HH:MM:00
  Without this, the Mac must already be awake at the scheduled time for the job to run."
- Tell the user they can run `/kf-unsubs` to undo everything.

If crontab:
- Show the user the exact crontab line to add, with the correct absolute path to `kf.sh`.
- Offer to open crontab for them with `crontab -e`.

In both cases, log output goes to `kf.log` in the project root.
