---
name: feature-tech-doc
description: Use when writing or updating feature technical docs under memory-bank/docs/features/ (e.g. *feature*tech*.md), restructuring requirements vs design, API specs, TODO lifecycle, agent handoff columns, or syncing docs after code changes.
---

# Feature technical documentation

## Overview

This skill defines structure, maintenance, and **multi-agent handoff** TODO conventions for files under `memory-bank/docs/features/`. Goals: **separate requirements from implementation**, **traceable design changes**, **inspectable API contracts**, **do not substitute Git SHAs for technical explanation**, and **any agent reading this page knows what to do next**.

## Branch and file naming

Same as **`.claude/rules/memory-bank-framework.md`** (“Feature branch ↔ tech-doc file naming”). The filename must match the feature branch:

```
Branch:  feature/{name}
File:    memory-bank/docs/features/{name}-tech-doc.md

Rule:    branch.removePrefix("feature/") + "-tech-doc.md"
Example: feature/2024-q1-auth → memory-bank/docs/features/2024-q1-auth-tech-doc.md
```

CI uses this rule to locate the tech doc for Level 1 push review and Level 2 MR review.

## Creating a doc from requirements

After the branch exists:

1. Derive path: `memory-bank/docs/features/{name}-tech-doc.md`
2. Gather requirements:
   - **URL**: fetch content (WebFetch or MCP)
   - **Chat**: extract from the conversation
3. Generate using the template below: §1 Requirements → §2 Design (draft) → §3 TODO table → §4 APIs
4. User reviews, then commit

## Required sections

1. **Metadata**: title, iteration/scope, `Last updated`, who maintains this page and when.
2. **Overview** (optional, recommended): summary table; state that **§3 TODO is authoritative** for execution status.
3. **§1 Requirements**: per capability — background, users/scenarios, acceptance; **concrete examples** when useful (request JSON, before/after filters, UI behavior). No class names/SQL unless the example needs them.
4. **§2 Technical design**: data layer (tables/views/migrations), domain model, layer responsibilities, constraints and algorithms. **Must include “Impact on current code”** (rename/deprecate/compatibility/transactions). **Do not** put commit SHAs in the design.
5. **§3 TODO-LIST**: **for agents**; column rules below.
6. **§4 API documentation**: required if this iteration adds or changes REST contracts; request/response field tables follow **“§4 REST field table conventions”** below; otherwise state “No new/changed REST APIs this iteration”.
7. **§5 Maintenance**: **revision history** (date | summary | affected sections) + **agent update checklist**.
8. **§6 Review log** (CI appends): Level 1 push findings appended by CI. Columns: `| Date | Commit range | Issue | Severity | Status |`.

Optional **appendix**: table/API index, pointers to other skills; avoid duplicating the main body.

## §3 TODO-LIST (agent handoff)

### Purpose

With multiple agents or sessions, **§3 is the single source of truth** for what to do next (overview tables must not contradict §3). Before ending a session, write handoff into §3 so the next session does not re-discover scope.

### Columns (keep all headers; use `—` when empty)

| Column | Meaning |
|--------|---------|
| **ID** | Stable id (`T2`, `ARCH-1`); same id in history and deprecation notes. |
| **Priority** | `P0` / `P1` / `P2` or `—`; blocks others or release. |
| **Task** | Short title; details may reference §2 sections. |
| **Status** | `pending` \| `in_progress` \| `done` \| `deprecated`. |
| **DoD** | What “done” means: behavior + how to verify. |
| **Next step** | **Required for `pending` / `in_progress`**: first executable action for the next agent (file/method or one command), not “keep going”. `done` / `deprecated` → `—`. |
| **Blocked / deps** | External deps, review waits, env; other TODO ids; else `—`. |
| **Anchors** | Main code paths + §1/§2/§4 references. |
| **Last updated** | `YYYY-MM-DD`; update when status or handoff changes. |

### Rules by status

| Status | Next step | Blocked | DoD | Notes |
|--------|-----------|---------|-----|-------|
| **pending** | Suggest first action if planned; else `TBD: see §2.x` | List dep TODO or external condition | Must be verifiable | — |
| **in_progress** | **Required**; where done vs remaining lives in code | If paused, **required** reason | Same | Optional long notes in §3.2 |
| **done** | `—` | `—` | One-line how we verified | **Anchor** to final code and §4 |
| **deprecated** | `—` | e.g. “dependency gone” | `—` | **Required**: reason + **replacement task id** |

### §3.2 In-progress notes (optional)

For **`in_progress`** when the table is too small, use bullets:

- **What changed this round** (file-level; no commit ids)
- **Branch or environment** if non-default
- **Open decisions / product questions**
- **Do not** write “half done” without a **Next step** row

If nothing in progress: `No in-progress tasks; update the table and this section when there are.`

### TODO and design changes (deprecation)

- If design makes a task unnecessary: set **`deprecated`**, note **reason** and **replacement id**.
- **Do not delete** deprecated rows.
- Add a §5 revision row.
- For breaking redesigns: mark **Breaking change** in history and separate current vs historical TODOs.

## §4 REST field table conventions

For **§4** describing **single DTOs / nested objects**, use Markdown tables. Common wrappers (e.g. `DataResponse<T>` with `return_code` / `return_message` / `data`) may be documented once in a “General conventions” subsection under §4; the rules below focus on **`data` payloads** and **request JSON**.

### Headers

| Kind | Columns |
|------|---------|
| **Request body** | **Field** \| **Type** \| **Required** \| **Description** |
| **Response (`data`)** | **Field** \| **Type** \| **Description** |

- **No “Required” column on responses** (not a client “required” concept).

### Nesting

- Child fields use **`↳`** in the **Field** column, scoped to the **nearest previous non-↳ parent**.
- Deeper nesting adds **`↳`** (e.g. **`↳↳`** for second level under parent).
- Consecutive **`↳`** rows belong to the same parent until the next top-level field without **`↳`**.

### Notes

- **Field** names match code / JSON (camelCase per DTO).
- **Type**: language types or stable names (`List<Long>`, `SomeEnum`); generics may say “see `Foo` DTO” with another table.
- Examples, curl, env notes **do not replace** §4 field tables; put extras in a companion doc or `log/`, not the canonical `*-tech-doc.md`.

## Agent update checklist

After related code merges or changes:

1. Align Controller/DTO/migrations with **§2**, **§4** (including field tables), and **impact**.
2. Sync **§3**: status, next step, blocked, last updated; mark **done** with DoD summary.
3. Before stopping on **`in_progress`**: update **next step**, **blocked**, and §3.2 if needed.
4. Before claiming “doc matches code”, run the project’s verification (lint/build/validate).
5. Do not use commit ids instead of explaining impact.
6. Append a row to §5 for every material change.

## New doc template

```markdown
# {Iteration title} — feature technical doc

## Metadata

- **Scope**:
- **Last updated**: YYYY-MM-DD
- **Maintenance**: Owner updates during dev/QA/release; major design changes need revision history.

## Overview

| ID | Capability | Summary |
|----|------------|---------|
| 1 | … | … |

(Execution status is authoritative in §3 TODO.)

## 1. Requirements

### 1.1 …

## 2. Technical design

### 2.1 …

#### Impact on current code

- …

## 3. TODO-LIST

(For agents: column definitions are in the feature-tech-doc SKILL.)

| ID | Priority | Task | Status | DoD | Next step | Blocked | Anchors | Last updated |
|----|----------|------|--------|-----|-----------|---------|---------|--------------|
| T1 | P0 | … | pending | … | … | … | §2.1; `path/to/file` | YYYY-MM-DD |

### 3.1 Deprecated tasks (history)

| ID | Task | Status | Notes |
|----|------|--------|-------|

### 3.2 In-progress notes

No in-progress tasks; update the table and this section when there are.

## 4. API documentation

(Write if APIs change; else “No new/changed REST contracts this iteration.”)

**Field tables**: request **Field | Type | Required | Description**; response **Field | Type | Description**; nesting with **`↳` / `↳↳`**. See SKILL “§4 REST field table conventions”.

## 5. Maintenance

### Revision history

| Date | Summary | Sections |
|------|---------|----------|
| YYYY-MM-DD | Initial draft | All |

### Agent checklist

- See SKILL “Agent update checklist”.

## 6. Review log

Appended by CI; do not delete existing rows when editing manually.

| Date | Commit range | Issue | Severity | Status |
|------|----------------|-------|----------|--------|
```

## When NOT to use

- Pure product PRDs or non-implementation UX specs: you do not need the full template; link the PRD and reference section numbers in the tech doc.
