---
name: code-review-report
description: Use when generating AI-powered code review reports in GitLab CI. Defines the fixed markdown format for Level 1 (feature push) and Level 2 (MR) reviews, including summary and risk classification.
---

# Code Review Report

## Overview

This skill defines the **required** markdown format for AI code reviews in GitLab CI so that:

- Conclusions are traceable
- Risk is classified consistently
- Optional Feishu notifications can parse counts (see `.gitlab/send-feishu.py`)

## Report structure

### Required sections

```markdown
## Summary

[One paragraph: scope, total findings, counts per risk level]

## Risk assessment

| Level | Count | Notes |
|-------|-------|-------|
| Low | N | Naming, style, non-functional improvements |
| Medium | N | Maintainability, likely bugs, performance concerns |
| High | N | Must-fix: security, correctness, data integrity |

> If any **High** findings exist, Feishu title should be prefixed with a high-risk warning when using optional notifications.

## Detailed findings

### Low (N items)

1. [Description]
   - File: `path/to/file:line`
   - Suggestion: [fix]

### Medium (N items)

1. [Description]
   - File: `path/to/file:line`
   - Impact: [impact]
   - Suggestion: [fix]

### High (N items)

1. [Description]
   - File: `path/to/file:line`
   - Impact: [impact]
   - Suggestion: [required fix]

## Passed checks (optional)

- [What looked good]
```

## Risk rubric

| Level | Criteria | Examples |
|-------|----------|----------|
| **Low** | Works; style or minor improvements | Naming, logging, duplication |
| **Medium** | Future bugs, maintainability | NPE risk, resource leaks, hot loops |
| **High** | Security, wrong behavior, data issues | Injection, auth bypass, data corruption |

## Context to read (adjust paths via `AI_REVIEW_DOC_BASE`)

### Level 1 (feature push)

| Resource | Example path | Purpose |
|----------|--------------|---------|
| Rules | `.claude/rules/` | Project conventions |
| Tech doc | `{AI_REVIEW_DOC_BASE}/{branch}-tech-doc.md` | Requirements alignment (skip if missing) |

### Level 2 (MR)

| Resource | Example path | Purpose |
|----------|--------------|---------|
| Rules | `.claude/rules/` | Same as L1 |
| Tech doc | `{AI_REVIEW_DOC_BASE}/{branch}-tech-doc.md` | Requirements |
| Architecture / perf | `docs/`, `memory-bank/` | As configured in MR scope hint |

## Rules

1. **Summary** must be a real paragraph, not only counts.
2. Each issue must include **file:line**.
3. Order **High** first; group by level.
4. Omit empty level sections or write "None".
5. Do not omit findings.

## Level 1 vs Level 2

| Aspect | Level 1 | Level 2 |
|--------|---------|---------|
| Scope | Current push diff | Full MR diff |
| Strictness | Branch policy | Stricter before integration merge |
