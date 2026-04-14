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

**Required** (must set): `GITLAB_API_TOKEN`, `GITLAB_TRIGGER_TOKEN`.  
**Optional** (have `.gitlab-ci.yml` defaults, only set to override): the rest.

| Variable | Required | Options / Default | Purpose |
|----------|----------|-------------------|---------|
| `GITLAB_API_TOKEN` | ✅ Yes | — | PAT with `api` + `read_repository` + `write_repository` scopes (`write_repository` required: `claude-assist` and `update-memory-bank` push commits via token) |
| `GITLAB_TRIGGER_TOKEN` | ✅ Yes | — | Pipeline trigger token (webhook listener → Trigger API); create at Settings → CI/CD → Pipeline triggers |
| `CODE_REVIEW_REPORT_LANGUAGE` | Optional | `zh` / `en`; default **`zh`** if unset | Review report language (`zh` = Chinese, `en` = English) |
| `CLAUDE_MODEL` | Optional | Any Anthropic model ID; default **`claude-sonnet-4-6`** if unset | Model passed to `claude` CLI in CI |
| `FEISHU_APP_TOKEN` | Optional | —; default **unset** (skip notifications) | Feishu app token; if unset, Feishu notifications are skipped but reviews still run |

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
| `GITLAB_TRIGGER_TOKEN` + webhook | Required (listener `.env` + GitLab webhook) |
| Bundle on Runner | path to `runner/.claude/skills/gitlab-runner-onboarding/` |
| Next | On Runner: **gitlab-runner-onboarding** skill |

**Runner session one-liner:** Follow **`gitlab-runner-onboarding`**: register shell runner, deploy **`scripts/webhook-listener.py`**, `.env` + GitLab webhook — **`runner/.claude/skills/gitlab-runner-onboarding/SKILL.md`**.

---

## `@claude` — comment on commit / MR

Webhook (Comments) → listener → Trigger API with `GITLAB_TRIGGER_TOKEN`. Job `claude-assist` when `CI_PIPELINE_SOURCE == trigger` and vars match `.gitlab-ci.yml`. Details: **`runner/.claude/skills/gitlab-runner-onboarding/SKILL.md`**.

---

## Agent roles

| Role | Skill |
|------|--------|
| Developer / app repo | **`vibecoding-workflow-onboarding`** |
| Runner host | **`gitlab-runner-onboarding`** only |
