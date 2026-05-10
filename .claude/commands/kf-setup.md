Set up KnowledgeFeeder by doing the following steps in order:

1. Run `pip3 install -r requirements.txt` and confirm it succeeds.
2. Run `claude --version` to confirm the CLI is available.
3. Check whether `config.yaml` exists.
   - If it does not exist: copy `config.yaml.example` to `config.yaml`, then tell the user exactly what they need to fill in (email address, app password). For Gmail, remind them to use an App Password from https://myaccount.google.com/apppasswords, not their main password.
   - If it does exist: verify it has the required keys (`email.address`, `email.password`, `anthropic.model_generation`, `anthropic.model_utility`) and flag any that are still placeholder values.
4. Run `./kf.sh list` to show current subjects.
5. Give the user a clear summary: what's ready, what still needs action, and suggest running `/kf-add` to add their first subject.
