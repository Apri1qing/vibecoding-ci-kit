#!/usr/bin/env python3
"""
Send a Feishu (Lark) interactive card with a condensed code-review summary.

Requires env:
  FEISHU_APP_TOKEN — tenant app access token (contact + im scopes).
  CODE_REVIEW_REPORT_LANGUAGE — optional, same as CI review output: zh (default) or en.
    Card labels and generated lines match this language.

Docs: https://open.feishu.cn/document/ (Feishu Open Platform)
"""
import json
import urllib.request
import urllib.error
import sys
import os
import re
import uuid

if len(sys.argv) < 5:
    print(
        "Usage: send-feishu.py <report_file> <title> <review_url> <author_email>",
        file=sys.stderr,
    )
    sys.exit(1)

report_file = sys.argv[1]
card_title = sys.argv[2]
review_url = sys.argv[3]
author_email = sys.argv[4]

feishu_app_token = os.environ.get("FEISHU_APP_TOKEN")
if not feishu_app_token:
    print("Error: FEISHU_APP_TOKEN is not set", file=sys.stderr)
    sys.exit(1)


def resolve_ui_lang() -> str:
    raw = (os.environ.get("CODE_REVIEW_REPORT_LANGUAGE") or "zh").strip().lower()
    if raw.startswith("zh"):
        return "zh"
    if raw.startswith("en"):
        return "en"
    return "zh"


UI = {
    "zh": {
        "default_summary": "审查已完成。",
        "line_high": "高风险 × {}",
        "line_medium": "中风险 × {}",
        "line_low": "低风险 × {}",
        "no_notable_risks": "未发现明显风险",
        "badge_high": "高风险（{}）",
        "badge_medium": "中风险（{}）",
        "badge_pass": "已通过",
        "title_high": "[高风险] {}",
        "title_medium": "[中风险] {}",
        "title_pass": "[已通过] {}",
        "risk_level": "风险等级",
        "risk_overview": "风险概况",
        "author": "提交人",
        "summary": "审查总结",
        "view_full": "查看完整报告",
    },
    "en": {
        "default_summary": "Review completed.",
        "line_high": "High × {}",
        "line_medium": "Medium × {}",
        "line_low": "Low × {}",
        "no_notable_risks": "No notable risks",
        "badge_high": "High risk ({})",
        "badge_medium": "Medium risk ({})",
        "badge_pass": "Passed",
        "title_high": "[High risk] {}",
        "title_medium": "[Medium risk] {}",
        "title_pass": "[Passed] {}",
        "risk_level": "Risk level",
        "risk_overview": "Risk overview",
        "author": "Author",
        "summary": "Summary",
        "view_full": "View full report",
    },
}


def get_open_id_by_email(email: str, app_token: str):
    """Resolve Feishu open_id for an email via Contact API."""
    url = (
        "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id"
        "?user_id_type=open_id"
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {app_token}",
    }
    payload = {"emails": [email], "include_resigned": True}

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)

    try:
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode())

        if result.get("code") == 0:
            user_list = result.get("data", {}).get("user_list", [])
            if user_list:
                open_id = user_list[0].get("user_id")
                print("Resolved open_id for author email")
                return open_id
            print("Warning: no Feishu user for email", file=sys.stderr)
            return None
        print(f"Warning: batch_get_id failed: {result.get('msg')}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"Warning: Feishu API request failed: {e.reason}", file=sys.stderr)
        return None


lang = resolve_ui_lang()
L = UI[lang]

feishu_open_id = get_open_id_by_email(author_email, feishu_app_token)

with open(report_file, encoding="utf-8") as f:
    report = f.read()


def extract_risk_count(report_text: str, patterns: list) -> int:
    for pattern in patterns:
        match = re.search(pattern, report_text)
        if not match:
            continue
        if match.lastindex and match.lastindex >= 1:
            return int(match.group(1))
        num_match = re.search(r"(\d+)", match.group(0))
        if num_match:
            return int(num_match.group(1))
    return 0


_HIGH_PATTERNS = [
    r"🔴[^\n|]*\|\s*(\d+)",
    r"🔴\s*高风险[^\n|]*\|\s*(\d+)",
    r"(?i)🔴[^\n|]*high[^\n|]*\|\s*(\d+)",
]
_MEDIUM_PATTERNS = [
    r"🟡[^\n|]*\|\s*(\d+)",
    r"🟡\s*中风险[^\n|]*\|\s*(\d+)",
    r"(?i)🟡[^\n|]*medium[^\n|]*\|\s*(\d+)",
]
_LOW_PATTERNS = [
    r"🟢[^\n|]*\|\s*(\d+)",
    r"🟢\s*低风险[^\n|]*\|\s*(\d+)",
    r"(?i)🟢[^\n|]*low[^\n|]*\|\s*(\d+)",
]

high_risk = extract_risk_count(report, _HIGH_PATTERNS)
medium_risk = extract_risk_count(report, _MEDIUM_PATTERNS)
low_risk = extract_risk_count(report, _LOW_PATTERNS)

_summary_patterns = [
    r"##\s*📋\s*审查总结\s*\n\s*(.+?)(?=\n##|\Z)",
    r"(?i)##\s*Review summary\s*\n\s*(.+?)(?=\n##|\Z)",
]
summary = L["default_summary"]
for pat in _summary_patterns:
    summary_match = re.search(pat, report, re.DOTALL)
    if summary_match:
        summary = summary_match.group(1).strip()
        break

risk_lines = []
if high_risk > 0:
    risk_lines.append(L["line_high"].format(high_risk))
if medium_risk > 0:
    risk_lines.append(L["line_medium"].format(medium_risk))
if low_risk > 0:
    risk_lines.append(L["line_low"].format(low_risk))

risk_text = " | ".join(risk_lines) if risk_lines else L["no_notable_risks"]

if high_risk > 0:
    template = "red"
    risk_badge = L["badge_high"].format(high_risk)
    header_title = L["title_high"].format(card_title)
elif medium_risk > 0:
    template = "orange"
    risk_badge = L["badge_medium"].format(medium_risk)
    header_title = L["title_medium"].format(card_title)
else:
    template = "green"
    risk_badge = L["badge_pass"]
    header_title = L["title_pass"].format(card_title)

card_content = {
    "config": {"wide_screen_mode": True},
    "header": {
        "title": {"tag": "plain_text", "content": header_title},
        "template": template,
    },
    "elements": [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{L['risk_level']}**: {risk_badge}",
            },
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{L['risk_overview']}**: {risk_text}",
            },
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{L['author']}**: {author_email}",
            },
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{L['summary']}**:\n{summary[:200]}...",
            },
        },
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": L["view_full"]},
                    "type": "primary",
                    "url": review_url,
                }
            ],
        },
    ],
}

if not feishu_open_id:
    print(
        "Skipping Feishu DM: could not resolve open_id (optional notification).",
        file=sys.stderr,
    )
    sys.exit(0)

url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {feishu_app_token}",
}

payload = {
    "receive_id": feishu_open_id,
    "msg_type": "interactive",
    "content": json.dumps(card_content, ensure_ascii=False),
    "uuid": str(uuid.uuid4()),
}

data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
req = urllib.request.Request(url, data=data, headers=headers)

try:
    response = urllib.request.urlopen(req)
    result = json.loads(response.read().decode())

    if result.get("code") == 0:
        print("Feishu message sent")
    else:
        print(f"Error: Feishu send failed: {result.get('msg')}", file=sys.stderr)
        sys.exit(1)
except urllib.error.URLError as e:
    print(f"Error: Feishu request failed: {e.reason}", file=sys.stderr)
    sys.exit(1)
