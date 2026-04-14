# Memory Bank Framework

Each project uses a `memory-bank/` directory as its knowledge base — the single source of truth for project understanding that persists across sessions.

## Core Files (Required)

Files build on each other in a clear hierarchy: `projectbrief` feeds into `productContext`, `systemPatterns`, and `techContext`, which together inform `activeContext`, which drives `progress`.

| File | Purpose |
|------|---------|
| projectbrief.md | Foundation document — core requirements, goals, scope. Shapes all other files. |
| productContext.md | Why the project exists, problems it solves, how it should work, UX goals. |
| systemPatterns.md | System architecture, key technical decisions, design patterns, component relationships. |
| techContext.md | Technologies used, development setup, technical constraints, dependencies. |
| activeContext.md | Current work focus, recent changes, next steps, active decisions. |
| progress.md | What works, what's left to build, current status, known issues. |

## Optional Files

Create additional files/folders when they help organize deeper knowledge:

- `performance.md` — Query optimization cases, caching strategies, benchmarks
- `docs/` — Feature-level technical documents (requirements, design, API specs, TODOs)

## Feature branch ↔ tech-doc file naming

Maps **`feature/{name}`** branches to **`memory-bank/docs/features/{suffix}-tech-doc.md`** (same rules as the [feature-tech-doc SKILL](../skills/feature-tech-doc/SKILL.md)).

- **Branch shape:** `feature/{name}` — `{name}` may contain multiple segments (e.g. `2024-q1-auth`).
- **suffix:** everything after the **first** `feature/` prefix only (strip one prefix, not multiple).
- **File path:** `memory-bank/docs/features/{suffix}-tech-doc.md`

Formula: `{suffix} = branch.replaceFirst("^feature/", "")` → filename `{suffix}-tech-doc.md`.

| Branch | suffix | Tech doc file |
|--------|--------|---------------|
| `feature/user-auth` | `user-auth` | `memory-bank/docs/features/user-auth-tech-doc.md` |
| `feature/2024-q1-auth` | `2024-q1-auth` | `memory-bank/docs/features/2024-q1-auth-tech-doc.md` |

**Code review:** the **ci-code-review** skill resolves the tech-doc path from stdin `branch` (Level 1) or `mr_source` (Level 2) using the same suffix rule — see that skill’s “Tech-doc path” section.

## When to update `memory-bank/docs/features/`

- **`feature/*`:** Update the tech-doc file given by the table above. Update when that feature’s requirements, design, APIs, or tracked TODO/review material change — keep this file aligned with the code on the branch. Details: [feature-tech-doc SKILL](../skills/feature-tech-doc/SKILL.md).
- **`integration/*` or `release/*`:** Usually **do not** bulk-rewrite feature tech-doc here. Refresh **root** core files and `performance.md` after merge. Edit **`docs/features/*-tech-doc.md` only** if it is still **wrong** vs merged behavior (small fixes), not as the main place to “finish” a full memory-bank pass.

## Reading Strategy

Read memory-bank files **on demand**, not all-at-once for every task.

**General guidelines** (project CLAUDE.md may override with more specific rules):

| Situation | Files to read |
|-----------|---------------|
| First time working on the project | `projectbrief.md` → `techContext.md` → `systemPatterns.md` |
| Need to understand product goals | `productContext.md` |
| Starting a new task | `activeContext.md` → `progress.md` |
| Making architectural decisions | `systemPatterns.md` |
| Writing queries or optimizing performance | `performance.md` |
| Working on a specific feature | Relevant file(s) under `docs/` |

Each project's CLAUDE.md contains a table mapping files to their read-triggers, tailored to that project's needs. Prefer that project-specific guidance over these general defaults.

## Update Rules

Memory bank updates occur when:

1. **Discovering new project patterns** — document in `systemPatterns.md`
2. **After implementing significant changes** — update `activeContext.md` and `progress.md`
3. **When user requests "update memory bank"** — **read and reconcile every core file** (`projectbrief`, `productContext`, `systemPatterns`, `techContext`, `activeContext`, `progress`). Edit each only where reality has drifted; do **not** limit changes to `activeContext` / `progress`—those two are the usual *emphasis* for “what we’re doing now,” but the rest must still be checked. Also follow **When to update `docs/`** for `docs/`, and update `performance.md` when rule 5 applies.
4. **When context needs clarification** — refine the relevant file
5. **After performance optimizations** — document in `performance.md`
