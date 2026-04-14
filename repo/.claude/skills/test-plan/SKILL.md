---
name: test-plan
description: Write or update feature test plan documents. Use when the user asks to write a test plan, update test cases, generate TCs, or when a feature tech doc change requires syncing test scenarios. Supports both API interface testing and unit/integration testing.
---

# Test Plan Skill

## Where to store documents

Test plans **sit next to the code or feature docs under test**. Path is user-specified or inferred as follows:

| Scenario | Recommended path |
|----------|------------------|
| Feature iteration | `memory-bank/docs/tests/test-plan-{feature-name}.md` |
| Single module | Same directory as module source, named `TEST_PLAN.md` |
| User explicitly specifies | Follow the user’s path |

## TC naming

```
[TC-{three-digit id}] {short description of what is tested}

Examples:
[TC-001] Normal analysis request returns expected data
[TC-002] Drill-down API returns non-duplicate content
```

- Group by feature/module; number sequentially within each group
- Use different IDs for happy path, boundary, and error scenarios for the same feature

---

## API test case format

```markdown
#### [TC-{id}] {short description}

- **Feature area**: {module or feature}
- **Scenario**: {one-line test intent}
- **Endpoint**: {HTTP METHOD} {API PATH}
- **Request body / params**:
  ```json
  { ... }
  ```
- **Assertions**:
  1. return_code = 0 (or expected error code)
  2. {field-level checks}
  3. {boundary / error handling}
- **Expected outcome**: {brief expected response}
```

## Unit / integration test case format

```markdown
#### [TC-{id}] {short description}

- **Under test**: `{ClassName#methodName}`
- **Scenario**: {one-line test intent}
- **Preconditions**: {mocks / data setup}
- **Inputs**: {parameters}
- **Assertions**:
  1. {return value}
  2. {side effects / state}
- **Expected outcome**: {brief expected behavior}
```

---

## TODO-LIST (aligned with feature tech doc)

When a feature tech doc exists, the TODO-LIST references its TODO IDs:

| ID | Task | Priority | Test status | Test result | Last updated |
|----|------|----------|-------------|-------------|--------------|
| T1 | {description} | P0 | `pending` \| `in_progress` \| `passed` \| `failed` | {notes} | YYYY-MM-DD |

**Status flow**: `pending` → `in_progress` → `passed` / `failed`

---

## Document outline template

```markdown
# {Feature name} — Test plan

## Overview

- **Goals**: {what this round covers}
- **Scope**: API tests / unit tests / both
- **Related docs**: [feature tech doc link] (if any)

## Scenarios

### 1. {Feature group} (TC-001 ~ TC-0XX)

#### [TC-001] {point under test}
...

## TODO-LIST

| ID | Task | Priority | Test status | Test result | Last updated |
|----|------|----------|-------------|-------------|--------------|

## Change log

| Date | Change | Affected TCs |
|------|--------|--------------|
```

---

## Workflow to produce a test plan

1. **Read the code or tech doc** for the feature; understand APIs and core logic
2. **Derive test points**: happy path → boundaries → errors / return codes
3. **Write TCs in the formats above**; for API tests, include full request JSON where applicable
4. **Fill TODO-LIST**, referencing TODO IDs from the feature doc when present
5. **When the feature doc changes**: reconcile API/logic changes → update or add TCs → append the change log
