# vibecoding-ci-kit onboarding (reference)

Canonical detail for **`vibecoding-workflow-onboarding`** lives **in this skill folder** (`SKILL.md` + `references/`).

---

## Clone and merge (Track A)

1. **Clone** the **vibecoding-ci-kit** repository (full clone so **`repo/`** and **`runner/.claude/skills/gitlab-runner-onboarding/`** exist).
2. From the **kit clone root**, copy the merge bundle into your **GitLab application repo root** (resolve conflicts if needed):

   ```bash
   rsync -a repo/ /path/to/your/app/
   ```

3. CI runs **in the application repo** after merge — not in the kit repo root.

---

## Three layers

| Layer | Purpose |
|-------|---------|
| **Kit repo** | Supplies **`repo/`** + Runner skill tree; this skill describes what goes where |
| **`repo/`** | Merge at **application repo root**: `.gitlab-ci.yml`, `.gitlab/`, `.claude/`, `memory-bank/`, `CLAUDE.md`, `AGENTS.md` |
| **`runner/.claude/skills/gitlab-runner-onboarding/`** | **Runner host only** — not merged into the app |

---

## Glossary

| Term | Meaning |
|------|---------|
| **Kit clone root** | Directory containing **`repo/`** and **`runner/.claude/skills/gitlab-runner-onboarding/`** |
| **Track A** | Developer: merge **`repo/`**, variables, CI lint — **`vibecoding-workflow-onboarding`** |
| **Track B** | Runner host: shell Runner + webhook — **`gitlab-runner-onboarding`** (separate session) |
| **Why CI is not in the kit root** | **`.gitlab-ci.yml`** ships under **`repo/`** and is merged into the **application** repo; pipelines run there |

---

## GitLab CI/CD variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes | Claude API for CI jobs |
| `GITLAB_API_TOKEN` | Yes | PAT with scopes your jobs need |
| `GITLAB_TRIGGER_TOKEN` | For `@claude` | Pipeline trigger token |
| `CLAUDE_MODEL` | No | Model id |
| `FEISHU_APP_TOKEN` | No | Feishu notifications |
| `CODE_REVIEW_REPORT_LANGUAGE` | No | `zh` or `en` |

---

## Merge `repo/` (file checklist)

- `.gitlab-ci.yml`, `.gitlab/`
- `.claude/settings.json` — **required** for **UserPromptSubmit** hooks; without it, **`.claude/hooks/`** scripts are not registered
- `.claude/hooks/`
- `.claude/rules/` (`memory-bank-framework.md`, `coding-standards.md`; add project-specific `*.md` as needed)
- `.claude/skills/` (`ci-code-review`, `feature-tech-doc`, `test-plan`)
- `memory-bank/` skeleton + `memory-bank/docs/features/` (and `memory-bank/docs/tests/` if you use test plans), `CLAUDE.md`, `AGENTS.md`

---

## Branch naming (default)

| Pattern | CI |
|---------|-----|
| `feature/*` | Level 1 `feature-review` |
| MR → `integration/*` or `integration-*` | Level 2 `mr-review` |
| push `integration/*` | Optional `update-memory-bank` |

Align with **`.claude/rules/memory-bank-framework.md`**, **`.gitlab-ci.yml`** `rules:`, and your app’s branches.

---

## Track B (Runner)

- Shell Runner, `claude` + `jq` on PATH; Python venv for webhook (`gunicorn`, `flask`, `requests` per **`runner/.claude/skills/gitlab-runner-onboarding/SKILL.md`**).
- Copy **`runner/.claude/skills/gitlab-runner-onboarding/`** to the host (or install under `~/.claude/skills/gitlab-runner-onboarding`); use that SKILL on the Runner machine (separate Claude session).

---

## Handoff checklist (Track A → B)

| Item | Note |
|------|------|
| GitLab project URL | |
| `repo/` merged | ✓ / pending |
| CI variables set | |
| `GITLAB_TRIGGER_TOKEN` + webhook | for `@claude` |
| Bundle on Runner | path to `runner/.claude/skills/gitlab-runner-onboarding/` |
| Next | On Runner: **gitlab-runner-onboarding** skill |

**Runner session one-liner:** Follow **`gitlab-runner-onboarding`**: register shell runner, deploy **`scripts/webhook-listener.py`**, `.env` + GitLab webhook — **`runner/.claude/skills/gitlab-runner-onboarding/SKILL.md`**.

---

## Triggers and `@claude`

Webhook (Comments) → listener → Trigger API with `GITLAB_TRIGGER_TOKEN`. Job `claude-assist` when `CI_PIPELINE_SOURCE == trigger` and vars match `.gitlab-ci.yml`. Details: **`runner/.claude/skills/gitlab-runner-onboarding/SKILL.md`**.

---

## Agent roles

| Role | Skill |
|------|--------|
| Developer / app repo | **`vibecoding-workflow-onboarding`** |
| Runner host | **`gitlab-runner-onboarding`** only |
