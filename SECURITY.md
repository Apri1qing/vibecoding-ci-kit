# Security

## Reporting

Do **not** post live tokens or full CI logs with secrets in public issues.

Contact maintainers through a private channel you agree on (e.g. confidential issue or email).

## For operators

- Store `ANTHROPIC_API_KEY`, `GITLAB_API_TOKEN`, `GITLAB_TRIGGER_TOKEN` as **masked** (and **protected** if appropriate) CI variables.
- Set `WEBHOOK_SECRET` and match it in the GitLab webhook configuration.
- Rotate tokens periodically.
- Run a secret scanner on your fork before publishing (e.g. gitleaks, trufflehog).
