#!/usr/bin/env python3
"""Feishu interactive card for GitLab CI. Needs FEISHU_APP_ID, FEISHU_APP_SECRET, CI_PROJECT_ID.
Optional: CODE_REVIEW_REPORT_LANGUAGE (zh|en), FEISHU_CARD_MODE=reply, FEISHU_CARD_TEMPLATE (header color).
https://open.feishu.cn/document/"""
import json
import urllib.request
import urllib.error
import sys
import os
import re
import uuid
import time
from pathlib import Path

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

_SUMMARY_MAX = 1800


def get_token_cache_path():
    home = Path.home()
    project_id = os.environ.get("CI_PROJECT_ID", "default")
    cache_dir = home / ".feishu-token.d" / project_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "token"


def get_tenant_access_token():
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")

    if not app_id or not app_secret:
        print("Error: FEISHU_APP_ID or FEISHU_APP_SECRET is not set", file=sys.stderr)
        sys.exit(1)

    cache_path = get_token_cache_path()
    now = int(time.time())

    if cache_path.exists():
        try:
            with open(cache_path, "r") as f:
                cache = json.load(f)
            token = cache.get("token")
            expire_at = cache.get("expire_at", 0)

            if token and expire_at > now + 1800:
                return token
        except Exception as e:
            print(f"Warning: failed to read token cache: {e}", file=sys.stderr)

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("code") != 0:
            print(f"Error: Feishu auth failed: {data}", file=sys.stderr)
            sys.exit(1)

        token = data["tenant_access_token"]
        expire = data.get("expire", 7200)
        expire_at = now + expire

        with open(cache_path, "w") as f:
            json.dump({"token": token, "expire_at": expire_at}, f)

        return token

    except Exception as e:
        print(f"Error: failed to get tenant_access_token: {e}", file=sys.stderr)
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
        "line_high": "🔴 高风险 × {}",
        "line_medium": "🟡 中风险 × {}",
        "line_low": "🟢 低风险 × {}",
        "no_notable_risks": "未发现明显风险",
        "title_high": "[高风险] {}",
        "title_medium": "[中风险] {}",
        "title_pass": "[已通过] {}",
        "risk_overview": "风险概况",
        "author": "提交人",
        "view_full": "查看完整报告",
        "view_gitlab": "打开 GitLab",
    },
    "en": {
        "default_summary": "Review completed.",
        "line_high": "🔴 High × {}",
        "line_medium": "🟡 Medium × {}",
        "line_low": "🟢 Low × {}",
        "no_notable_risks": "No notable risks",
        "title_high": "[High risk] {}",
        "title_medium": "[Medium risk] {}",
        "title_pass": "[Passed] {}",
        "risk_overview": "Risk overview",
        "author": "Author",
        "view_full": "View full report",
        "view_gitlab": "Open in GitLab",
    },
}


def _reply_notify_mode() -> bool:
    return (os.environ.get("FEISHU_CARD_MODE") or "").strip().lower() == "reply"


def _reply_header_template() -> str:
    raw = (os.environ.get("FEISHU_CARD_TEMPLATE") or "blue").strip().lower()
    allowed = {
        "blue",
        "wathet",
        "turquoise",
        "green",
        "yellow",
        "orange",
        "red",
        "violet",
        "grey",
    }
    return raw if raw in allowed else "blue"


def get_open_id_by_email(email: str, app_token: str):
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
        response = urllib.request.urlopen(req, timeout=10)
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


def _is_table_separator_row(line: str) -> bool:
    cells = _split_table_row(line)
    if not cells:
        return False
    return all(re.match(r"^[\s\-:]+$", c) for c in cells)


def _split_table_row(line: str) -> list:
    parts = line.strip().split("|")
    return [p.strip() for p in parts if p.strip()]


def convert_markdown_tables_to_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    out: list = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("|") and "|" in stripped[1:]:
            block: list = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            out.append(_format_table_block(block))
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def _format_table_block(block: list) -> str:
    rows = []
    for raw in block:
        cells = _split_table_row(raw)
        if not cells:
            continue
        if _is_table_separator_row(raw):
            continue
        rows.append(cells)
    if len(rows) < 1:
        return "\n".join(block)

    header = rows[0]
    data_rows = rows[1:] if len(rows) > 1 else []

    if len(header) >= 2 and data_rows:
        lines_out = []
        for data in data_rows:
            if len(data) >= 2:
                left, right = data[0], data[1]
                lines_out.append(f"• {left}：**{right}**")
            elif len(data) == 1:
                lines_out.append(f"• {data[0]}")
        if lines_out:
            return "\n".join(lines_out)

    lines_out = []
    for r in rows:
        lines_out.append(" · ".join(r) if len(r) > 1 else (r[0] if r else ""))
    return "\n".join(lines_out)


_FENCED_BLOCK_RE = re.compile(r"```[a-zA-Z0-9_-]*\r?\n[\s\S]*?```", re.MULTILINE)


def _protect_fenced_blocks(text: str) -> tuple[str, dict[str, str]]:
    store: dict[str, str] = {}
    n = [0]

    def repl(m) -> str:
        key = f"__FEISHU_FENCE_{n[0]}__"
        store[key] = m.group(0)
        n[0] += 1
        return key

    return _FENCED_BLOCK_RE.sub(repl, text), store


def _restore_fenced_blocks(text: str, store: dict[str, str]) -> str:
    for key, val in store.items():
        text = text.replace(key, val)
    return text


def normalize_headings_for_lark_md(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    out: list = []
    for line in lines:
        stripped = line.strip()
        m = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if m:
            title = m.group(2).strip()
            level = len(m.group(1))
            indent = "　" * max(0, level - 3) if level > 3 else ""
            out.append(f"{indent}**{title}**")
        else:
            out.append(line)
    return "\n".join(out)


def normalize_summary_for_feishu(text: str) -> str:
    t = convert_markdown_tables_to_text(text)
    t, fence_store = _protect_fenced_blocks(t)
    t = normalize_headings_for_lark_md(t)
    t = _restore_fenced_blocks(t, fence_store)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def extract_first_h2_section(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    start_i = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("##") and not s.startswith("###"):
            start_i = i
            break
    if start_i is None:
        return ""
    out: list = []
    for j in range(start_i, len(lines)):
        line = lines[j]
        if j > start_i:
            s = line.strip()
            if s.startswith("##") and not s.startswith("###"):
                break
        out.append(line)
    return "\n".join(out).strip()


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


def truncate_for_card(text: str) -> str:
    if len(text) <= _SUMMARY_MAX:
        return text
    return text[: _SUMMARY_MAX - 3] + "..."


feishu_app_token = get_tenant_access_token()
lang = resolve_ui_lang()
L = UI[lang]

with open(report_file, encoding="utf-8") as f:
    report = f.read()

feishu_open_id = get_open_id_by_email(author_email, feishu_app_token)
if not feishu_open_id:
    print(
        "Skipping Feishu DM: Contact API returned no open_id for this email. "
        "The user must exist in the same Feishu tenant as the app, or use an on-premises directory match.",
        file=sys.stderr,
    )
    sys.exit(0)

if _reply_notify_mode():
    summary_text = truncate_for_card(normalize_summary_for_feishu(report.strip()))
    template = _reply_header_template()
    header_title = (card_title or "Claude")[:200]
    card_content = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": header_title},
            "template": template,
        },
        "elements": [
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": summary_text,
                },
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{L['author']}**\n{author_email}",
                },
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": L["view_gitlab"]},
                        "type": "primary",
                        "url": review_url,
                    }
                ],
            },
        ],
    }
else:
    high_risk = extract_risk_count(report, _HIGH_PATTERNS)
    medium_risk = extract_risk_count(report, _MEDIUM_PATTERNS)
    low_risk = extract_risk_count(report, _LOW_PATTERNS)

    risk_lines = []
    if high_risk > 0:
        risk_lines.append(L["line_high"].format(high_risk))
    if medium_risk > 0:
        risk_lines.append(L["line_medium"].format(medium_risk))
    if low_risk > 0:
        risk_lines.append(L["line_low"].format(low_risk))
    risk_text = "\n".join(risk_lines) if risk_lines else L["no_notable_risks"]

    first_section = extract_first_h2_section(report)
    if not first_section.strip():
        raw = report.strip()
        first_section = raw[:2000] if raw else L["default_summary"]
    summary_text = truncate_for_card(normalize_summary_for_feishu(first_section))

    if high_risk > 0:
        template = "red"
        header_title = L["title_high"].format(card_title)
    elif medium_risk > 0:
        template = "orange"
        header_title = L["title_medium"].format(card_title)
    else:
        template = "green"
        header_title = L["title_pass"].format(card_title)

    card_content = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": header_title},
            "template": template,
        },
        "elements": [
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{L['risk_overview']}**\n{risk_text}",
                },
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{L['author']}**\n{author_email}",
                },
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": summary_text,
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
    response = urllib.request.urlopen(req, timeout=15)
    result = json.loads(response.read().decode())

    if result.get("code") == 0:
        print("Feishu message sent")
    else:
        print(f"Error: Feishu send failed: {result.get('msg')}", file=sys.stderr)
        sys.exit(1)
except urllib.error.URLError as e:
    print(f"Error: Feishu request failed: {e.reason}", file=sys.stderr)
    sys.exit(1)
