# vibecoding-ci-kit

[English](README.md) · [Chinese](README.zh.md)

**vibecoding-ci-kit** turns a GitLab application repo into an AI-assisted engineering workflow: local agents work from your project facts, CI reviews feature branches and MRs against those facts, `@claude` turns GitLab comments into code changes, and `memory-bank` keeps project knowledge alive after merge.

This repository is not application code. Copy **the contents of** `repo/` into your **GitLab application repo root** to add CI, hooks, rules, skills, and docs.

**CI:** GitLab only for now.

## Watch first

https://github.com/user-attachments/assets/40d8c7e5-49ab-446d-ae7b-3672d34e7237

[Open the interactive walkthrough](https://apri1qing.github.io/vibecoding-ci-kit/presentation.html?lang=en)

## Prerequisites

1. **Branches:** develop on `feature/<name>`, then merge into `integration/...` (or change `rules:` in `.gitlab-ci.yml` so CI matches your branch names).
2. **Feishu email identity, if Feishu is enabled:** align Git commit author email, GitLab Public email, and the Feishu directory email. `feature-review` uses Git commit author email; `mr-review` and `@claude` prefer GitLab Public email.

## Installation

### Recommended: Agent onboarding

Clone this repository, then ask your coding agent to read [`vibecoding-workflow-onboarding`](.claude/skills/vibecoding-workflow-onboarding/SKILL.md) and help onboard `repo/` into your target GitLab application repo.

This is strongly recommended. The agent can merge files, resolve conflicts, and walk through GitLab variables, Runner setup, Feishu options, and `@claude` webhook setup with fewer missed steps than manual copying.

Want to install by hand? Jump to [Manual installation](#manual-installation).

## What you get

| Capability | Benefit |
|------------|---------|
| Local development conventions | Agents read `AGENTS.md`, `memory-bank`, rules, hooks, and skills before acting, so work starts from project facts instead of a blank chat. |
| Feature docs loop | On `feature/*`, tech docs become the technical truth page and test plans become verification evidence; keyword-triggered hooks keep requirements, APIs, TODOs, and test cases in sync. |
| `feature-review` | Runs on push to `feature/*`, catching problems early during development. |
| `mr-review` | Runs on MRs to `integration/*` or `integration-*`, using the complete MR diff and project context as a pre-merge gate. |
| `@claude` | GitLab commit or MR comments that mention `@claude` can become follow-up code changes. |
| Feishu notifications | Review and assist results can be written back to GitLab and sent to the right person in Feishu. |
| Memory bank retention | After an MR is merged, the push to `integration/*` triggers `update-memory-bank`, refreshing long-lived project knowledge automatically. |

## Local development: agents work from project facts

Onboarding brings `AGENTS.md`, `memory-bank`, `.claude/rules/`, hooks, and skills into your application repo. Together they tell agents what to read first, which project rules to follow, and when feature docs or test plans should be synchronized.

**Core files**

| File | Role |
|------|------|
| `AGENTS.md` | Repo entrypoint for agents, including reading strategy and working expectations. |
| `memory-bank/` | Long-lived project knowledge: product context, architecture, tech stack, current work, feature docs, and test docs. |
| `.claude/rules/coding-standards.md` | Shared coding conventions, extendable through the coding-rule hook. |
| `.claude/rules/memory-bank-framework.md` | Memory-bank layout, feature tech doc naming, and update rules; when the user says `update memory bank`, the agent reconciles memory-bank files by this rule. |

**Hooks**

| Hook | Role |
|------|------|
| `code-review-trigger.py` | When the user asks for code review, refactor, or "per project rules", the agent reads `.claude/rules/` first. |
| `coding-rule-trigger.py` | When the user asks to remember a rule, the agent appends it to `coding-standards.md`. |
| `feature-tech-doc-sync-trigger.py` | Keeps feature technical docs aligned when requirements, design, APIs, or TODOs drift. |
| `test-plan-sync-trigger.py` | Routes test plan and test case updates through the `test-plan` skill. |

**Skills**

| Skill | Role |
|-------|------|
| `ci-code-review` | Defines CI `feature-review` / `mr-review` inputs and report shape through `CODE_REVIEW_REPORT_LANGUAGE`. |
| `feature-tech-doc` | Defines `memory-bank/docs/features/*-tech-doc.md`. |
| `test-plan` | Defines feature verification plans, such as `memory-bank/docs/tests/`. |

## GitLab Review: gated by project facts

`feature-review` and `mr-review` are not generic style comments. They check whether code changes match the repo's own facts.

| Compare | `feature-review` | `mr-review` |
|---------|------------------|-------------|
| Trigger | Push to `feature/*`. | MR targeting `integration/*` or `integration-*`. |
| Purpose | Catch problems early while development is still in progress. | Run a stricter pre-merge gate. |
| Facts used | Branch snapshot or incremental diff, `.claude/rules/*.md`, the matching `memory-bank/docs/features/*-tech-doc.md`, and the `ci-code-review` skill. | Complete MR diff, `.claude/rules/*.md`, feature tech docs, `memory-bank/systemPatterns.md`, `memory-bank/techContext.md`, `memory-bank/performance.md`, and the `ci-code-review` skill. |

## Manual installation

1. Copy `repo/` into your application repo:

   ```bash
   rsync -a repo/ /path/to/your/app/
   ```

   Resolve conflicts if needed. CI runs in the application repo, not in this kit repo.

2. Configure GitLab CI/CD variables.

   Manage tokens and secrets as GitLab protected or masked CI/CD variables where appropriate.

   **Required GitLab access**

   - `GITLAB_API_TOKEN`: GitLab API token. PAT scopes: `api`, `read_repository`, and `write_repository`; write access is needed for `claude-assist` and `update-memory-bank` to push commits.
   - `GITLAB_TRIGGER_TOKEN`: pipeline trigger token used by the webhook listener to start `claude-assist`.

   **Choose one Claude authentication method**

   - `ANTHROPIC_API_KEY`: Anthropic API key authentication.
   - `CLAUDE_CODE_OAUTH_TOKEN`: OAuth token from `claude setup-token`, usually starting with `sk-ant-oat01-`.

   **Optional runtime settings**

   - `ANTHROPIC_BASE_URL`: custom Anthropic endpoint for internal mirrors or corporate proxies.
   - `CLAUDE_MODEL`: model passed to `claude` in CI; default is defined in `repo/.gitlab-ci.yml`.
   - `CODE_REVIEW_REPORT_LANGUAGE`: review report language; default is `zh`, set `en` for English.

   **Optional Feishu notifications**

   - `FEISHU_APP_ID`: Feishu app id.
   - `FEISHU_APP_SECRET`: Feishu app secret.
   - `FEISHU_DEFAULT_NOTIFY_EMAIL`: fallback recipient when author identity cannot be resolved.

3. Prepare the GitLab Runner host.

   Use GitLab Runner. The OS user that runs jobs must have `claude` and `jq` on `PATH` for `feature-review`, `mr-review`, `claude-assist`, and `update-memory-bank`. Register the Runner and keep it online before pushing, otherwise jobs remain pending.

4. Enable `@claude` comments on commits and MRs.

   On the same Runner host, copy [`runner/.claude/skills/gitlab-runner-onboarding/`](runner/.claude/skills/gitlab-runner-onboarding/) to that environment, or to `~/.claude/skills/gitlab-runner-onboarding`. Open it with Claude and follow its `SKILL.md` to configure the webhook listener and `GITLAB_TRIGGER_TOKEN`.

## License

MIT - [LICENSE](LICENSE).
