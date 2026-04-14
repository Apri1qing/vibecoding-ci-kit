#!/usr/bin/env python3
"""
UserPromptSubmit hook: when requirements or design may have drifted from
memory-bank/docs/features/ tech docs, or the user asks to sync docs.

On match, inject additionalContext so the agent aligns the tech doc before coding.
"""
import sys
import json

EXPLICIT = [
    '同步技术文档', '同步需求文档', '更新技术文档', '更新需求文档',
    '写回技术文档', '写进技术文档', '更新功能技术文档',
    '同步 tech-doc', '更新 tech-doc', 'feature-tech-doc',
    '按刚才说的更新文档', '把刚才定的写进文档', '对话结论写进文档',
    '对话里定的方案', 'sync tech doc', 'sync the tech doc',
    'update tech doc', 'update the tech doc', 'update feature tech doc',
    'document this decision', 'write this to the tech doc',
]

DRIFT = [
    '需求变了', '需求有变', '方案改了', '技术方案调整',
    '实现和文档不一致', '文档和实现不一致', '文档需要同步', '文档要对齐',
    '对需求的理解', '最终方案是', '按我们讨论的结果',
]

FEATURE_CHANGE = [
    '新增字段', '加字段', '添加字段', '增加字段',
    '新增接口', '加接口', '添加接口', '增加接口',
    '新增功能', '加功能', '添加功能', '增加功能',
    '修改字段', '改字段', '调整字段',
    '修改接口', '改接口', '调整接口',
    '修改逻辑', '改逻辑', '调整逻辑',
    '删除字段', '去掉字段', '移除字段',
    '删除接口', '去掉接口', '移除接口',
    '改成', '换成', '替换成',
    'add field', 'new field', 'add column',
    'modify field', 'change field', 'update field',
    'remove field', 'delete field',
]

TRIGGERS = EXPLICIT + DRIFT + FEATURE_CHANGE

CONTEXT_MSG = (
    'Requirements or design may have diverged from the feature tech doc under '
    '`memory-bank/docs/features/`, or the user asked to write conclusions back '
    'into the doc. Before implementing further:\n'
    '1. Resolve the doc path: if `git branch --show-current` is `feature/{name}`, '
    'use `memory-bank/docs/features/{name}-tech-doc.md`. If not a feature branch '
    'or the path is unclear, confirm with the user.\n'
    '2. Read `.claude/skills/feature-tech-doc/SKILL.md` and '
    '`.claude/rules/memory-bank-framework.md` (sections on when to update docs).\n'
    '3. Update the doc with agreed requirements, design, APIs, and TODO changes: '
    'revise sections 1–4 as needed; append one row to section 5 revision history '
    '(date, summary, affected sections); keep section 3 TODO status / DoD / next '
    'steps consistent with reality.\n'
    '4. If details are incomplete but recent turns changed the plan, treat the '
    'latest consensus in the thread as source of truth; do not leave stale text.\n'
    'Update the doc before more code unless the user explicitly asked for code only.'
)

try:
    data = json.load(sys.stdin)
    prompt = data.get('prompt', '') or ''
    if any(t in prompt for t in TRIGGERS):
        print(json.dumps({
            'hookSpecificOutput': {
                'hookEventName': 'UserPromptSubmit',
                'additionalContext': CONTEXT_MSG,
            }
        }))
except Exception:
    pass
