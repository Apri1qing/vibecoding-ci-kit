#!/usr/bin/env python3
"""
UserPromptSubmit hook: detect code review / refactor trigger phrases.
Triggers: Chinese and English phrases such as refactor, optimize, review and simplify.
Effect: inject additional context so the model reads project rules before reviewing code.
"""
import sys
import json

TRIGGERS = [
    '检查并简化', '重构代码', '优化代码', '简化代码', '重构一下',
    '检查代码', '代码重构', '代码优化', '按规范', '按项目规范',
    'refactor', 'simplify the code', 'review and simplify',
    'code review', 'review the code', 'per project rules',
]

CONTEXT_MSG = (
    'The user asked for a code review or refactor. Read all files under `.claude/rules/` '
    'before reviewing or changing code. Apply every applicable rule and remove '
    'unnecessary defensive code where it does not add value.'
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
