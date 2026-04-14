---
name: vibecoding-workflow-onboarding
description: Use when adopting the vibecoding-ci-kit workflow with no prior context — merge repo/ into the user's application repo (Track A), set GitLab variables, and configure @claude via Runner + webhook (Track B). Kit layout, session boundaries, pointers to references/ for variables and merge checklist. Not for installing GitLab Runner on this machine unless you are SSH'd on the Runner.
---

# Vibecoding workflow onboarding (developer-side agent)

## What you get

After **Track A**, the **application repository** (not the kit repo) contains: **GitLab CI** (AI review on **`feature/*`**, MRs to **`integration/*`**) plus **`.claude/`** and **memory-bank**. CI runs **in the app repo** (code + merged `.gitlab-ci.yml`).

**Track B (GitLab Runner) is required for all CI features** — `feature-review`, `mr-review`, `update-memory-bank`, and `@claude` (webhook listener for comment on commit/MR → `claude-assist` job) all run on the Runner. Without Track B, pipeline jobs stay pending indefinitely.

**Detail (variables, branches, merge list, Track B, handoff):** **`references/vibecoding-ci-kit-onboarding.md`**.

## When to use

- Full **vibecoding-ci-kit** checkout on disk (**`repo/`** + **`runner/.claude/skills/gitlab-runner-onboarding/`**).
- User needs **Track A** (merge **`repo/`** into their app repo + GitLab variables) and **Track B** (Runner + webhook on another machine, **`gitlab-runner-onboarding`**).
- **Both tracks are required** — Track A alone produces no working CI; Track B (Runner) must be completed to run any pipeline job.

## Prerequisites

- **Application:** GitLab project + push access.
- **Track A:** copy/merge into app repo; optional **Claude Code** locally for hooks (not required for GitLab CI).
- **Track B (later):** Runner with **shell** executor, **`claude`** + **`jq`** on `PATH`; follow **`gitlab-runner-onboarding`** on that host.

## Session boundary (critical)

- **This session** = **Track A** — merge **`repo/`**, conflicts, **CI/CD variables** per **`references/vibecoding-ci-kit-onboarding.md`**.
- **Do not** claim Runner registration, webhook, or launchd/systemd on the Runner host unless the shell is **on that host** and the user asked.
- **Track B** = separate session on the Runner: load **`gitlab-runner-onboarding`**.

## Kit layout (paths from kit clone root)

- **`repo/`** — merge into **application repo root**
- **`runner/.claude/skills/gitlab-runner-onboarding/`** — Runner only; not merged into the app
- **`.claude/skills/vibecoding-workflow-onboarding/`** — this skill

## Track A — one workflow

1. Read **`references/vibecoding-ci-kit-onboarding.md`** (clone/merge, variables, branch table, merge checklist).
2. Confirm **app repo root** (absolute path); warn before overwriting **`.gitlab-ci.yml`**, **`.claude/`**, etc.
3. Copy or merge from **`repo/`** (see reference **Merge `repo/`**).
4. Align branches with **`.claude/rules/memory-bank-framework.md`**, **`.gitlab-ci.yml`** `rules:`, and your app (default: **`feature/*`** → MR to **`integration/*`**).
5. **GitLab → CI/CD → Editor → Validate** on `.gitlab-ci.yml` (or CI Lint API) — does **not** trigger pipeline.
6. Set **CI/CD variables** (reference **GitLab CI/CD variables**) — does **not** trigger pipeline. **Present all variables (required + optional) to the user and let them decide what to set. Do not pre-filter or decide on their behalf.**
7. Push — **this triggers the pipeline**. Warn the user: **Runner (Track B) is required for ALL CI jobs** (`feature-review`, `mr-review`, `update-memory-bank`, `claude-assist`). Without it, every job stays pending indefinitely. Tell the user the pipeline will work only after Track B is done.
8. Fill and paste the **Handoff checklist** in **`references/vibecoding-ci-kit-onboarding.md`** for the Runner session.

### Pitfall

- Merging **`repo/`** does **not** install Runner or webhook — that is **Track B**.
- **Push before Runner is ready** → pipeline jobs **stay pending** (not fail). User may think CI is broken.
- **Recommended:** set variables + validate first, push last — after confirming Runner is registered and online.

## Related skills

| Skill | Role |
|-------|------|
| **gitlab-runner-onboarding** | Runner host — Runner, webhook, listener, deps |
| **ci-code-review** | CI review stdin/format (after **`repo/`** merge) |

## Python deps (webhook listener)

**gunicorn**, **flask**, **requests** — install lines in **`runner/.claude/skills/gitlab-runner-onboarding/SKILL.md`** (Step 4).
