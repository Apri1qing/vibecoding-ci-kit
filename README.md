# vibecoding-ci-kit

[English](README.md) · [Chinese](README.zh.md)

**vibecoding-ci-kit** is not application code — copy **the contents of** **`repo/`** into your **GitLab application repo root** (see [If you are a human](#if-you-are-a-human) step **1**) to add CI, hooks, and docs. English by default unless your team says otherwise.

**CI:** **GitLab** only for now.

## Prerequisites

1. **Clone** this repository.
2. **Branches:** develop on **`feature/<name>`**, then merge into **`integration/...`** (or change **`rules:`** in **`.gitlab-ci.yml`** so CI matches your branch names).

---

## What you get

| What | When |
|------|------|
| **Level 1 AI review** | Push **`feature/*`** |
| **Level 2 AI review (MR)** | MR to **`integration/*`** or **`integration-*`** |
| **`@claude`** (comment on **commit** / **MR**) | Leave a **comment on GitLab** (commit or merge request) that mentions **`@claude`** and your request — that **triggers a pipeline** so Claude can apply changes.|
| **Memory bank** + **`update-memory-bank`** | Push **`integration/*`**; keep in sync via **`AGENTS.md`** + rules |

### `repo/.claude/` (and merge root)

| File | Role |
|------|------|
| **`settings.json`** | Required so **hooks** run on **user prompt submit**; without it, scripts in **`hooks/`** never run. |

| Hooks | Role |
|-------|------|
| **`code-review-trigger.py`** | Code review / refactor / “per rules” → read **`.claude/rules/`** first. |
| **`coding-rule-trigger.py`** | “Remember a rule” → append a line to **`coding-standards.md`**. |
| **`feature-tech-doc-sync-trigger.py`** | Tech doc sync / drift → **`memory-bank/docs/features/`**. |
| **`test-plan-sync-trigger.py`** | Test plan / TC sync → **test-plan** skill first. |

| Rules | Role |
|-------|------|
| **`coding-standards.md`** | Shared conventions (+ coding-rule hook). |
| **`memory-bank-framework.md`** | Layout; **`feature/*`** ↔ **`docs/features/*-tech-doc.md`**. |

| Skills | Role |
|--------|------|
| **`ci-code-review`** | CI `feature-review` / `mr-review` stdin + report shape (`CODE_REVIEW_REPORT_LANGUAGE`). |
| **`feature-tech-doc`** | **`memory-bank/docs/features/*-tech-doc.md`**. |
| **`test-plan`** | Test plans (e.g. **`memory-bank/docs/tests/`**). |

Also: **`CLAUDE.md`**, **`AGENTS.md`**.

---

## If you are a human

1. **[Prerequisites](#prerequisites)** — from the clone that contains **`repo/`**:

   ```bash
   rsync -a repo/ /path/to/your/app/
   ```

   Fix conflicts if needed. CI runs **in the app repo**.

2. **GitLab → CI/CD → Variables**

   | Variable | Required | Mask | Purpose |
   |----------|---------|------|---------|
   | `GITLAB_API_TOKEN` | Yes | ✅ | GitLab API in CI. PAT scopes: `api` + `read_repository` + `write_repository` (write needed for `claude-assist` and `update-memory-bank` to push commits). |
   | `GITLAB_TRIGGER_TOKEN` | Yes | ✅ | Pipeline trigger token; webhook listener starts `claude-assist`. |
   | `ANTHROPIC_API_KEY` | Auth Method 1 | ✅ | Anthropic API key authentication. See `gitlab-runner-onboarding` §1.2 Method 1. |
   | `ANTHROPIC_BASE_URL` | Optional | ❌ | Override Anthropic API endpoint (internal mirror or corporate proxy). Set alongside `ANTHROPIC_API_KEY` when needed. |
   | `CLAUDE_CODE_OAUTH_TOKEN` | Auth Method 2 | ✅ | OAuth token (from `claude setup-token`; starts with `sk-ant-oat01-`). See `gitlab-runner-onboarding` §1.2 Method 2. |

   | Variable | Default (see **`repo/.gitlab-ci.yml`**) | Mask | Purpose |
   |----------|------------------------------------------|------|---------|
   | `CODE_REVIEW_REPORT_LANGUAGE` | **`zh`** | ❌ | Review report language; set **`en`** for English. |
   | `CLAUDE_MODEL` | **`claude-sonnet-4-6`** | ❌ | Model passed to `claude` in CI. |
   | `FEISHU_APP_ID` | *(unset)* | ❌ | Feishu app_id; if unset, Feishu notifications are skipped. |
   | `FEISHU_APP_SECRET` | *(unset)* | ✅ | Feishu app_secret; if unset, Feishu notifications are skipped. |

   > **Mask** column: ✅ = must be masked (contains secrets); ❌ = no need to mask. GitLab only allows masking when the value contains no `$`, `\n`, etc., and is ≤ 32 characters in some setups.

3. **GitLab Runner host:** use **GitLab Runner** (not a generic CI agent). The OS user that runs jobs must have **`claude`** + **`jq`** on **`PATH`** (for `feature-review`, `mr-review`, `update-memory-bank`, …). **Runner must be registered and online before you push** — otherwise jobs stay `pending` indefinitely.

4. **`@claude` (comments on commits / MRs):** on the **same Runner host**, copy **[`runner/.claude/skills/gitlab-runner-onboarding/`](runner/.claude/skills/gitlab-runner-onboarding/)** to that environment (or to `~/.claude/skills/gitlab-runner-onboarding`), open it in Claude, and follow **[`SKILL.md`](runner/.claude/skills/gitlab-runner-onboarding/SKILL.md)** for the webhook listener and **`GITLAB_TRIGGER_TOKEN`** setup.

5. **Memory bank:** **CI** — after merge to **`integration/*`**, **`update-memory-bank`** on the next push (no GitLab prompt); uses **`AGENTS.md`** + **`.claude/rules/memory-bank-framework.md`**. **Chat** — full pass when the user says **`update memory bank`** (framework **Update Rules §3**); smaller edits per §1–2 / §4–5.

---

## If you are an agent

1. Load **[`vibecoding-workflow-onboarding`](.claude/skills/vibecoding-workflow-onboarding/SKILL.md)** (`~/.claude/skills/`).

2. **Memory bank — tell the user what it is and how to use / update it**

   - **What it is:** **`memory-bank/`** is the app repo’s **long-lived project knowledge** (scope, product context, architecture, stack, current work, **`docs/`** for features and tests). It is not source code; it keeps humans and agents aligned across sessions. Details: **`AGENTS.md`**, **Reading strategy** in **`memory-bank-framework.md`**.

   - **How to update:** Ongoing edits follow **Update Rules** §1–2 / §4–5 in **`memory-bank-framework.md`**. When the user asks to **`update memory bank`**, do a **full reconciliation** of every **core** root file per **§3** (not only `activeContext` / `progress`). On **`feature/*`**, keep the paired **`docs/features/*-tech-doc.md`** aligned with the branch. **CI** refreshes **`memory-bank/`** on push to **`integration/*`** — see **[If you are a human](#if-you-are-a-human)** step **5** above.

---

## License

MIT — [LICENSE](LICENSE).
