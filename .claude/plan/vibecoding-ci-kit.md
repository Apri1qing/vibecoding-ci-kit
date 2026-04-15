# Vibecoding CI Kit — 设计与实现说明

**GitLab CI/CD、AI 代码审查（`feature-review` / `mr-review`）、评论驱动助手（`@claude` → `claude-assist`）、合入后 Memory Bank 更新（`update-memory-bank`）**。

本文档位于脚手架仓库 **`.claude/plan/vibecoding-ci-kit.md`**。合并 **`repo/`** 到业务仓库时**默认不包含**本目录；若团队需要可单独拷贝。

## 文档地位（事实来源）

- **流水线行为**以业务仓库根目录 **`.gitlab-ci.yml`**（由 **`repo/.gitlab-ci.yml`** 合并而来）为准。
- **审查 stdin 与报告结构**以 **`repo/.claude/skills/ci-code-review/SKILL.md`** 为准。
- **Memory bank 与分支约定**以 **`repo/.claude/rules/memory-bank-framework.md`** 为准。

若本文与上述文件或 CI 不一致，**以 `repo/.gitlab-ci.yml` 与 rule/skill 为准**。

## 仓库布局（vibecoding-ci-kit）

本仓库**不是**业务应用代码，而是可复用的脚手架；目录分工如下。

| 位置 | 内容 | 说明 |
|------|------|------|
| 根目录 **`README.md`** / **`README.zh.md`** | 接入步骤、CI/CD 变量、分支与 Track A/B | 主入口；**不**随 `repo/` 合并 |
| **`repo/`** | `.gitlab-ci.yml`、`.gitlab/`、`.claude/`、`memory-bank/`、`CLAUDE.md`、`AGENTS.md` 等 | **复制到业务 GitLab 仓库根目录**（Track A） |
| **`runner/.claude/skills/gitlab-runner-onboarding/`** | `SKILL.md`、`scripts/webhook-listener.py` | **仅**在 Runner / 运维机使用（Track B）；**不**合并进业务仓库 |
| **`.claude/skills/vibecoding-workflow-onboarding/`** | 合并清单、变量与交接说明 | 开发机侧 Agent；**不**合并进业务仓库 |

**Agent 分工**：业务仓库侧用 **`vibecoding-workflow-onboarding`**（合并 `repo/`、变量、交接 Runner）；Runner 上用 **`gitlab-runner-onboarding`**（Runner、Webhook、Trigger）。

**Claude 认证（CI）**：支持 **`ANTHROPIC_API_KEY`**（可选 **`ANTHROPIC_BASE_URL`**）或 **`CLAUDE_CODE_OAUTH_TOKEN`**，与根目录 **`README.md`** 一致。

**`AGENTS.md`**：脚手架提供通用模板 **`repo/AGENTS.md`**；团队可在业务仓库中按项目覆盖。

---

## 📋 方案概述

本方案实现了完整的 AI 驱动代码审查和智能助手系统，包含：

1. **自动代码审查**：`feature/*` 分支 **push** 触发 Level 1；**MR 目标分支**为 `integration/*` 或 `integration-*` 时触发 Level 2（与 **`repo/.gitlab-ci.yml`** 的 `rules` 一致）
2. **@claude 智能助手**：通过评论 `@claude` 触发按需代码修复和功能实现
3. **飞书私聊通知**：通过邮箱获取 open_id 发送私聊消息；卡片文案与 `CODE_REVIEW_REPORT_LANGUAGE`（`zh` / `en`）一致
4. **Memory Bank 自动更新**：代码合入 integration 分支后自动更新知识库
5. **防止 CI 循环**：`claude-assist` 使用 **`git push -o ci.skip=true`**（**不在** commit message 里写 `[skip ci]`，以免跳过 MR 流水线）；`update-memory-bank` 的 bot 提交仍使用 **`[skip ci]`**（见 **`repo/.gitlab-ci.yml`** 注释）
6. **审查报告语言**：`CODE_REVIEW_REPORT_LANGUAGE`（默认 `zh`）写入 stdin，Claude 按 **ci-code-review** skill 输出对应语言；飞书脚本读取同一变量以本地化卡片

**审查行为与报告格式（事实来源）**：

- **分支 ↔ tech-doc 文件命名**：`repo/.claude/rules/memory-bank-framework.md`（「Feature branch ↔ tech-doc file naming」）
- **报告结构、Level 1/2 必读材料**：`repo/.claude/skills/ci-code-review/SKILL.md`
- **`claude -p` 的 stdin 键值**：见下节「GitLab CI 审查 stdin」（与 **`repo/.gitlab-ci.yml`** 写入一致）

本文档侧重**部署与运维**；若与上述 rule/skill 冲突，以 **`repo/`** 内 rule/skill 与 CI 为准。

## GitLab CI 审查 stdin

`.gitlab-ci.yml` 只向 `claude -p` 写入 `key: value` 行。**事实来源：脚手架内 `repo/.gitlab-ci.yml`**（合并到业务仓后为仓库根目录 `.gitlab-ci.yml`）；下表与之一致。

### Level 1（`feature-review`）：首次 push vs 非首次 push

新分支 **首次 push** 时，GitLab 常将 `CI_COMMIT_BEFORE_SHA` 置为**空或全 0**；**非首次** 则为该分支在远程的**上一笔提交**。

| 模式 | 触发条件 | 典型 stdin | 审查含义 |
|------|----------|------------|----------|
| **分支快照** | `CI_COMMIT_BEFORE_SHA` 为空或全 0 | `first_push: true`、`review_scope: branch_tree`、`diff_range: n/a`，以及 `review_level: 1`、`branch`、`review_report_language`、`ci_code_review` | 审 **当前分支 `HEAD` 上已跟踪代码**（`git ls-files` + Read / Glob），**不以** `git diff` 相对 `main`/release 为**主**审查范围。详见 **ci-code-review** skill。 |
| **增量 diff** | 否则 | `first_push: false`、`review_scope: diff_range`、`diff_range: <CI_COMMIT_BEFORE_SHA>..HEAD`，以及同上通用键 | 对该区间 **`git diff`**，覆盖**本次 push** 相对上一远程 tip 的连续变更（多 commit 同推为合计 diff）。 |

### Level 1 / Level 2 键一览

| 键 | Level 1 | Level 2 |
|----|---------|---------|
| `review_level` | `1` | `2` |
| `first_push` / `review_scope` / `diff_range` | 见上表（Level 1 分两档） | — |
| `branch` | 当前分支 | — |
| `mr_source` | — | MR 源分支 |
| `mr_target` | — | MR 目标分支 |
| `review_report_language` | `${CODE_REVIEW_REPORT_LANGUAGE:-zh}`（`zh` 或 `en`） | 同 |
| `ci_code_review` | **ci-code-review** skill 路径：`.claude/skills/ci-code-review/SKILL.md`（审查时 Read 该文件并按其中要求输出） | 同 |

`ci_code_review` 与 skill **ci-code-review** 对应（键名用下划线，仓库路径用连字符目录名）。

审查须 Read stdin 中 `ci_code_review` 指向的 skill 文件并执行；`review_report_language` 与 **ci-code-review** skill 中「stdin: review_report_language」一致，用于整份 Markdown 报告语言。

**`.gitlab-ci.yml` 默认变量（可在 GitLab CI/CD Variables 覆盖）**：

| 变量 | 默认 | 说明 |
|------|------|------|
| `CLAUDE_MODEL` | 以仓库 `.gitlab-ci.yml` 为准 | 传给 `claude --model` |
| `CODE_REVIEW_REPORT_LANGUAGE` | `zh` | 审查报告与飞书卡片 UI 语言；设为 `en` 则全文英文 |

---

## 🎯 核心功能

### 1. Level 1 Review - Feature 分支自动审查

**触发条件**：push 到 `feature/*` 分支

**执行流程**：
```
Feature 分支 Push
    ↓
feature-review job 启动
    ↓
CI checkout 到 feature 分支
    ↓
向 claude -p 传入极短 stdin（见上「Level 1：首次 vs 非首次」）
    ↓
┌─ 首次 push（CI_COMMIT_BEFORE_SHA 空/全 0）→ 分支快照审：Glob/Read 已跟踪文件，不以 git diff 为主
└─ 非首次 push → 按 diff_range 做 git diff（本次 push 相对上一远程 tip 的合计变更）
    ↓
按 ci-code-review skill 输出 Markdown 报告
    ↓
生成 review-report.md
    ↓
CI 脚本发送 GitLab 评论（带 <!-- AI_CODE_REVIEW --> 标记）
    ↓
CI 脚本发送飞书通知（根据风险等级调整卡片颜色）
```

**非首次 push 时 `diff_range` 的含义（与「只看最后一个 commit」的区别）**：

- `BEFORE_SHA` 取自 **`CI_COMMIT_BEFORE_SHA`**（GitLab 提供，即该分支上一笔在远程的提交）。
- stdin 中 `diff_range` 为 **`BEFORE_SHA..HEAD`**。Claude 对该区间使用 **`git diff`**，审查**本次推送**引入的连续变更；一次 push 含多个 commit 时，为**合计 diff**，而非仅 `git show HEAD`（只看 tip 一笔）。

**首次 push 分支快照**：

- **不**使用 `merge-base(origin/main, HEAD)..HEAD` 等相对基线的 diff 作为默认主范围；**不**用 `git diff` 相对某基线替代「看分支上的代码」。
- 大仓库可对路径做优先级或范围说明，见 **ci-code-review** skill。

**关键特性**：
- ✅ Claude 使用 **Bash**（`git ls-files` / `git diff` 等）与 **Read / Grep / Glob** 读文件与规范
- ✅ 使用权限白名单 `--allowedTools "Bash Read Grep Glob"`
- ✅ CI 脚本负责发送评论和飞书通知（确定性强）
- ✅ 不依赖 MCP Server，部署更简单

---

### 2. Level 2 Review - MR 全量审查

**触发条件**：MR 目标分支为 `integration/*` 或 `integration-*`

**执行流程**：
```
创建 MR：feature/xxx → integration/5.0
    ↓
mr-review job 启动
    ↓
CI checkout 到源分支，fetch 目标分支
    ↓
Claude 用 git diff 查看 MR 全量变更
    ↓
生成 review-report.md
    ↓
CI 脚本发送 MR 评论
    ↓
CI 脚本发送飞书通知
```

**关键特性**：
- ✅ CI 向 stdin 传入 `review_level: 2`、`mr_source`、`mr_target`、`review_report_language`、`ci_code_review`（见上文「GitLab CI 审查 stdin」）；Claude 在已 `fetch` 目标分支的前提下，用 **`git diff origin/<mr_target>...HEAD`**（或等价）查看 **MR 全量** diff（目标分支以实际 MR 为准）
- ✅ 必读材料与报告格式见 **ci-code-review** skill
- ✅ Level 2 为合入前的全量审查，更严格

---

### 3. @claude 智能助手

**触发条件**：用户在 Commit/MR 评论中提到 `@claude`

**执行流程**：
```
用户评论：@claude 修复第 1、3 条，跳过第 2 条
    ↓
GitLab Webhook 发送事件到监听器
    ↓
监听器解析评论，触发 Pipeline Trigger API
    ↓
claude-assist job 启动
    ↓
CI 判断场景（commit 或 MR）
    ↓
┌─────────────────────┬─────────────────────┐
│   Commit 场景        │      MR 场景         │
├─────────────────────┼─────────────────────┤
│ CI 拉取 commit 评论  │ CI 拉取 MR 讨论      │
│ 用 jq 分类评论      │ 用 jq 分类讨论       │
│ Claude: git show    │ CI fetch 目标分支    │
│                     │ Claude: git diff     │
└─────────────────────┴─────────────────────┘
    ↓
Claude 修复代码
    ↓
git commit & **`git push -o ci.skip=true`**（避免分支 pipeline 循环；与 `[skip ci]` 策略不同，见下文「防止 CI 循环」）
    ↓
默认**不会**自动再跑 `feature-review`（ci.skip）；需要再审查时再 push 或更新 MR
```

**关键特性**：
- ✅ **场景区分**：自动识别 commit 评论 vs MR 评论
- ✅ **评论分类**：CI 脚本通过 jq 预处理，区分 AI review 和人类 feedback
- ✅ **优先级**：人类 feedback > AI review > 用户当前指令
- ✅ **MR 场景**：查看整个 MR 的变更，不只是最后一个 commit
- ✅ **防止循环**：`git push -o ci.skip=true`（**不**在 commit message 中使用 `[skip ci]`，以免 MR 相关流水线被跳过）

---

### 4. Memory Bank 自动更新

**触发条件**：push 到 `integration/*` 或 `integration-*` 分支（与 `.gitlab-ci.yml` 中 `update-memory-bank` 的 `rules` 一致）。

**要点**：

- Job 使用 `git config user.name` = `claude`、`user.email` = `claude@users.noreply.${CI_SERVER_HOST:-gitlab}` 推送自动提交（与人工提交区分；与 **claude-assist** 同一作者名与邮箱，仅推送场景不同）。
- 仅当 `memory-bank/` 有变更时才 commit + push；提交信息含 **`[skip ci]`**，避免循环触发。

---

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                        GitLab 项目                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Feature 分支 Push ──────────┐                              │
│                              ├──► feature-review (Level 1)   │
│  MR 创建/更新 ───────────────┤                              │
│                              └──► mr-review (Level 2)        │
│                                                              │
│  用户评论 @claude ───────────┐                              │
│                              │                               │
│                              ▼                               │
│                    ┌──────────────────┐                     │
│                    │ Webhook 监听器    │                     │
│                    │ (外部服务)        │                     │
│                    └──────────────────┘                     │
│                              │                               │
│                              ▼                               │
│                    触发 Pipeline Trigger                     │
│                              │                               │
│                              ▼                               │
│                    claude-assist (AI 助手)                   │
│                              │                               │
│                              ├──► 拉取评论并分类             │
│                              ├──► AI review vs 人类 feedback │
│                              ├──► Claude 修复代码            │
│                              └──► commit & push              │
│                                                              │
│  代码合入 integration ───────► update-memory-bank            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 👥 人工参与步骤

### 步骤 1：配置 GitLab CI/CD 变量

**位置**：GitLab 项目 → **Settings** → **CI/CD** → **Variables**

| 变量名 | 类型 | 必需 | 说明 | 示例值 |
|--------|------|------|------|--------|
| `ANTHROPIC_API_KEY` | Masked | ✅ 必需* | Claude API Key（与 `CLAUDE_CODE_OAUTH_TOKEN` **二选一**） | `sk-ant-api03-xxx` |
| `GITLAB_API_TOKEN` | Masked | ✅ 必需 | GitLab Project Access Token（需要 `api`、`read_repository`、`write_repository` 权限） | `glpat-xxx` |
| `GITLAB_TRIGGER_TOKEN` | Masked | ✅ 必需（@claude 功能） | Pipeline Trigger Token | `glptt-xxx` |
| `FEISHU_APP_ID` | Variable | ⚪ 可选 | 飞书自建应用 `app_id`；与 `FEISHU_APP_SECRET` 同时配置才会发飞书 | `cli_xxx` |
| `FEISHU_APP_SECRET` | Masked | ⚪ 可选 | 飞书自建应用 `app_secret`；**`send-feishu.py` 内用其换取 `tenant_access_token`**，无需手工填 2 小时 token | — |
| `FEISHU_DEFAULT_NOTIFY_EMAIL` | Variable | ⚪ 可选 | 当无法从评论/提交元数据解析收件人邮箱时的兜底（`claude-assist` / `update-memory-bank`） | — |
| `CODE_REVIEW_REPORT_LANGUAGE` | Variable | ⚪ 可选 | 审查报告与飞书卡片语言：`zh`（默认）或 `en` | `zh` |
| `ANTHROPIC_BASE_URL` | Variable | ⚪ 可选 | 覆盖 Anthropic API 端点（内网镜像等），与 `ANTHROPIC_API_KEY` 同用 | — |
| `CLAUDE_CODE_OAUTH_TOKEN` | Masked | ⚪ 可选* | OAuth token（`claude setup-token`）；与 `ANTHROPIC_API_KEY` **二选一** | — |

\*Runner 上 **`claude`** 至少配置 **`ANTHROPIC_API_KEY`** 或 **`CLAUDE_CODE_OAUTH_TOKEN`** 之一；可选 **`ANTHROPIC_BASE_URL`**。

**创建 GitLab API Token**：
1. 进入项目 **Settings** → **Access Tokens**
2. Token name: `claude-ci-bot`
3. 权限选择：
   - ✅ `api`
   - ✅ `read_repository`
   - ✅ `write_repository`
4. 点击 **Create project access token**
5. 复制生成的 token（只显示一次）

**创建 Pipeline Trigger Token**：
1. 进入项目 **Settings** → **CI/CD** → **Pipeline triggers**
2. Description: `claude-webhook-trigger`
3. 点击 **Add trigger**
4. 复制生成的 token

**Webhook 调用 Trigger API 时传入的变量（与 `.gitlab-ci.yml` 中 `claude-assist` 一致）**：

| 变量 | 说明 |
|------|------|
| `AI_FLOW_EVENT` | 固定为 `comment`，与 job 的 `rules` 匹配 |
| `AI_FLOW_BRANCH` | 源分支 ref |
| `AI_FLOW_INPUT` | 评论中 `@claude` 后的指令文本 |
| `AI_FLOW_CONTEXT` | 评论/MR 链接 |
| `AI_FLOW_COMMIT_SHA` | Commit 评论场景必传；MR 场景可传 `last_commit` 供对账 |
| `AI_FLOW_MR_IID` | **仅 MR 评论**传入 MR 的 IID，CI 才能走 MR 全量 diff；Commit 评论勿传 |

**创建飞书应用（`FEISHU_APP_ID` + `FEISHU_APP_SECRET`）**：
1. 进入飞书开放平台：https://open.feishu.cn/
2. 创建企业自建应用
3. 在应用详情中获取 **App ID**、**App Secret**，并分别配置为 GitLab 变量 **`FEISHU_APP_ID`**、**`FEISHU_APP_SECRET`**（Secret 建议 Masked）
4. 添加应用权限：
   - ✅ `contact:user.email:readonly`（通过邮箱解析用户并私聊）
   - ✅ `im:message`（发送消息）
5. 发布应用并完成租户授权

**注意**：**`repo/.gitlab/send-feishu.py`** 在运行时**用 `app_id` + `app_secret` 调用飞书接口换取 `tenant_access_token`**，无需在 CI 变量中手工维护 2 小时过期的 token。

---

### 步骤 2：安装 Claude Code CLI（GitLab Runner）

**在 GitLab Runner 机器上执行**：

```bash
# 方法 1：使用官方安装脚本
curl -fsSL https://claude.ai/install.sh | bash

# 方法 2：使用 npm（如果已安装 Node.js）
npm install -g @anthropic-ai/claude-code

# 验证安装
claude --version
```

**配置 Runner 环境**：

```bash
# 确保 PATH 包含 claude
export PATH="/opt/homebrew/bin:$PATH"  # macOS
# 或
export PATH="/usr/local/bin:$PATH"     # Linux

# 安装 jq（用于 JSON 处理）
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# CentOS/RHEL
sudo yum install jq
```

---

### 步骤 3：部署 Webhook 监听器（@claude 功能）

**部署在物理机器上**（与 Claude Code CLI 同一台机器）：

#### 3.1 安装依赖

```bash
# 安装 Python 依赖
pip3 install flask requests gunicorn

# 验证安装
python3 -c "import flask, requests; print('✓ 依赖安装成功')"
```

#### 3.2 创建 systemd 服务

```bash
# 创建服务文件
sudo tee /etc/systemd/system/gitlab-webhook.service > /dev/null <<'EOF'
[Unit]
Description=GitLab Webhook Listener for @claude
After=network.target

[Service]
Type=simple
User=gitlab-runner
WorkingDirectory=/path/to/your/repo/.gitlab
Environment="GITLAB_URL=https://your-gitlab.com"
Environment="GITLAB_API_TOKEN=your-api-token"
Environment="GITLAB_TRIGGER_TOKEN=your-trigger-token"
Environment="WEBHOOK_SECRET=your-random-secret"
ExecStart=/usr/bin/gunicorn -w 4 -b 127.0.0.1:5000 webhook-listener:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 修改 WorkingDirectory 为实际路径
sudo sed -i 's|/path/to/your/repo|/actual/path/to/webhook|g' /etc/systemd/system/gitlab-webhook.service

# 重载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start gitlab-webhook

# 设置开机自启
sudo systemctl enable gitlab-webhook

# 查看状态
sudo systemctl status gitlab-webhook

# 查看日志
sudo journalctl -u gitlab-webhook -f
```

#### 3.3 配置 Nginx 反向代理（可选）

如果需要外网访问：

```bash
# 创建 Nginx 配置
sudo tee /etc/nginx/sites-available/gitlab-webhook <<'EOF'
server {
    listen 80;
    server_name webhook.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 启用配置
sudo ln -s /etc/nginx/sites-available/gitlab-webhook /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 配置 SSL（使用 Let's Encrypt）
sudo certbot --nginx -d webhook.yourdomain.com
```

#### 3.4 内网部署（无需外网访问）

如果 GitLab 和 Webhook 监听器都在内网：

```bash
# 修改 systemd 服务，监听内网 IP
sudo sed -i 's|127.0.0.1:5000|0.0.0.0:5000|g' /etc/systemd/system/gitlab-webhook.service
sudo systemctl restart gitlab-webhook

# Webhook URL 使用内网 IP：http://192.168.1.100:5000/gitlab-webhook
```

---

### 步骤 4：配置 GitLab Webhook

**位置**：GitLab 项目 → **Settings** → **Webhooks**

1. **URL**: `https://webhook.yourdomain.com/gitlab-webhook`
2. **Secret token**: 填写步骤 3 中设置的 `WEBHOOK_SECRET`
3. **Trigger**: ✅ 只勾选 **Comments**
4. **SSL verification**: ✅ Enable SSL verification（如果使用 HTTPS）
5. 点击 **Add webhook**

**测试 Webhook**：
1. 点击 webhook 右侧的 **Test** → **Comments events**
2. 检查响应状态码是否为 200
3. 查看 webhook 监听器日志：`docker logs -f webhook-listener`

---

### 步骤 5：更新 .gitlab-ci.yml

将仓库根目录的 **`.gitlab-ci.yml`** 与当前方案对齐后提交（勿依赖已废弃的临时文件名）；建议先备份再合并：

```bash
cp .gitlab-ci.yml .gitlab-ci.yml.backup
# 编辑 .gitlab-ci.yml 后
git add .gitlab-ci.yml
git commit -m "ci: align pipeline with AI review / @claude / Feishu"
git push origin <your-branch>
```

---

### 步骤 6：测试验证

#### 测试 1：自动 Review

```bash
# 在 feature 分支提交代码
git checkout -b feature/test-ci-upgrade
echo "test" > test.txt
git add test.txt
git commit -m "test: trigger review"
git push origin feature/test-ci-upgrade
```

**预期结果**：
- ✅ CI 自动触发 `feature-review` job
- ✅ 在 commit 页面看到 AI 评论（包含 `<!-- AI_CODE_REVIEW -->`）
- ✅ 飞书收到通知（如果配置了）

---

#### 测试 2：@claude 修复

```bash
# 在上面的 commit 页面评论
@claude 请添加一个 README.md 文件，说明这是测试项目
```

**预期结果**：
- ✅ Webhook 监听器收到事件（查看日志）
- ✅ CI 触发 `claude-assist` job
- ✅ 看到新的 commit 添加了 README.md
- ✅ 新提交默认**不**再自动跑 `feature-review`（与 `git push -o ci.skip=true` 一致）；需要可再推一笔触发审查

---

#### 测试 3：评论分类

```bash
# 1. 等待 AI review 评论生成
# 2. 添加人类评论
这里应该用 ConcurrentHashMap，不要用 HashMap

# 3. 触发 @claude
@claude 修复所有 review 意见，但跳过第 2 条

# 4. 检查 claude-assist job 的 artifacts
# 下载 /tmp/ai-reviews.txt 和 /tmp/human-feedback.txt
```

**预期结果**：
- ✅ AI review 和人类 feedback 被正确分类
- ✅ Claude 优先处理人类 feedback
- ✅ 如果人类说"跳过第 2 条"，即使 AI review 中有，也会跳过

---

## 🔧 技术实现细节

### 1. Claude 如何查看代码

**不使用 MCP，完全依赖本地 git 命令**；审查范围与必读文件以 **ci-code-review** skill 为准。

| Job | Claude 的查看方式 |
|-----|------------------|
| **feature-review（首次 push）** | stdin：`first_push: true`、`review_scope: branch_tree`、`diff_range: n/a` → 以 **`git ls-files` + Read / Glob** 为主，审 **分支 `HEAD` 上已跟踪代码**；**不以** `git diff` 相对其他 ref 为主输入 |
| **feature-review（非首次 push）** | stdin：`diff_range: <CI_COMMIT_BEFORE_SHA>..HEAD` → 对该区间 **`git diff`**（一次 push 多 commit 时为**整段**相对上一远程 tip，而非仅 `git show HEAD`）；可用 `git diff --name-only` 辅助；`Read` 读完整文件与 `.claude/rules/`、tech-doc 等 |
| **mr-review** | stdin 提供 `mr_source` / `mr_target`；CI 已 `fetch` 目标分支 → **`git diff origin/<mr_target>...HEAD`** 查看 MR 全量 diff（目标分支名以 MR 为准）<br>`Read` 同上 |
| **claude-assist (commit)** | `git show <commit_sha>` 查看指定 commit 的 diff<br>`Read` 工具读取需要修改的文件<br>`Edit/Write` 工具修改代码 |
| **claude-assist (MR)** | `git diff origin/<目标分支>...HEAD`（目标分支来自 MR API 的 `target_branch`）<br>`Read` 工具读取需要修改的文件<br>`Edit/Write` 工具修改代码 |

**优势**：
- ✅ 不需要部署 MCP Server
- ✅ 本地操作更快
- ✅ Claude 可以灵活组合 git 命令和 Read 工具

---

### 2. 评论分类逻辑

**CI 脚本预处理**（`.gitlab-ci.yml` 中的 `claude-assist` job）：

#### Commit 场景

```bash
# 拉取 commit 评论
COMMENTS=$(curl -sS --header "PRIVATE-TOKEN: $GITLAB_API_TOKEN" \
  "${API_URL}/projects/${CI_PROJECT_ID}/repository/commits/${COMMIT_SHA}/comments")

# 用 jq 分类
AI_REVIEWS=$(echo "$COMMENTS" | jq -r '
  .[] | select(.body | contains("<!-- AI_CODE_REVIEW -->"))
  | "- " + .body')

HUMAN_FEEDBACK=$(echo "$COMMENTS" | jq -r '
  .[] | select(.body | contains("<!-- AI_CODE_REVIEW -->") | not)
  | "- [" + .author.name + "]: " + .body')
```

#### MR 场景

```bash
# 拉取 MR 讨论
MR_DISCUSSIONS=$(curl -sS --header "PRIVATE-TOKEN: $GITLAB_API_TOKEN" \
  "${API_URL}/projects/${CI_PROJECT_ID}/merge_requests/${MR_IID}/discussions")

# 用 jq 分类（从 discussions 中提取 notes）
AI_REVIEWS=$(echo "$MR_DISCUSSIONS" | jq -r '
  .[] | .notes[] | select(.body | contains("<!-- AI_CODE_REVIEW -->"))
  | "- " + .body')

HUMAN_FEEDBACK=$(echo "$MR_DISCUSSIONS" | jq -r '
  .[] | .notes[] | select(.body | contains("<!-- AI_CODE_REVIEW -->") | not)
  | "- [" + .author.name + "]: " + .body')
```

**分类规则**：

| 评论类型 | 判断条件 |
|---------|---------|
| **AI Review** | 包含 `<!-- AI_CODE_REVIEW -->` 标记 |
| **人类 Feedback** | 不包含 `<!-- AI_CODE_REVIEW -->` 标记的所有评论 |

**说明**：
- 使用 Personal Access Token 发表评论时，评论作者是 token 所属用户，而不是独立的 bot 账号
- 因此只依赖 `<!-- AI_CODE_REVIEW -->` 标记来区分 AI 和人类评论
- `feature-review` 和 `mr-review` job 发表的评论都会自动添加此标记

---

### 3. 飞书通知逻辑

**脚本**：`repo/.gitlab/send-feishu.py`（注释与日志为英文；需 **`FEISHU_APP_ID`** + **`FEISHU_APP_SECRET`**）

**两条路径（由 `FEISHU_CARD_MODE` 与 job 决定）**：

| 路径 | 适用 | 卡片正文 |
|------|------|----------|
| **审查**（默认，无 `FEISHU_CARD_MODE` 或不为 `reply`） | `feature-review` / `mr-review` | **风险概况**（🔴🟡🟢 数量）、**提交人**、**报告中第一个 `##` 二级标题章节**（含该标题行）；**无**单独的「风险等级」区块；header 仍按风险配色 |
| **reply** | `claude-assist` / `update-memory-bank` 中设 `FEISHU_CARD_MODE=reply` | 与 GitLab 评论/API 使用的 **`REPLY_BODY` 同源**（先写入临时文件再 `send-feishu`）；整份正文经规范化后入卡 |

**流程概要**：

1. 用 **App ID / App Secret** 换取 **`tenant_access_token`**，再调飞书 API。
2. 使用 **Contact API** `batch_get_id`，按 **收件人邮箱** 解析 `open_id`；解析失败则跳过发送（**不阻塞 CI**，exit 0）。
3. **审查路径**：从报告解析风险表 🔴🟡🟢 数量；取第一个 `## …` 节至下一同级 `##` 前（无 `##` 时有脚本内 fallback）；**reply 路径**：对临时文件全文规范化，**不再**用「审查总结」类正则抽取。
4. 构建 **交互卡片**（`msg_type: interactive`），通过 **IM API** 私聊。正文过长时卡片按脚本内上限截断：**飞书卡片可能短于 GitLab 页面上可见的全文**，GitLab 仍为完整 `REPLY_BODY`。

**收件人邮箱（与 job 一致）**：

| Job | 邮箱来源（摘要） |
|-----|------------------|
| **feature-review** | 当前流水线 **`CI_COMMIT_SHA`** 上**最后一笔提交**的作者邮箱：`git log -1 --format=%ae` |
| **mr-review** | 优先：**GitLab API** 取 MR **`author.id`** → **`GET /users/:id`** 的 **`public_email`** 或 **`email`**；若为空或失败则**回退**为 `git log -1 %ae`（与旧行为一致） |
| **claude-assist** | 依序：`AI_FLOW_AUTHOR_EMAIL` → `CI_COMMIT_AUTHOR` 解析 → `git log` → **`FEISHU_DEFAULT_NOTIFY_EMAIL`** |
| **update-memory-bank** | 优先：**MR author**（`GET .../commits/:sha/merge_requests` 或 merged 列表匹配 `merge_commit_sha` → **`GET /merge_requests/:iid`** 的 **`author.id`** → **`GET /users/:id`** 的 **`public_email`** / **`email`**）；**否则** `AI_FLOW_AUTHOR_EMAIL` → `CI_COMMIT_AUTHOR` → `git log` → **`FEISHU_DEFAULT_NOTIFY_EMAIL`** |

**语言（与审查报告一致）**：环境变量 **`CODE_REVIEW_REPORT_LANGUAGE`**（默认 `zh`）。子进程继承，**无需额外传参**。

**CI 调用示例（feature-review）**：

```bash
AUTHOR_EMAIL=$(git log -1 --pretty=format:'%ae' $CI_COMMIT_SHA)
python3 .gitlab/send-feishu.py review-report.md "Feature Review: $CI_COMMIT_BRANCH" "$COMMIT_URL" "$AUTHOR_EMAIL"
```

**优势**：按邮箱匹配飞书用户；审查路径按风险驱动卡片 header 配色；与 **`CODE_REVIEW_REPORT_LANGUAGE`** 一致；reply 路径与 GitLab 正文同源。

---

### 4. 权限控制

| Job | 权限配置 | 说明 |
|-----|---------|------|
| `feature-review` | `--allowedTools "Bash Read Grep Glob"` | Claude 用 git 命令查看代码，只读权限 |
| `mr-review` | `--allowedTools "Bash Read Grep Glob"` | Claude 用 git 命令查看 MR，只读权限 |
| `claude-assist` | `--allowedTools "Read Edit Write Grep Glob"`<br>`--disallowedTools "Bash Agent WebFetch WebSearch"` | 读写代码；**禁止 Bash**（避免任意 shell）、禁止 Agent / 联网 |
| `update-memory-bank` | `--disallowedTools "Bash"` | 只能修改文件，不能执行 shell |

**不使用 MCP**：
- ✅ 所有 job 都不依赖 MCP Server
- ✅ 部署更简单，不需要配置 MCP 认证
- ✅ 本地 git 操作更快

---

### 5. 防止 CI 循环

**当前实现（以 `repo/.gitlab-ci.yml` 为准）分两种**：

**A. `claude-assist`（`@claude` 推送修复）**

- **commit message** 使用固定文案，例如：`fix: apply review suggestions from @claude`（**不含** `[skip ci]`）。
- **push** 使用 **`git push -o ci.skip=true`**，跳过**分支**上的新 pipeline，但**不会**像 `[skip ci]` 那样让 **MR pipeline** 等全部被跳过（详见 YAML 内注释）。

**B. `update-memory-bank`**

- 仅在 `memory-bank/` 有变更时提交；commit message 含 **`[skip ci]`**，避免再次跑自身 job。

```text
claude-assist: commit → git push -o ci.skip=true
  → 减少无意义分支 pipeline；MR 仍可更新

update-memory-bank: git commit -m "chore: auto-update memory bank [skip ci]"
  → 不触发依赖 push 的重复 job
```

---

## 📊 与之前方案的差异

### 核心改进

| 维度 | 之前方案 | 最终方案 | 改进点 |
|------|---------|---------|--------|
| **代码查看** | CI 脚本 `git diff > file` | Claude 自己用 git 命令 | ✅ 更灵活，Claude 可以选择性读取文件 |
| **MCP 依赖** | 使用 MCP GitLab | 完全不用 MCP | ✅ 部署更简单，不需要 MCP Server |
| **修复 Review** | 手动触发 `review-apply` job | 评论 `@claude` 自动触发 | ✅ 更便捷，自然语言交互 |
| **评论分类** | Claude 自己理解 | CI 脚本用 jq 预处理 | ✅ 更可靠，确定性强 |
| **权限控制** | `--dangerously-skip-permissions` | `--allowedTools` 白名单 | ✅ 更安全，最小权限原则 |
| **Feature push 审查** | 易误解为只看最新一笔（`git show HEAD`） | **首次 push**：分支快照（`git ls-files` + Read / Glob），**非首次**：`diff_range` + **`git diff`** 覆盖本次 push 整段 | ✅ 首次看「分支上代码」；后续看增量 diff |
| **MR 场景** | 只看最后一个 commit | 查看整个 MR 的 diff（`origin/<target>...HEAD`） | ✅ 更准确 |
| **功能范围** | 只能修复 review 意见 | 任意指令（修复、重构、添加测试等） | ✅ 更灵活 |
| **交互方式** | 点击 Pipeline 按钮 + 填写变量 | 自然语言评论 | ✅ 更自然 |
| **调试性** | 中等 | 高（CI 脚本分类，artifacts 保留） | ✅ 更易调试 |

---

### 删除的功能

| 功能 | 原因 | 替代方案 |
|------|------|---------|
| `review-apply` job | 被 `@claude` 完全取代 | 使用 `@claude 修复 review 意见` |
| MCP GitLab Server | 不需要远程 API | Claude 用本地 git 命令 |
| CI 脚本预处理 diff | Claude 自己调用更灵活 | Claude 用 `git show`/`git diff` |
| `--dangerously-skip-permissions` | 不安全 | 使用 `--allowedTools` 白名单 |

---

### 新增功能

| 功能 | 说明 | 价值 |
|------|------|------|
| **@claude 智能助手** | 通过评论触发任意指令 | 极大提升开发效率 |
| **MR 场景支持** | 在 MR 页面 @claude，查看整个 MR | 更准确的修复 |
| **评论分类** | 区分 AI review 和人类 feedback | 确保人类意见优先 |
| **Webhook 监听器** | 监听 GitLab 评论事件 | 实现 @claude 功能的基础设施 |
| **权限白名单** | 精细化权限控制 | 提高安全性 |

---

## 🎯 使用场景

### 场景 1：日常开发

```
1. 开发者在 feature 分支提交代码
2. CI 自动触发 feature-review
3. 收到飞书通知：🟡 中风险 (2 项)
4. 开发者在 commit 页面评论：@claude 修复第 1 条，第 2 条我稍后处理
5. Claude 自动修复并提交并 **`git push -o ci.skip=true`**
6. 默认**不会**再自动跑一轮 `feature-review`（避免与 bot 推送循环）；需要再审查时可再 push 一笔或更新 MR
```

---

### 场景 2：MR 审查后修复

```
1. 开发者创建 MR：feature/xxx → integration-5.0
2. CI 自动触发 mr-review（全量审查）
3. AI 在 MR 讨论区发布 review 报告
4. 人类 reviewer 补充意见：这里应该用 ConcurrentHashMap
5. 开发者在 MR 页面评论：@claude 修复所有 review 意见
6. Webhook 触发 claude-assist（MR 场景）
7. CI 拉取 MR 的所有讨论并分类（AI review + 人类 feedback）
8. CI fetch 目标分支
9. Claude 用 git diff 查看整个 MR 的变更
10. Claude 修复代码并推送到源分支
11. MR 自动更新
```

**关键点**：
- ✅ 在 MR 页面 @claude，查看的是整个 MR 的 diff，不只是最后一个 commit
- ✅ 人类 feedback 优先级高于 AI review

---

### 场景 3：Commit 评论修复

```
1. 开发者提交代码到 feature 分支
2. CI 自动触发 feature-review
3. AI 在 commit 页面发布 review 评论
4. 开发者在 commit 页面评论：@claude 修复第 1、3 条，跳过第 2 条
5. Webhook 触发 claude-assist（commit 场景）
6. CI 拉取该 commit 的所有评论并分类
7. Claude 用 git show 查看该 commit 的变更
8. Claude 修复代码并推送（`-o ci.skip=true`）
9. 默认不自动再跑 `feature-review`；需要时再推一笔或开/更新 MR
```

**关键点**：
- ✅ 在 commit 页面 @claude，只看该 commit 的变更
- ✅ 可以选择性修复（"跳过第 2 条"）

---

## 🛡️ 安全考虑

### 1. 权限最小化

每个 job 只授予必要的权限，避免过度授权。

### 2. Webhook 验证

使用 `WEBHOOK_SECRET` 验证 webhook 请求，防止未授权访问。

### 3. Token 安全

所有敏感 token 使用 GitLab Masked Variables，不会出现在日志中。

### 4. 防止 CI 循环

`claude-assist` 依赖 **`git push -o ci.skip=true`**；`update-memory-bank` 使用带 **`[skip ci]`** 的提交信息。详见上文「防止 CI 循环」。

### 5. 不使用 MCP

完全不依赖 MCP Server，降低部署复杂度和安全风险。

---

## 📈 监控和优化

### 关键指标

| 指标 | 目标 | 监控方式 |
|------|------|---------|
| Review 成功率 | > 95% | GitLab CI 统计 |
| @claude 响应时间 | < 5 分钟 | Webhook 监听器日志 |
| Token 消耗 | < 50K/次 | `--debug` 输出 |
| 飞书通知成功率 | > 99% | `send-feishu.py` 日志 |

### 成本优化建议

1. **限制 review 频率**：只在代码文件变更时触发
2. **限制执行时间**：设置 `timeout: 15 minutes`
3. **使用更便宜的模型**：根据需要选择 Sonnet 而非 Opus

---

## 📦 完整部署指南

### 阶段 1：基础配置（无需 @claude 功能）

#### 1.1 配置 GitLab CI/CD 变量

**位置**：GitLab 项目 → **Settings** → **CI/CD** → **Variables**

**必需变量**：

| 变量名 | 类型 | 说明 | 如何获取 |
|--------|------|------|---------|
| `ANTHROPIC_API_KEY` | Masked | Claude API Key | 从 https://console.anthropic.com/ 获取 |
| `GITLAB_API_TOKEN` | Masked | GitLab Project Access Token | 见下方步骤 |
| `GITLAB_TRIGGER_TOKEN` | Masked | Pipeline Trigger Token（@claude 功能需要） | 见下方步骤 |

**可选变量**：

| 变量名 | 类型 | 说明 | 如何获取 |
|--------|------|------|---------|
| `FEISHU_APP_ID` | Variable | 飞书自建应用 `app_id` | 见 §1.4 |
| `FEISHU_APP_SECRET` | Masked | 飞书自建应用 `app_secret` | 见 §1.4 |
| `FEISHU_DEFAULT_NOTIFY_EMAIL` | Variable | 飞书收件人兜底邮箱（`claude-assist` / `update-memory-bank`） | 团队公用通知邮箱等 |
| `CLAUDE_MODEL` | Variable | 覆盖 `repo/.gitlab-ci.yml` 默认模型 id | 与 Claude CLI 约定一致 |
| `CODE_REVIEW_REPORT_LANGUAGE` | Variable | `zh`（默认）或 `en` | 项目级 CI/CD Variables |
| `ANTHROPIC_BASE_URL` | Variable | 可选；覆盖 Anthropic API 根 URL | 内网镜像 |
| `CLAUDE_CODE_OAUTH_TOKEN` | Masked | 可选；与 API Key 二选一 | `claude setup-token` |

---

#### 1.2 创建 GitLab API Token

**步骤**：

1. 进入项目 **Settings** → **Access Tokens**
2. Token name: `claude-ci-bot`
3. 选择权限：
   - ✅ `api`（必需：读取评论、触发 Pipeline）
   - ✅ `read_repository`（必需：读取代码）
   - ✅ `write_repository`（必需：Claude 推送代码）
4. 点击 **Create project access token**
5. 复制生成的 token（只显示一次）
6. 在 GitLab 项目中添加变量：
   - Key: `GITLAB_API_TOKEN`
   - Value: `glpat-xxx`（刚才复制的 token）
   - Type: **Masked**
   - Protected: ❌ 不勾选
   - Expand variable reference: ❌ 不勾选

---

#### 1.3 创建 Pipeline Trigger Token

**步骤**：

1. 进入项目 **Settings** → **CI/CD** → **Pipeline triggers**
2. Description: `claude-webhook-trigger`
3. 点击 **Add trigger**
4. 复制生成的 token
5. 在 GitLab 项目中添加变量：
   - Key: `GITLAB_TRIGGER_TOKEN`
   - Value: `glptt-xxx`（刚才复制的 token）
   - Type: **Masked**
   - Protected: ❌ 不勾选
   - Expand variable reference: ❌ 不勾选

---

#### 1.4 配置飞书自建应用（可选）

**步骤**：

1. 打开飞书开放平台：https://open.feishu.cn/ → **创建企业自建应用**
2. 在应用 **凭证与基础信息** 中获取 **App ID**、**App Secret**
3. **权限管理** 中开通（至少）：
   - ✅ `contact:user.email:readonly`
   - ✅ `im:message`
4. **创建版本** → **申请发布** → 租户管理员安装/授权
5. 在 GitLab **CI/CD → Variables** 中新增：
   - Key: **`FEISHU_APP_ID`** — Value: 应用的 App ID  
   - Key: **`FEISHU_APP_SECRET`** — Value: App Secret，**Type: Masked**

**说明**：**`repo/.gitlab/send-feishu.py`** 在 job 内用 **`app_id` + `app_secret`** 调用飞书 **`tenant_access_token/internal`** 换取 token，**无需**把 2 小时过期的 `tenant_access_token` 配进 GitLab。

---

#### 1.5 在 GitLab Runner 机器上安装依赖

**安装 Claude Code CLI**：

```bash
# 使用官方安装脚本
curl -fsSL https://claude.ai/install.sh | bash

# 验证安装
claude --version

# 配置 PATH（如果需要）
export PATH="/opt/homebrew/bin:$PATH"  # macOS
export PATH="/usr/local/bin:$PATH"     # Linux
```

**安装 jq**：

```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# CentOS/RHEL
sudo yum install jq
```

---

#### 1.6 更新 .gitlab-ci.yml

在仓库根目录维护单一的 **`.gitlab-ci.yml`**，与本文档及团队约定一致后提交推送。

---

#### 1.7 测试 feature-review 自动触发

```bash
# 创建 feature 分支
git checkout -b feature/test-ci
echo "test" > test.txt
git add test.txt
git commit -m "test: trigger review"
git push origin feature/test-ci
```

**预期结果**：
- ✅ CI 自动触发 `feature-review` job
- ✅ 在 commit 页面看到 AI 评论

---

### 阶段 2：@claude 功能部署

#### 2.1 部署 Webhook 监听器（物理机器）

**创建部署目录**：

```bash
# 在 GitLab Runner 机器上执行
mkdir -p /path/to/gitlab-runner/webhook
cd /path/to/gitlab-runner/webhook
```

**复制 webhook-listener.py**：

```bash
# 从 vibecoding-ci-kit 克隆中复制（路径以你本机为准）
cp /path/to/vibecoding-ci-kit/runner/.claude/skills/gitlab-runner-onboarding/scripts/webhook-listener.py ./webhook-listener.py
```

**创建 Python 虚拟环境**：

```bash
python3 -m venv venv
source venv/bin/activate
pip install flask requests gunicorn
```

**配置环境变量**：

创建 `.env` 文件：

```bash
cat > .env <<'EOF'
GITLAB_URL=http://your-gitlab-server:port
GITLAB_API_TOKEN=your-gitlab-api-token
GITLAB_TRIGGER_TOKEN=your-trigger-token
WEBHOOK_SECRET=your-random-secret
EOF

chmod 600 .env
```

**创建 launchd 服务（macOS）**：

```bash
# 创建 plist 文件
sudo tee /Library/LaunchDaemons/com.gitlab.webhook.plist > /dev/null <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gitlab.webhook</string>

    <key>ProgramArguments</key>
    <array>
        <string>/path/to/webhook/venv/bin/gunicorn</string>
        <string>-w</string>
        <string>4</string>
        <string>-b</string>
        <string>0.0.0.0:5000</string>
        <string>webhook-listener:app</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/path/to/webhook</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>GITLAB_URL</key>
        <string>http://your-gitlab-server:port</string>
        <key>GITLAB_API_TOKEN</key>
        <string>your-token</string>
        <key>GITLAB_TRIGGER_TOKEN</key>
        <string>your-token</string>
        <key>WEBHOOK_SECRET</key>
        <string>your-secret</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/path/to/webhook/webhook.log</string>

    <key>StandardErrorPath</key>
    <string>/path/to/webhook/webhook.error.log</string>
</dict>
</plist>
EOF

# 修改权限
sudo chown root:wheel /Library/LaunchDaemons/com.gitlab.webhook.plist
sudo chmod 644 /Library/LaunchDaemons/com.gitlab.webhook.plist

# 加载服务
sudo launchctl load /Library/LaunchDaemons/com.gitlab.webhook.plist
```

**创建 systemd 服务（Linux）**：

```bash
sudo tee /etc/systemd/system/gitlab-webhook.service > /dev/null <<'EOF'
[Unit]
Description=GitLab Webhook Listener for @claude
After=network.target

[Service]
Type=simple
User=gitlab-runner
WorkingDirectory=/path/to/webhook
Environment="GITLAB_URL=http://your-gitlab-server:port"
Environment="GITLAB_API_TOKEN=your-token"
Environment="GITLAB_TRIGGER_TOKEN=your-token"
Environment="WEBHOOK_SECRET=your-secret"
ExecStart=/path/to/webhook/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 webhook-listener:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl start gitlab-webhook
sudo systemctl enable gitlab-webhook
sudo systemctl status gitlab-webhook
```

**验证服务**：

```bash
# 测试健康检查
curl http://localhost:5000/health

# 查看日志（macOS）
tail -f /path/to/webhook/webhook.error.log

# 查看日志（Linux）
sudo journalctl -u gitlab-webhook -f
```

---

#### 2.2 配置 GitLab Webhook

**步骤**：

1. 打开 GitLab 项目：`http://your-gitlab-server/your-project`
2. 进入 **Settings** → **Webhooks**
3. 填写配置：
   - **URL**: `http://webhook-server-ip:5000/gitlab-webhook`
   - **Secret token**: `your-webhook-secret`（与 `.env` 中的 `WEBHOOK_SECRET` 一致）
   - **Trigger**: ✅ 只勾选 **Comments**
   - **SSL verification**: ❌ 取消勾选（如果使用 HTTP）
4. 点击 **Add webhook**
5. 点击 **Test** → **Comments events** 测试连通性

**预期结果**：
- ✅ 看到 **HTTP 200** 响应
- ✅ Webhook 日志中看到测试请求

---

#### 2.3 测试 @claude 功能

```bash
# 在任意 commit 页面评论
@claude 请添加一个 README.md 文件
```

**预期结果**：
- ✅ Webhook 监听器收到事件（查看日志）
- ✅ CI 触发 `claude-assist` job
- ✅ 看到新的 commit 添加了 README.md
- ✅ 新的 commit 经 **`git push -o ci.skip=true`** 推送，避免无意义的分支 pipeline 刷屏（与 **`[skip ci]`** 策略不同）

---

## 🔍 故障排查

### 问题 1：feature-review 未触发

**可能原因**：
- 分支名不匹配 `feature/*` 格式
- Claude CLI 未安装或不在 PATH 中
- `ANTHROPIC_API_KEY` 未配置或无效

**排查步骤**：

```bash
# 检查分支名
git branch --show-current

# 检查 Claude CLI
which claude
claude --version

# 在 GitLab Pipeline 页面查看 feature-review job 日志
```

---

### 问题 2：@claude 未触发

**可能原因**：
- Webhook 监听器未启动
- Webhook 配置错误
- `GITLAB_TRIGGER_TOKEN` 未配置

**排查步骤**：

```bash
# 检查监听器状态（macOS）
ps aux | grep gunicorn | grep -v grep

# 检查监听器状态（Linux）
sudo systemctl status gitlab-webhook

# 查看监听器日志
tail -f /path/to/webhook/webhook.error.log

# 测试 Webhook
curl -X POST http://localhost:5000/gitlab-webhook \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: your-webhook-secret" \
  -d '{"object_kind":"note","object_attributes":{"note":"@claude test"}}'
```

---

### 问题 3：飞书通知未收到

**可能原因**：
- **`FEISHU_APP_ID` / `FEISHU_APP_SECRET`** 未配置或错误
- 收件人邮箱在飞书通讯录中无法匹配（`mr-review` 依赖 GitLab **公开邮箱** 或 token 可见的 **`email`**）
- 飞书应用权限或租户未授权

**排查步骤**：

```bash
# 检查提交人邮箱
git log -1 --pretty=format:'%ae'

# 测试飞书 API
curl -X POST 'https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id?user_id_type=open_id' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer your-app-token' \
  -d '{"emails": ["user@example.com"], "include_resigned": true}'

# 查看 CI 日志
# 在 GitLab Pipeline 页面查看 feature-review job 日志
```

---

### 问题 4：Webhook 网络不通

**可能原因**：
- GitLab 服务器无法访问 Webhook 监听器
- 防火墙阻止
- 监听地址配置错误

**排查步骤**：

```bash
# 在 GitLab 服务器上测试
curl http://webhook-server-ip:5000/health

# 检查防火墙（macOS）
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# 检查防火墙（Linux）
sudo ufw status
sudo iptables -L

# 查看监听地址
netstat -an | grep 5000
```

---

## 📁 项目文件结构

**脚手架仓库 vibecoding-ci-kit（克隆根目录）**：

```text
vibecoding-ci-kit/
├── README.md / README.zh.md
├── repo/                              # Track A：整体 rsync 到业务仓库根目录
│   ├── .gitlab-ci.yml
│   ├── .gitlab/send-feishu.py
│   ├── .claude/ …
│   ├── memory-bank/ …
│   ├── CLAUDE.md
│   └── AGENTS.md
├── runner/.claude/skills/gitlab-runner-onboarding/   # Track B：仅 Runner 机
│   ├── SKILL.md
│   └── scripts/webhook-listener.py
└── .claude/
    ├── skills/vibecoding-workflow-onboarding/
    └── plan/vibecoding-ci-kit.md      # 本文档（不随 repo/ 合并）
```

---

## 🎯 部署完成确认清单

### 阶段 1：基础配置（自动审查）
- [ ] 在 GitLab 项目中配置 `ANTHROPIC_API_KEY` 或 `CLAUDE_CODE_OAUTH_TOKEN`
- [ ] 在 GitLab 项目中配置 `GITLAB_API_TOKEN`
- [ ] 在 GitLab Runner 上安装 Claude Code CLI
- [ ] 在 GitLab Runner 上安装 jq
- [ ] 将 **`repo/`** 合并到业务仓库后的 **`.gitlab-ci.yml`** 与脚手架一致
- [ ] 测试 `feature-review` 自动触发

### 阶段 2：@claude 功能
- [ ] 在 GitLab 项目中配置 **`GITLAB_TRIGGER_TOKEN`**（Pipeline Trigger；与 Webhook 配套）
- [ ] 部署 Webhook 监听器服务
- [ ] 配置 Webhook 监听器环境变量
- [ ] 启动 Webhook 监听器服务
- [ ] 在 GitLab 项目中配置 Webhook
- [ ] 测试 Webhook 连通性
- [ ] 测试 `@claude` 评论触发

### 阶段 3：可选功能
- [ ] 配置 **`FEISHU_APP_ID`** + **`FEISHU_APP_SECRET`**（飞书通知）
- [ ] 测试飞书通知功能

---

## 🎓 总结

本方案通过以下核心改进，实现了更智能、更便捷、更可靠的 AI 驱动代码审查系统：

1. **更简单**：完全不使用 MCP，不需要部署 MCP Server
2. **更灵活**：Claude 自己用 git 命令查看代码，可以灵活组合 git 命令和 Read 工具
3. **更便捷**：通过 `@claude` 评论触发，无需手动点击按钮
4. **更可靠**：CI 脚本预处理评论分类，确定性强
5. **更安全**：权限白名单，最小权限原则
6. **更准确**：Feature **首次** push 审分支快照；**后续** push 按 `diff_range` 审连续变更；MR 场景查看整个 MR 的 diff

通过分阶段部署，可以先验证基础功能（自动 review），再逐步启用高级功能（@claude 助手），降低部署风险。

### 核心工作流程（与 `repo/.gitlab-ci.yml` 一致）

```text
feature-review:
  首次 push: stdin 含 first_push=true, review_scope=branch_tree, diff_range=n/a, branch=..., review_report_language=..., ci_code_review=...
  → Claude: git ls-files / Glob + Read（分支快照）；按 skill 与 review_report_language 生成 review-report.md
  非首次: stdin 含 first_push=false, diff_range=<CI_COMMIT_BEFORE_SHA>..HEAD, ...
  → Claude: git diff <diff_range>；同上

mr-review:
  fetch mr_target；stdin: review_level=2, mr_source=..., mr_target=..., review_report_language=..., ci_code_review=...
  → Claude: git diff origin/<mr_target>...HEAD；生成 review-report.md

（可选）FEISHU_APP_ID + FEISHU_APP_SECRET: python3 .gitlab/send-feishu.py …（继承 CODE_REVIEW_REPORT_LANGUAGE；mr-review 收件人优先 MR 作者邮箱）

claude-assist (commit):
  git config user.name claude；git checkout 源分支；curl commit 评论 → 分类
  → Claude 读 diff → commit；git push -o ci.skip=true

claude-assist (MR):
  git diff origin/<target_branch>...HEAD（target 来自 MR API）
  → commit；git push -o ci.skip=true

update-memory-bank:
  git config user.name claude；仅 memory-bank/ 变更时 commit 信息含 [skip ci] 并 push
```
