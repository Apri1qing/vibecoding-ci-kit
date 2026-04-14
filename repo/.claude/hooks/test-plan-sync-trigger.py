#!/usr/bin/env python3
"""
UserPromptSubmit hook: detect test-plan authoring or sync triggers.
When the user asks to write/update a test plan or sync cases after doc changes,
inject context to read the test-plan SKILL first.
"""
import sys
import json

EXPLICIT = [
    '写测试计划', '生成测试计划', '创建测试计划', '新建测试计划',
    '更新测试计划', '同步测试计划', '补充测试计划',
    '写测试用例', '生成测试用例', '生成 TC', '补充 TC', '更新 TC',
    '测试场景', '测试方案',
    'write test plan', 'create test plan', 'update test plan',
    'generate test cases', 'generate TC', 'update TC',
    'test plan', 'test cases',
]

DRIFT = [
    '接口变了', '接口改了', '接口有变更',
    '需求变了', '需求改了', '方案调整', '技术方案有变',
    '测试计划要更新', '测试计划要同步', '测试计划跟文档对齐',
    '更新测试计划', '同步测试',
    'sync test plan', 'update test plan', 'align test plan',
    'test plan needs update', 'test plan out of date',
]

TRIGGERS = EXPLICIT + DRIFT

CONTEXT_MSG = (
    'The user asked to write or update a test plan, or to sync test cases after '
    'feature tech doc changes. Before proceeding:\n'
    '1. Read `.claude/skills/test-plan/SKILL.md` for TC naming, structure, and templates.\n'
    '2. Locate the test plan file: if `git branch --show-current` is `feature/{name}`, '
    'the default path is `memory-bank/docs/tests/test-plan-{name}.md`. '
    'Create from the SKILL template if missing; otherwise update incrementally.\n'
    '3. If this was triggered by a tech doc change: compare API definitions and '
    'update affected TC inputs/assertions; add TCs for new behavior; mark removed '
    'logic as skipped in TCs; append a row to the change log (date, summary, '
    'affected TCs).\n'
    '4. Sync the TODO list: for TODOs marked done in the tech doc section 3, '
    'set the matching test status to passed or failed as appropriate.\n'
    'Follow the SKILL output format; do not skip TC numbering.'
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
