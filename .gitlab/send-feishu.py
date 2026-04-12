#!/usr/bin/env python3
"""Optional Feishu (Lark) DM for review reports. Requires FEISHU_APP_TOKEN."""
import json
import urllib.request
import urllib.error
import sys
import os
import re
import uuid

if len(sys.argv) < 5:
    print("Usage: send-feishu.py <report_file> <title> <review_url> <author_email>")
    sys.exit(1)

report_file = sys.argv[1]
title = sys.argv[2]
review_url = sys.argv[3]
author_email = sys.argv[4]

feishu_app_token = os.environ.get('FEISHU_APP_TOKEN')
if not feishu_app_token:
    print("Error: FEISHU_APP_TOKEN environment variable is not set")
    sys.exit(1)


def get_open_id_by_email(email, app_token):
    """Resolve Feishu open_id by email."""
    url = 'https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id?user_id_type=open_id'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {app_token}'
    }
    payload = {
        'emails': [email],
        'include_resigned': True
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)

    try:
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode())

        if result.get('code') == 0:
            user_list = result.get('data', {}).get('user_list', [])
            if user_list and len(user_list) > 0:
                open_id = user_list[0].get('user_id')
                print(f"✓ Resolved open_id for {email}")
                return open_id
            print(f"⚠ No Feishu user for email {email}")
            return None
        print(f"⚠ open_id API error: {result.get('msg')}")
        return None
    except urllib.error.URLError as e:
        print(f"⚠ Feishu API request failed: {e.reason}")
        return None


def count_risk_row(report, level_name):
    """Parse | Level | Count | table (English report from code-review-report SKILL)."""
    pat = rf'\|\s*{level_name}\s*\|\s*(\d+)\s*\|'
    m = re.search(pat, report, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0


feishu_open_id = get_open_id_by_email(author_email, feishu_app_token)

with open(report_file) as f:
    report = f.read()

low_risk = count_risk_row(report, 'Low')
medium_risk = count_risk_row(report, 'Medium')
high_risk = count_risk_row(report, 'High')

summary_match = re.search(r'## Summary\s*\n\s*(.+?)(?=\n##|\Z)', report, re.DOTALL | re.IGNORECASE)
summary = summary_match.group(1).strip() if summary_match else "Review completed."

risk_parts = []
if high_risk > 0:
    risk_parts.append(f"High × {high_risk}")
if medium_risk > 0:
    risk_parts.append(f"Medium × {medium_risk}")
if low_risk > 0:
    risk_parts.append(f"Low × {low_risk}")

risk_text = " | ".join(risk_parts) if risk_parts else "No major risks flagged"

if high_risk > 0:
    template = 'red'
    risk_badge = f'High risk ({high_risk})'
    title = f"⚠️ {title}"
elif medium_risk > 0:
    template = 'orange'
    risk_badge = f'Medium risk ({medium_risk})'
    title = f"⚡ {title}"
else:
    template = 'green'
    risk_badge = 'Passed'
    title = f"✅ {title}"

card_content = {
    'config': {'wide_screen_mode': True},
    'header': {
        'title': {'tag': 'plain_text', 'content': title},
        'template': template
    },
    'elements': [
        {
            'tag': 'div',
            'text': {'tag': 'lark_md', 'content': f'**Risk**: {risk_badge}'}
        },
        {
            'tag': 'div',
            'text': {'tag': 'lark_md', 'content': f'**Overview**: {risk_text}'}
        },
        {
            'tag': 'div',
            'text': {'tag': 'lark_md', 'content': f'**Author**: {author_email}'}
        },
        {
            'tag': 'div',
            'text': {'tag': 'lark_md', 'content': f'**Summary**:\n{summary[:200]}...'}
        },
        {
            'tag': 'action',
            'actions': [
                {
                    'tag': 'button',
                    'text': {'tag': 'plain_text', 'content': 'View full report'},
                    'type': 'primary',
                    'url': review_url
                }
            ]
        }
    ]
}

if not feishu_open_id:
    print(f"⚠ Skipping Feishu: no open_id for {author_email}")
    sys.exit(0)

url = 'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id'
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {feishu_app_token}'
}

payload = {
    'receive_id': feishu_open_id,
    'msg_type': 'interactive',
    'content': json.dumps(card_content, ensure_ascii=False),
    'uuid': str(uuid.uuid4())
}

data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers)

try:
    response = urllib.request.urlopen(req)
    result = json.loads(response.read().decode())

    if result.get('code') == 0:
        print("✓ Feishu message sent")
    else:
        print(f"✗ Feishu error: {result.get('msg')}")
        sys.exit(1)
except urllib.error.URLError as e:
    print(f"✗ Feishu send failed: {e.reason}")
    sys.exit(1)
