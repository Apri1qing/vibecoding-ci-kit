# Setup

## 1. GitLab CI/CD variables

**Settings → CI/CD → Variables**

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key (masked) |
| `GITLAB_API_TOKEN` | Yes for posting comments / git push | Project access token with scopes you need |
| `GITLAB_TRIGGER_TOKEN` | Yes for `@claude` | Pipeline trigger token |
| `FEISHU_APP_TOKEN` | No | Feishu app token for optional DMs |

Use placeholders in docs only, e.g. `glpat-xxx`, never real values.

## 2. Runner

- **Executor**: `shell`
- Install **Claude Code CLI** and **jq**
- If `claude` is not on default `PATH`, set `RUNNER_EXTRA_PATH` (example: `/opt/homebrew/bin` on macOS)

## 3. Webhook (`@claude`)

1. On a host reachable by GitLab, install dependencies: `pip install -r webhook/requirements.txt`
2. Copy `webhook/.env.example` to `.env`, set `GITLAB_URL`, `GITLAB_API_TOKEN`, `GITLAB_TRIGGER_TOKEN`, optional `WEBHOOK_SECRET`
3. Run the app (e.g. gunicorn) so `POST /gitlab-webhook` is available
4. **Project → Webhooks**: URL to your listener, **Comments** enabled, secret matches `WEBHOOK_SECRET`
5. Trigger API variables must match `.gitlab-ci.yml` `claude-assist` rules, including `AI_FLOW_EVENT=comment` and `AI_FLOW_MR_IID` for MR comments

## 4. Branch conventions

- Level 1: `feature/*`
- Level 2: MR target `integration/*` or `integration-*`
- Tech doc path: `{AI_REVIEW_DOC_BASE}/{slug}-tech-doc.md` (default base `docs/features`)

## 5. Feishu

Optional. The report must follow `.claude/skills/code-review-report/SKILL.md` so the risk table parses correctly (English **Summary** and **Risk assessment** table).
