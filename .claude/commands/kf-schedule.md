Set up a daily scheduled run of KnowledgeFeeder on macOS using launchd.

1. Ask the user what time they want the daily push delivered (default: 9:00 AM).
2. Ask whether they want to use launchd (recommended, more reliable on macOS) or crontab.

If launchd:
- Create a plist file at `~/Library/LaunchAgents/com.knowledgefeeder.plist` with the chosen time and the full absolute path to `kf.sh run`.
- Run `launchctl load ~/Library/LaunchAgents/com.knowledgefeeder.plist` to activate it.
- Run `launchctl list | grep knowledgefeeder` to confirm it is loaded.
- Tell the user how to unload it if they ever want to stop: `launchctl unload ~/Library/LaunchAgents/com.knowledgefeeder.plist`.

If crontab:
- Show the user the exact crontab line to add, with the correct absolute path to `kf.sh`.
- Offer to open crontab for them with `crontab -e`.

In both cases, remind the user that their Mac needs to be awake at the scheduled time, and that `kf.log` in the project root will record each run.
