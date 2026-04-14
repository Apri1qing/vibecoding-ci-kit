#!/usr/bin/env python3
"""
UserPromptSubmit hook: detect prompts asking to record a new coding rule.
Triggers: remember this style / rule / pattern (Chinese and English).
Effect: inject context to append new rules to coding-standards.md after the task.
"""
import sys
import json

TRIGGERS = [
    '记住这个写法', '记住这种写法', '记住这个规则', '记住这个pattern',
    '以后别这样写', '以后不要这样写', '不要这样写', '以后不要这样',
    'remember this style', 'remember this rule', 'remember this pattern',
]

CONTEXT_MSG = (
    'The user asked to record a new coding rule. After finishing the current task, '
    'append the rule to `.claude/rules/coding-standards.md` in the right section '
    '(Defensive Programming / Error Handling / Code Style). '
    'One short sentence per rule; no implementation detail or class names.'
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
