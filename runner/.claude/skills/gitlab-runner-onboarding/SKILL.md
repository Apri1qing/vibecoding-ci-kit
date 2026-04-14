---
name: gitlab-runner-onboarding
description: Use when onboarding a new machine for this repo’s GitLab CI—install and configure GitLab Runner (shell), webhook listener, local dependencies, and GitLab variables/network; not a catalog of CI job behavior.
---

# GitLab Runner Onboarding

## Overview

Deploy GitLab Runner, a webhook listener, and supporting dependencies on the target host, and complete GitLab-side and host-side variable and network settings so this repository’s CI/CD can run on that Runner. This skill covers **environment and service setup only**; job responsibilities and branch rules live in `.gitlab-ci.yml` and project CI docs.

## Prerequisites

- Target host: macOS or Linux
- GitLab Runner registered to your GitLab instance with the **shell** executor
- This repository cloned on the host
- **No MCP Server required** (uses local `git` and HTTP only)

## Deployment steps

### Step 1: Install GitLab Runner

#### 1.1 Install GitLab Runner

Follow the official docs for your platform.

**macOS (Homebrew):**
```bash
brew install gitlab-runner
brew services start gitlab-runner
```

**Linux (RHEL/CentOS/Rocky/AlmaLinux 9):**
```bash
curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.rpm.sh" | sudo bash
sudo dnf install -y gitlab-runner

# Register (see parameters below)
sudo gitlab-runner register
```

**Linux (Debian/Ubuntu):**
```bash
curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh" | sudo bash
sudo apt-get install gitlab-runner

# Register (see parameters below)
sudo gitlab-runner register
```

#### 1.2 Prerequisite: Claude Code CLI

Review / `@claude` jobs run **`claude`** (Claude Code CLI) on the Runner host. Install and pin versions per your org (internal mirror or official channel). Ensure the **shell** executor can find the binary on `PATH` (e.g. `which claude` under the same user that runs jobs).

> **Auth:** the **Runner user** must have Claude Code **already configured** on that host. Pipeline jobs **do not** inherit your laptop’s environment.

### Step 2: Register the Runner

**First, ask the user:** Is this Runner **shared** (group/instance-level, picks up jobs from multiple projects) or **project-scoped** (isolated to one project)?

- **Shared Runner:** register once; all projects whose CI/CD settings allow shared runners can use it.
- **Project-scoped Runner (non-shared):** each project needs its own registration — run `gitlab-runner register` once per project using that project's registration token. All registrations share the same `config.toml`; verify with `gitlab-runner list`. If this host serves multiple projects, also note:
  - Each project's webhook listener must use a **different port** (or different path if behind a reverse proxy) — check availability with `ss -tlnp` before deploying each one.
  - Use **project-specific service names** (e.g. `iris-webhook.service`, `other-project-webhook.service`) and **project-specific listener directories** (e.g. `~/iris-webhook/`, `~/other-project-webhook/`) so they do not conflict.

Use the following when registering. **Understand each field before filling it in:**

| Field | Purpose |
|------|---------|
| `GitLab instance URL` | GitLab base URL the Runner uses to fetch CI jobs |
| `Registration token` | Trust token between Runner and GitLab; from **Project → Settings → CI/CD → Runners** |
| `Description` | Display name for this Runner in the GitLab UI |
| `Tags` | Job filter: only jobs whose `tags` match are picked. Use project/machine tags such as `macos`, `shell` |
| `Executor` | Use **`shell`**. This repo’s jobs are shell scripts; Docker and other executors are not assumed |

**Example registration (replace placeholders):**
```bash
gitlab-runner register \
  --url "https://gitlab.example.com" \
  --registration-token "YOUR_REGISTRATION_TOKEN" \
  --description "shell-runner-01" \
  --tag-list "macos,shell" \
  --executor "shell"
```

> **Why shell?** Jobs need the local Claude Code CLI (`which claude`), git, and HTTP calls to the GitLab API. Shell executor uses the host environment directly.

### Step 3: GitLab Web UI configuration

Complete these in the GitLab UI to obtain credentials for the host.

#### 3.1 Runner registration token

1. **Project → Settings → CI/CD → Runners**
2. Under **Set up a specific Runner manually**, copy the **Registration token** (used when registering the Runner)

#### 3.2 Create a CI/CD trigger

The trigger token is what the webhook listener uses to start a pipeline via the API:

1. **Project → Settings → CI/CD → Pipeline triggers**
2. **Add a trigger**
3. Set **Trigger description** (e.g. `webhook-listener`)
4. **Add trigger**, then copy the generated token → **`GITLAB_TRIGGER_TOKEN`**

#### 3.3 Configure GitLab webhook (required)

Webhooks deliver comment events so @claude can be driven from notes:

1. **Project → Settings → Integrations** (or **Webhooks**, depending on GitLab version)
2. **Add webhook**
3. Fill in:

| Field | Value | Notes |
|--------|-----|------|
| URL | `http://<RUNNER_HOST_IP>:<PORT>/gitlab-webhook` | Fill in after choosing port in Step 4; use the port confirmed free there |
| Secret token | A string you choose | Must match `WEBHOOK_SECRET` later |
| Trigger | **Comments** | Required to receive comment events |

4. **Add webhook**

> **Required:** The webhook listener is required. `@claude`, `feature-review`, `mr-review`, and `update-memory-bank` all run on the Runner — all are mandatory. Only `FEISHU_APP_TOKEN` (Feishu notifications) is optional.

#### 3.4 Create a Personal Access Token (PAT)

CI and the listener call GitLab via **REST** (notes, MR comments, triggers, etc.) and via **Git over HTTPS** (`oauth2:<token>@…` for `git fetch` / `git push`). In GitLab these are **different scopes**—enable both as needed.

1. User menu → **Preferences → Access Tokens**
2. **Add new token**
3. **Token name** (e.g. `gitlab-runner-token`)
4. **Scopes** (align with this repo’s `.gitlab-ci.yml`; typical minimal set):

| Scope | Enable | Purpose |
|------|:--------:|------|
| **api** | ✅ | `curl` + `PRIVATE-TOKEN` for GitLab REST API |
| **read_repository** | ✅ | Read repo over **HTTPS + token** (not covered by `api` alone) |
| **write_repository** | ✅ | Push over HTTPS; jobs such as `review-apply` / `update-memory-bank` use `oauth2:${GITLAB_API_TOKEN}@…` |
| **read_user** | ⬜ | `/user` etc.; **usually unnecessary if `api` is enabled**. Use only for minimal tokens without `api` that still need `GET /user` |

5. Set **Expiration date**
6. **Create personal access token** and **copy it immediately** (it won’t be shown again)

> **Pitfall:** The **`api`** scope means full **API** access; it does **not** imply **`write_repository`** (Git-over-HTTP). Pushes can still return **403** if `write_repository` is missing—add it (and usually `read_repository`). This skill assumes **one PAT** sufficient for this repo’s CI unless you split tokens for least privilege.

> **Who committed what?**
> - **Git author/committer:** comes from `git commit` metadata (`git config` or `-c user.name` / `-c user.email` in the job), not from whether `read_user` is checked on the PAT.
> - **Who triggered this pipeline:** use predefined CI variables (`CI_COMMIT_AUTHOR`, `GITLAB_USER_LOGIN`, etc.); you don’t need `read_user` just for that when `api` is enabled.
> - **Which GitLab user owns this PAT:** `GET /api/v4/user` is covered by **`api`**; use **`read_user`** only in minimal setups without `api`.

#### 3.5 CI/CD variables

Configure secrets for pipelines:

1. **Project → Settings → CI/CD → Variables**
2. **Add variable** for each:

| Variable | Source | Required | Purpose | Options |
|----------|--------|----------|---------|---------|
| `GITLAB_API_TOKEN` | §3.4 PAT | ✅ **Yes** | REST + Git HTTPS (see §3.4 scopes) | Masked |
| `GITLAB_TRIGGER_TOKEN` | §3.2 Trigger | ✅ **Yes** | Webhook listener → Trigger API (`claude-assist`); set in listener **`<LISTENER_DIR>/.env`** (§6.2) | Masked if also in GitLab |
| `CLAUDE_MODEL` | Your choice | ⚪ **Optional** | Claude model id, e.g. `claude-opus-4-6`; default if unset | Masked |
| `FEISHU_APP_TOKEN` | Feishu app | ⚪ **Optional** | Feishu notifications | Masked |

> **Masked variables:** GitLab only allows Masked when the value has no `$`, `\n`, etc., length ≤ 32 in some setups—check GitLab’s current rules.

**How variables map to features:**
- **Auto review** (`feature-review`, `mr-review`): Claude Code on the Runner host + `GITLAB_API_TOKEN`; `CLAUDE_MODEL` optional
- **update-memory-bank:** same; PAT must include **`write_repository`**; **no** webhook required
- **`@claude` / `claude-assist`:** **`GITLAB_TRIGGER_TOKEN`** (listener `.env`) + webhook — **required** for this kit
- **Feishu:** optional, needs `FEISHU_APP_TOKEN`

### Step 4: Choose listener install path

**First, ask the user:** Does this host serve **multiple repositories** (i.e., will more than one project's webhook listener run here)?

- **Single repo:** any convenient path works (e.g. `~/listener/`).
- **Multiple repos:** each project **must** have its own isolated setup — different directory, different port, and a different service name. If any of these overlap, services will conflict and listeners will fail to start. For each project, choose:
  - A **unique directory** (e.g. `~/iris-webhook/`, `~/other-project-webhook/`)
  - A **unique port** (e.g. `5000`, `5001`, …) — confirmed free before deploying (see port check below)
  - A **unique service name** (e.g. `iris-webhook.service`, `other-project-webhook.service`)

> **Ask the user:** What directory do you want for this project's webhook listener? Use a project-specific name (e.g. `~/iris-webhook/`) to avoid future conflicts.

**Before proceeding, confirm the chosen port is free:**

```bash
ss -tlnp | grep :<PORT>
```

If the port is occupied, choose a different one. Do not deploy a new listener on a port already in use — the new service will fail to bind.

---

### Step 5: Install dependencies

**macOS:**
```bash
brew install jq
python3 -m venv <LISTENER_DIR>/venv
<LISTENER_DIR>/venv/bin/pip install gunicorn flask requests
```

**Linux (RHEL/CentOS/Rocky/AlmaLinux 9):**
```bash
sudo dnf install -y jq python3-pip
python3 -m pip install --user virtualenv
python3 -m virtualenv <LISTENER_DIR>/venv
<LISTENER_DIR>/venv/bin/pip install gunicorn flask requests
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install -y jq python3-venv
python3 -m venv <LISTENER_DIR>/venv
<LISTENER_DIR>/venv/bin/pip install gunicorn flask requests
```

Replace `<LISTENER_DIR>` with the path you chose above (e.g. `~/listener`).

### Step 6: Deploy the webhook listener (required)

The listener receives GitLab comment events and drives the `@claude` pipeline. **This step is required.**

#### 6.0 What `webhook-listener.py` is

A small **HTTP service** on the Runner host that:

1. Receives **comment** events from GitLab webhooks  
2. Parses **`@claude`** in the note body  
3. Calls the **Pipeline Trigger API** with `GITLAB_TRIGGER_TOKEN` to start the `claude-assist` job  

**Trigger variables (must match the repository root `.gitlab-ci.yml` `claude-assist` rules):**

| Variable | Commit comment | MR comment |
|----------|----------------|------------|
| `AI_FLOW_EVENT` | `comment` | `comment` (same value for both) |
| `AI_FLOW_BRANCH` | branch containing the commit | MR **source** branch |
| `AI_FLOW_CONTEXT` | link to the note | link to the note |
| `AI_FLOW_INPUT` | text after `@claude` | text after `@claude` |
| `AI_FLOW_COMMIT_SHA` | commit SHA | optional (e.g. `last_commit`) |
| `AI_FLOW_MR_IID` | omit | **set** to MR IID so the job loads MR discussions + full MR diff |

**Flow:**
```
User comments @claude → GitLab POSTs webhook → listener → parse → trigger claude-assist pipeline
```

#### 6.1 Install the listener script

```bash
# On the Runner host (adjust clone path)
mkdir -p <LISTENER_DIR>
cp /path/to/vibecoding-ci-kit/runner/.claude/skills/gitlab-runner-onboarding/scripts/webhook-listener.py <LISTENER_DIR>/webhook-listener.py
```

#### 6.2 Create `.env`

```bash
cat > <LISTENER_DIR>/.env << 'EOF'
GITLAB_URL=http://<GITLAB_HOST>:<GITLAB_PORT>/
GITLAB_API_TOKEN=your-gitlab-pat
GITLAB_TRIGGER_TOKEN=your-pipeline-trigger-token
WEBHOOK_SECRET=your-webhook-secret
EOF
chmod 600 <LISTENER_DIR>/.env
```

**Or copy from the skill tree and edit:**

| Path | Role |
|------|------|
| `runner/.claude/skills/gitlab-runner-onboarding/scripts/webhook-listener.py` | Listener app |
| `<LISTENER_DIR>/.env` | Secrets (create locally; not committed) |

#### 6.3 GitLab webhook + local `.env` (must match)

Configure both sides consistently—create the webhook and trigger in GitLab first, then fill `.env`.

**GitLab → Project → Settings → Webhooks:**

| Field | Value | Notes |
|--------|-----|------|
| URL | `http://<RUNNER_HOST_IP>:<PORT>/gitlab-webhook` | GitLab must reach this URL; use the port chosen in Step 4 |
| Secret token | Your chosen string | **Must equal `WEBHOOK_SECRET` in `.env`** |
| Trigger | **Comments** | Required for @claude on notes |

> **IP:** Use the Runner host’s **real** routable IP from GitLab’s perspective. Do **not** use `127.0.0.1` in the webhook URL if GitLab runs on another machine.

**Pipeline trigger:** already created in §3.2 — use the same `GITLAB_TRIGGER_TOKEN`.

**Local `.env` (e.g. `<LISTENER_DIR>/.env` or a path your service user can read):**

| Variable | Source | Notes |
|--------|--------|------|
| `GITLAB_URL` | Manual | Base URL of your GitLab server, e.g. `http://<GITLAB_HOST>:<GITLAB_PORT>/` |
| `GITLAB_API_TOKEN` | §3.4 | PAT with `api` + `read_repository` + `write_repository` as needed |
| `GITLAB_TRIGGER_TOKEN` | Trigger UI | Paste from GitLab |
| `WEBHOOK_SECRET` | Webhook UI | Must match **Secret token** |

> **`WEBHOOK_SECRET`:** GitLab may send `X-Gitlab-Token`; the listener compares it to this value. Recommended; if empty, that check is skipped.  
> **`GITLAB_TRIGGER_TOKEN`:** Used to call the trigger API after a valid comment.  
> **Security:** Prefer a **dedicated** bot user / PAT for automation, not a personal primary account.

### Step 7: Run the listener as a service

#### macOS (launchd)

Create `<LISTENER_DIR>/com.gitlab.<PROJECT>.webhook.plist` — use a **project-specific label** (e.g. `com.gitlab.iris.webhook`) to avoid conflicts when multiple listeners run on the same host. Replace `YOUR_LISTENER_DIR` with the **absolute path** of `<LISTENER_DIR>` (e.g. `/Users/runner/iris-webhook`) and `<PORT>` with the port chosen in Step 4.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gitlab.<PROJECT>.webhook</string>

    <key>ProgramArguments</key>
    <array>
        <string>YOUR_LISTENER_DIR/venv/bin/gunicorn</string>
        <string>-w</string>
        <string>4</string>
        <string>-b</string>
        <string>127.0.0.1:<PORT></string>
        <string>webhook-listener:app</string>
    </array>

    <key>WorkingDirectory</key>
    <string>YOUR_LISTENER_DIR</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>GITLAB_URL</key>
        <string>YOUR_GITLAB_BASE_URL</string>
        <key>GITLAB_API_TOKEN</key>
        <string>YOUR_GITLAB_API_TOKEN</string>
        <key>GITLAB_TRIGGER_TOKEN</key>
        <string>YOUR_GITLAB_TRIGGER_TOKEN</string>
        <key>WEBHOOK_SECRET</key>
        <string>YOUR_WEBHOOK_SECRET_OR_EMPTY</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>YOUR_LISTENER_DIR/webhook.log</string>

    <key>StandardErrorPath</key>
    <string>YOUR_LISTENER_DIR/webhook.error.log</string>
</dict>
</plist>
```

> Prefer a **local-only** plist or a wrapper that loads `<LISTENER_DIR>/.env`; **do not commit** plists containing real tokens.

Load:
```bash
launchctl load <LISTENER_DIR>/com.gitlab.<PROJECT>.webhook.plist
launchctl list | grep gitlab.<PROJECT>.webhook
tail -f <LISTENER_DIR>/webhook.log
```

#### Linux (systemd)

Create `/etc/systemd/system/<PROJECT>-webhook.service` — use a **project-specific service name** (e.g. `iris-webhook.service`) to avoid overwriting an existing service on the same host. Replace `YOUR_SERVICE_USER` and `YOUR_LISTENER_DIR` (absolute path of `<LISTENER_DIR>`). Replace `<PORT>` with the port chosen in Step 4. Bind address: use `0.0.0.0` if GitLab must reach the host on the network interface; use `127.0.0.1` only if a reverse proxy terminates TLS and forwards locally.

```ini
[Unit]
Description=GitLab Webhook Listener
After=network.target

[Service]
Type=simple
User=YOUR_SERVICE_USER
WorkingDirectory=YOUR_LISTENER_DIR
EnvironmentFile=-YOUR_LISTENER_DIR/.env
ExecStart=YOUR_LISTENER_DIR/venv/bin/gunicorn -w 4 -b 0.0.0.0:<PORT> webhook-listener:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

> **`EnvironmentFile=`** keeps secrets out of the unit file. Adjust `ExecStart` bind address to match your network layout.

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable <PROJECT>-webhook
sudo systemctl start <PROJECT>-webhook
sudo systemctl status <PROJECT>-webhook
```

### Step 8: Verify

#### 8.1 Listener

```bash
curl -s http://127.0.0.1:<PORT>/health || echo "listener down"
ps aux | grep gunicorn | grep -v grep
```

#### 8.2 Runner

```bash
gitlab-runner verify
gitlab-runner list
```

> **Note:** `gitlab-runner list` writes its output to **stderr**. Never suppress stderr with `2>/dev/null` — doing so hides the actual runner list and makes `|| echo "not registered"` fire even when runners are registered. Run `gitlab-runner list` directly and read the full output.

#### 8.3 End-to-end

1. Push a `feature/*` branch  
2. Confirm `feature-review` (or equivalent) runs  
3. Check job logs for Claude Code  
4. Confirm review output appears as commit comments (per your pipeline)

## Troubleshooting

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| `which claude: not found` | CLI not on `PATH` | Under the Runner user, fix `PATH` (Homebrew `bin`, etc.) or set in CI `before_script` |
| `claude` auth / API errors | CLI not configured on the Runner user | Finish Claude Code setup on the host |
| `claude-assist` stuck pending | Tag mismatch | Runner tags must match the job’s `tags` (e.g. `claude`) |
| Webhook fails | Firewall / bind address | Open inbound the chosen port; ensure URL uses an IP/DNS GitLab can reach |
| Feishu errors | Missing token | Set `FEISHU_APP_TOKEN` in CI (and any listener-side config if used) |
| Pipeline loops | Missing `[skip ci]` | Bot commits from `update-memory-bank` / @claude should include `[skip ci]` per project rules |
| `@claude` silent | Webhook not delivered | Verify webhook URL, Comments trigger, and network path to the listener |

## Parameter checklist

| Stage | Item | Required | Where |
|------|------|----------|--------|
| Runner | GitLab instance URL | ✅ | GitLab base URL |
| Runner | Registration token | ✅ | **Project → CI/CD → Runners** |
| CI | `GITLAB_API_TOKEN` | ✅ | **User → Access Tokens** (PAT) |
| CI | `GITLAB_TRIGGER_TOKEN` | ✅ | §3.2 Trigger → listener **`<LISTENER_DIR>/.env`** (§6.2) |
| CI | `CLAUDE_MODEL` | ⚪ | Model id string |
| CI | `FEISHU_APP_TOKEN` | ⚪ | Feishu |
| Webhook | Listener URL | ✅ | `http://<RUNNER_HOST_IP>:<PORT>/gitlab-webhook` (port chosen in Step 4) |
| Webhook | `WEBHOOK_SECRET` | ⚪ | Same string in GitLab + `.env` |

**Feature ↔ credentials:**
- **Auto review:** Runner with Claude Code configured + `GITLAB_API_TOKEN`
- **update-memory-bank:** same; PAT needs **`write_repository`**; branch protection must allow the push
- **`@claude`:** **`GITLAB_TRIGGER_TOKEN`** + webhook (required)
- **Feishu:** optional `FEISHU_APP_TOKEN`
