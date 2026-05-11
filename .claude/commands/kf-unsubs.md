Unsubscribe from KnowledgeFeeder's scheduled daily runs. This undoes everything /kf-schedule set up.

Run the following steps in order:

1. Unload the launchd agent (ignore errors if it was never loaded):
   `launchctl unload ~/Library/LaunchAgents/com.knowledgefeeder.plist`

2. Delete the plist file (ignore errors if it doesn't exist):
   `rm -f ~/Library/LaunchAgents/com.knowledgefeeder.plist`

3. Run `launchctl list | grep knowledgefeeder` and `pmset -g sched` to confirm the launchd side is gone.

4. Tell the user:
   "⚠️ One manual step required — run this in your terminal to cancel the scheduled wake:
   sudo pmset repeat cancel
   Without this, macOS will still wake your Mac at the old scheduled time."

5. Tell the user everything else has been removed and they can re-run `/kf-schedule` at any time to set it up again.
