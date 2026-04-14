---
name: ci-code-review
description: AI code review triggered by GitLab CI (feature-review / mr-review); report format and required inputs. Also used when writing or parsing review Markdown for GitLab or Feishu webhooks.
---

# CI Code Review (GitLab CI)

This skill matches **`.gitlab-ci.yml` jobs `feature-review` / `mr-review`**: CI writes `ci_code_review: .claude/skills/ci-code-review/SKILL.md` on stdin (this file). **Read this file first**, then produce output using the sources below and the report structure.

## stdin: `review_report_language`

CI passes e.g. `review_report_language: zh` or `review_report_language: en` (from `CODE_REVIEW_REPORT_LANGUAGE` in `.gitlab-ci.yml`).

| Value | Output |
|-------|--------|
| `zh` (default if omitted) | Entire report in **Chinese** — headings, tables, explanations, summary. |
| `en` | Entire report in **English**. |

The skill file stays English-only; **you** choose the output language from stdin, not from this document’s language.

Override per project: **GitLab → Settings → CI/CD → Variables** → `CODE_REVIEW_REPORT_LANGUAGE` = `zh` or `en`.

## stdin: Level 1 `first_push` and `review_scope`

`feature-review` passes one of two modes:

| stdin | Meaning |
|-------|---------|
| `first_push: true` and `review_scope: branch_tree` | **First push** to this `feature/*` branch (`CI_COMMIT_BEFORE_SHA` unset or all zeros). Review the **code as it exists on the branch at `HEAD`** (tracked files), **not** `git diff` vs another ref. |
| `first_push: false` and `review_scope: diff_range` | **Later pushes**. Use `git diff` with stdin `diff_range` (e.g. `before_sha..HEAD`). |

When `diff_range` is `n/a`, treat it as **no diff range** — do **not** use `git diff` as the primary review input.

### Branch tree review (first push)

1. Enumerate tracked files with Bash (e.g. `git ls-files` or `git ls-files | grep -E '\.(java|kt|ts|tsx|js|vue|go|py)$'` as appropriate for the repo) or **Glob**; respect `.gitignore` (tracked files only).
2. Use **Read** (and **Grep** as needed) to inspect **source** relevant to the feature; skip huge generated/binary dirs if the repo clearly separates them (e.g. `node_modules/`, `target/`).
3. **Do not** rely on `git diff origin/main...HEAD` or any merge-base diff as the main scope — the goal is **snapshot** review of the branch’s **current** code.
4. Still apply **tech-doc** and **rules** as above.

Large repos: prioritize high-risk paths (auth, API, DB) if listing everything is impractical within the job; note any scope limitation in the summary.

## Tech-doc path

`memory-bank/docs/features/{suffix}-tech-doc.md` where `suffix` is stdin `branch` (Level 1) or `mr_source` (Level 2) with the first `feature/` prefix removed. Full branch-to-file rules: **`.claude/rules/memory-bank-framework.md`** (“Feature branch ↔ tech-doc file naming”).

## Sources of truth

| Material | L1 (first push) | L1 (later push) | L2 |
|----------|-------------------|-----------------|----|
| Code | Tracked files at `HEAD` (`git ls-files` + **Read** / **Glob**); **not** `git diff` vs another branch | `git diff` + stdin `diff_range` | Full MR: `git diff origin/<mr_target>...HEAD` |
| Rules | `.claude/rules/` | Same | Same |
| Requirements | Tech doc; **skip requirement alignment if none** | Same | Same |
| Architecture / tech / perf | — | — | `memory-bank/systemPatterns.md`, `techContext.md`, `performance.md` if present |

Level 2 must be stricter than Level 1 (pre-merge to integration).

## Report structure

Use the outline below. **Localize** section titles and all prose to match `review_report_language` (Chinese when `zh`, English when `en`). Emoji section headers are optional; keep them consistent with the chosen language.

Output plain Markdown only (do not wrap the whole report in a code fence).

```markdown
## … Summary …
[One paragraph: scope, issue counts, counts per severity]

## … Risk assessment …
| … | Count | … |
| 🟢 / 🟡 / 🔴 | N | … |

## … Detailed findings …
### … high / medium / low risk …
1. … `path:line` …

## … Passes … (optional)
```

## Severity

🟢 Minor improvement · 🟡 Potential issue · 🔴 Functional / security / data — always cite evidence. Describe severity in the **same language** as the report.

## Rules

- The summary must not be numbers only; each item includes **`file:line`**; order 🔴→🟡→🟢; do not under-report.
- Feishu (if used): title prefix reflects 🔴/🟡 counts; use the **same language** as the report; body uses links.
