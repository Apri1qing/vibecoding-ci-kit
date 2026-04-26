# vibecoding-ci-kit

[English](README.md) · [中文](README.zh.md)

**vibecoding-ci-kit** 把一个 GitLab 应用仓变成 AI 协作工作流：本地 Agent 按项目事实源开发，CI 按事实源审查 feature 分支和 MR，`@claude` 把 GitLab 评论变成代码修改，`memory-bank` 在合并后继续沉淀项目知识。

本仓库**不是业务应用代码**。你需要将 `repo/` 目录**内容**合并进 **GitLab 应用仓库根目录**，为目标仓库加入 CI、hooks、rules、skills 与文档体系。

**CI：** 目前仅支持 GitLab。

## 先看演示

https://github.com/user-attachments/assets/de0b2826-1fe4-46d2-91f1-3552e54af2de

[打开交互演示页](https://apri1qing.github.io/vibecoding-ci-kit/presentation.html?lang=zh)

## 前置条件

1. **分支**：在 `feature/<name>` 上开发，再合并进 `integration/...`（或修改 `.gitlab-ci.yml` 中的 `rules:`，使 CI 与你们的分支名一致）。
2. **飞书邮箱身份打通（如启用飞书）**：统一 Git commit author email、GitLab Public email 与飞书通讯录邮箱。`feature-review` 使用 Git commit author email；`mr-review` 和 `@claude` 优先使用 GitLab Public email。

## Installation

### 推荐方式：Agent onboarding

克隆本仓库，然后让你的编程 Agent 阅读 [`vibecoding-workflow-onboarding`](.claude/skills/vibecoding-workflow-onboarding/SKILL.md)，帮助你把 `repo/` onboarding 到目标 GitLab 应用仓。

强烈推荐这种方式。Agent 可以帮你合并文件、处理冲突、检查 GitLab 变量、Runner、飞书选项和 `@claude` webhook 配置，比手动复制更不容易漏步骤。

如果你想人工安装，见 [Manual 安装](#manual-安装)。

## 能做什么

| 能力 | 用户得到什么 |
|------|--------------|
| 本地开发规范 | Agent 先读 `AGENTS.md`、`memory-bank`、rules、hooks、skills，再开始工作；不是只靠当前聊天上下文猜项目。 |
| 功能文档闭环 | `feature/*` 上的 tech doc 是技术真相页，test plan 是验证依据；关键词触发 hooks 推动需求、API、TODO、测试场景持续同步。 |
| `feature-review` | push 到 `feature/*` 时触发，在开发中尽早发现问题。 |
| `mr-review` | MR 指向 `integration/*` 或 `integration-*` 时触发，用完整 MR diff 和项目上下文做合并前把关。 |
| `@claude` | 在 GitLab commit 或 MR 下评论并提及 `@claude`，Claude 读取 diff、AI review 和人工评论后回推修复 commit。 |
| 飞书通知 | 配好飞书变量和邮箱映射后，review 和 assist 结果可回写 GitLab，也可以按人 DM 到飞书。 |
| Memory bank 沉淀 | MR 合并后，对 `integration/*` 的 push 会触发 `update-memory-bank` pipeline job，自动沉淀长期项目知识。 |

## 本地开发：让 Agent 按项目事实工作

接入后，`AGENTS.md`、`memory-bank`、`.claude/rules/`、hooks、skills 会进入你的应用仓。它们共同定义 Agent 先读什么、按什么规则改代码、什么时候同步功能技术文档和测试计划。

**核心文件**

| 文件 | 作用 |
|------|------|
| `AGENTS.md` | Agent 的仓库入口，定义阅读顺序和工作方式。 |
| `memory-bank/` | 长期项目知识，包括产品、架构、技术栈、当前进展、功能文档和测试文档。 |
| `.claude/rules/coding-standards.md` | 团队编码约定，可由 coding-rule hook 扩展。 |
| `.claude/rules/memory-bank-framework.md` | memory-bank 结构、feature tech doc 命名和更新规则；用户说 `update memory bank` 时，Agent 会按它核对并更新 memory bank。 |

**Hooks**

| Hook | 作用 |
|------|------|
| `code-review-trigger.py` | 用户要求代码审查、重构或“按项目规则”时，先读取 `.claude/rules/`。 |
| `coding-rule-trigger.py` | 用户要求“记住一条规则”时，把规则追加到 `coding-standards.md`。 |
| `feature-tech-doc-sync-trigger.py` | 需求、设计、API、TODO 与功能技术文档不一致时，推动 feature tech doc 同步。 |
| `test-plan-sync-trigger.py` | 测试计划和测试用例更新时，先走 `test-plan` skill。 |

**Skills**

| Skill | 作用 |
|-------|------|
| `ci-code-review` | 定义 CI 中 `feature-review` / `mr-review` 的输入和报告格式（`CODE_REVIEW_REPORT_LANGUAGE`）。 |
| `feature-tech-doc` | 定义 `memory-bank/docs/features/*-tech-doc.md`。 |
| `test-plan` | 定义测试计划，例如 `memory-bank/docs/tests/`。 |

## GitLab Review：按项目事实源把关

`feature-review` 和 `mr-review` 不是普通的代码风格点评，而是在 GitLab 流程里检查代码变更是否符合项目事实源。

| 对比项 | `feature-review` | `mr-review` |
|--------|------------------|-------------|
| 触发 | push 到 `feature/*`。 | MR 指向 `integration/*` 或 `integration-*`。 |
| 目的 | 开发中尽早发现问题。 | 合并前更严格把关。 |
| 事实来源 | 分支代码快照或增量 diff、`.claude/rules/*.md`、对应的 `memory-bank/docs/features/*-tech-doc.md`、`ci-code-review` skill。 | 完整 MR diff、`.claude/rules/*.md`、feature tech doc、`memory-bank/systemPatterns.md`、`memory-bank/techContext.md`、`memory-bank/performance.md`、`ci-code-review` skill。 |

## Manual 安装

1. 将 `repo/` 复制进你的应用仓：

   ```bash
   rsync -a repo/ /path/to/your/app/
   ```

   如有冲突请解决。CI 在应用仓里运行，不在本 kit 仓库里运行。

2. 配置 GitLab CI/CD 变量。

   token 和 secret 类变量应按 GitLab protected 或 masked CI/CD variables 管理。

   **Required GitLab access**

   - `GITLAB_API_TOKEN`：GitLab API token。PAT 权限范围：`api`、`read_repository`、`write_repository`；`claude-assist` 和 `update-memory-bank` 需要写权限来 push commit。
   - `GITLAB_TRIGGER_TOKEN`：pipeline trigger token，webhook listener 用它启动 `claude-assist`。

   **Choose one Claude authentication method**

   - `ANTHROPIC_API_KEY`：Anthropic API key 认证。
   - `CLAUDE_CODE_OAUTH_TOKEN`：来自 `claude setup-token` 的 OAuth token，通常以 `sk-ant-oat01-` 开头。

   **Optional runtime settings**

   - `ANTHROPIC_BASE_URL`：内部镜像或企业代理使用的 Anthropic endpoint。
   - `CLAUDE_MODEL`：CI 里传给 `claude` 的模型；默认值见 `repo/.gitlab-ci.yml`。
   - `CODE_REVIEW_REPORT_LANGUAGE`：审查报告语言；默认 `zh`，英文设为 `en`。

   **Optional Feishu notifications**

   - `FEISHU_APP_ID`：飞书 app id。
   - `FEISHU_APP_SECRET`：飞书 app secret。
   - `FEISHU_DEFAULT_NOTIFY_EMAIL`：无法解析作者身份时的兜底通知邮箱。

3. 准备 GitLab Runner 机器。

   使用 GitLab Runner。运行 Job 的系统用户，其 `PATH` 上需要有 `claude` 和 `jq`，供 `feature-review`、`mr-review`、`claude-assist`、`update-memory-bank` 使用。推送代码前请确保 Runner 已注册并在线，否则 job 会一直 pending。

4. 启用 commit / MR 下的 `@claude` 评论。

   在同一台 Runner 机器上，将 [`runner/.claude/skills/gitlab-runner-onboarding/`](runner/.claude/skills/gitlab-runner-onboarding/) 拷到该环境，或放到 `~/.claude/skills/gitlab-runner-onboarding`。用 Claude 打开它，并按其中的 `SKILL.md` 配置 webhook listener 与 `GITLAB_TRIGGER_TOKEN`。

## 许可

MIT - 见 [LICENSE](LICENSE)。
