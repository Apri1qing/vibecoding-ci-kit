# vibecoding-ci-kit

[English](README.md) · [中文](README.zh.md)

**vibecoding-ci-kit** 本仓库**不是业务应用代码**，而是将 **`repo/`** 目录**内容**合并进 **GitLab 应用仓库根目录**的配置与文档（CI、hooks、memory-bank 等）。说明与 [README.md](README.md) 对应；若有歧义，以英文版为准。

**CI：** 目前仅支持 **GitLab**。

## 前置条件

1. **克隆**本仓库。
2. **分支**：在 **`feature/<name>`** 上开发，再合并进 **`integration/...`**（或修改 **`.gitlab-ci.yml`** 中的 **`rules:`**，使 CI 与你们的分支名一致）。

---

## 能做什么

| 能力 | 触发时机 |
|------|----------|
| **Level 1 AI 代码审查** | 推送到 **`feature/*`** |
| **Level 2 AI 审查（MR）** | MR 目标为 **`integration/*`** 或 **`integration-*`** |
| **`@claude`**（在 **commit / MR** 上评论） | 在 **GitLab** 的 **提交**或**合并请求**下**发评论**，文中提及 **`@claude`** 并说明诉求，会**触发流水线**，由 Claude 协助改代码。 |
| **Memory bank** + **`update-memory-bank`** | 推送到 **`integration/*`**；与 **`AGENTS.md`** 及规则保持同步 |

### `repo/.claude/`（以及合并到应用仓根目录的文件）

| 文件 | 作用 |
|------|------|
| **`settings.json`** | 必须存在，**hooks** 才会在**用户每次提交提示**时执行；没有它，**`hooks/`** 里的脚本**不会运行**。 |

| Hooks | 作用 |
|-------|------|
| **`code-review-trigger.py`** | 代码审查 / 重构 /「按项目规则」→ 先读 **`.claude/rules/`**。 |
| **`coding-rule-trigger.py`** | 「记住一条规则」→ 任务结束后往 **`coding-standards.md`** 追加一行。 |
| **`feature-tech-doc-sync-trigger.py`** | 技术文档同步 / 与代码不一致 → **`memory-bank/docs/features/`**。 |
| **`test-plan-sync-trigger.py`** | 测试计划 / 用例同步 → 先走 **test-plan** skill。 |

| Rules | 作用 |
|-------|------|
| **`coding-standards.md`** | 团队编码约定（可由 coding-rule hook 扩展）。 |
| **`memory-bank-framework.md`** | Memory bank 目录结构；**`feature/*`** ↔ **`docs/features/*-tech-doc.md`** 命名。 |

| Skills | 作用 |
|--------|------|
| **`ci-code-review`** | CI 中 `feature-review` / `mr-review` 的 stdin 与报告格式（`CODE_REVIEW_REPORT_LANGUAGE`）。 |
| **`feature-tech-doc`** | **`memory-bank/docs/features/*-tech-doc.md`**。 |
| **`test-plan`** | 测试计划（如 **`memory-bank/docs/tests/`**）。 |

另有：**`CLAUDE.md`**、**`AGENTS.md`**。

---

## 给人类读者

1. **前置条件**见上；在包含 **`repo/`** 的克隆目录执行：

   ```bash
   rsync -a repo/ /path/to/your/app/
   ```

   如有冲突请解决。CI 在**应用仓库**里运行。

2. **GitLab → 设置 → CI/CD → 变量**

   | 变量 | 是否必填 | 用途 |
   |------|----------|------|
   | `GITLAB_API_TOKEN` | 是 | CI 中调用 GitLab API。PAT 权限范围：`api` + `read_repository` + `write_repository`（`write_repository` 为必选，`claude-assist` 和 `update-memory-bank` 需要通过 token push 代码）。 |
   | `GITLAB_TRIGGER_TOKEN` | 是 | 流水线触发令牌；webhook 监听器用于启动 `claude-assist`。 |

   | 变量 | 默认值（见 **`repo/.gitlab-ci.yml`**） | 用途 |
   |------|------------------------------------------|------|
   | `CODE_REVIEW_REPORT_LANGUAGE` | **`zh`** | 审查报告语言；英文可设为 **`en`**。 |
   | `CLAUDE_MODEL` | **`claude-sonnet-4-6`** | CI 里传给 `claude` 的模型。 |
   | `FEISHU_APP_TOKEN` | *未设置* | 未设置则**不**发飞书通知；审查仍会执行。 |

3. **GitLab Runner 机器：**须使用 **GitLab Runner** 执行作业（不是任意 CI Worker）。运行 Job 的系统用户，其 **`PATH`** 上需有 **`claude`** 与 **`jq`**（供 `feature-review`、`mr-review`、`update-memory-bank` 等）。

4. **`@claude`（在 commit / MR 下评论）：** 在**同一台 Runner 机器**上，将 **[`runner/.claude/skills/gitlab-runner-onboarding/`](runner/.claude/skills/gitlab-runner-onboarding/)** 拷到该环境（或放到 `~/.claude/skills/gitlab-runner-onboarding`），用 Claude 打开，并按 **[`SKILL.md`](runner/.claude/skills/gitlab-runner-onboarding/SKILL.md)** 配置 webhook 监听器与 **`GITLAB_TRIGGER_TOKEN`**。

5. **Memory bank：** **CI** — 合并进 **`integration/*`** 后，**下一次 push** 会跑 **`update-memory-bank`**（GitLab 里无需再输入提示词）；依据 **`AGENTS.md`** 与 **`.claude/rules/memory-bank-framework.md`**。**对话** — 用户说 **`update memory bank`** 时做全量核对（框架 **Update Rules §3**）；日常小改见 §1–2 / §4–5。

---

## 给 Agent

1. 加载 **[`vibecoding-workflow-onboarding`](.claude/skills/vibecoding-workflow-onboarding/SKILL.md)**（放到 `~/.claude/skills/`）。

2. **Memory bank — 向用户说明是什么、如何更新**

   - **是什么：** **`memory-bank/`** 是应用仓库里**长期保留的项目知识**（范围、产品、架构、技术栈、当前工作、功能/测试相关 **`docs/`**）。不是业务源码，用于人机跨会话对齐。细节见 **`AGENTS.md`** 与 **`memory-bank-framework.md`** 中的 **Reading strategy**。

   - **如何更新：** 日常修改遵循 **`memory-bank-framework.md`** 的 **Update Rules** §1–2 / §4–5。用户要求 **`update memory bank`** 时，按 **§3** 对根目录下**全部核心** `*.md` 做一次核对（不要只改 `activeContext` / `progress`）。在 **`feature/*`** 上开发时，保持对应的 **`docs/features/*-tech-doc.md`** 与分支一致。**CI** 在推送到 **`integration/*`** 时会刷新 **`memory-bank/`** — 见上文**「给人类读者」第 5 条**。

---

## 许可

MIT — 见 [LICENSE](LICENSE)。
