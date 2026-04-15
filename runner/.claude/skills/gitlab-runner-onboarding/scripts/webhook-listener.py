#!/usr/bin/env python3
"""
GitLab webhook listener (minimal).
Handles @claude triggers in Commit and Merge Request comments only.
"""

from flask import Flask, request, jsonify
import requests
import os
import re
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment
GITLAB_URL = os.environ.get('GITLAB_URL', 'https://gitlab.com')
GITLAB_API_TOKEN = os.environ['GITLAB_API_TOKEN']
GITLAB_TRIGGER_TOKEN = os.environ['GITLAB_TRIGGER_TOKEN']
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', '')

@app.route('/health', methods=['GET'])
def health():
    """Liveness / readiness probe."""
    return jsonify({'status': 'ok'}), 200

@app.route('/gitlab-webhook', methods=['POST'])
def handle_webhook():
    """Handle incoming GitLab webhook payloads."""

    # Optional shared secret (X-Gitlab-Token)
    if WEBHOOK_SECRET:
        token = request.headers.get('X-Gitlab-Token', '')
        if token != WEBHOOK_SECRET:
            logger.warning("Invalid webhook token")
            return jsonify({'error': 'Unauthorized'}), 401

    data = request.json

    # Notes (comments) only
    if data.get('object_kind') != 'note':
        return jsonify({'status': 'ignored', 'reason': 'not a comment'}), 200

    comment = data['object_attributes']['note']

    # AI code review posts from CI include this marker; body may mention @claude and must not re-trigger.
    if '<!-- AI_CODE_REVIEW -->' in comment:
        return jsonify({'status': 'ignored', 'reason': 'ai code review comment'}), 200

    # Require @claude mention
    if '@claude' not in comment.lower():
        return jsonify({'status': 'ignored', 'reason': 'no @claude mention'}), 200

    # Strip @claude to get the instruction text
    instruction = re.sub(r'@claude\s*', '', comment, flags=re.IGNORECASE).strip()
    if not instruction:
        instruction = "Execute the appropriate action based on context."

    # Context for routing
    noteable_type = data['object_attributes']['noteable_type']
    project_id = data['project']['id']
    author = data.get('user', {}).get('username', 'unknown')
    author_email = (data.get('user') or {}).get('email') or None

    logger.info(f"@claude triggered by {author} on {noteable_type}")

    try:
        if noteable_type == 'Commit':
            # Comment on a commit
            commit_sha = data['commit']['id']
            context_url = data['object_attributes'].get('url', '')

            # Resolve a branch that contains this commit
            branch = get_commit_branch(project_id, commit_sha)
            if not branch:
                logger.warning(f"Cannot find branch for commit {commit_sha}")
                return jsonify({'status': 'error', 'reason': 'cannot determine branch'}), 200

            # Trigger pipeline
            result = trigger_pipeline(
                project_id=project_id,
                ref=branch,
                instruction=instruction,
                context_url=context_url,
                commit_sha=commit_sha,
                author_email=author_email,
            )

            return jsonify({
                'status': 'triggered',
                'branch': branch,
                'commit': commit_sha[:8],
                'pipeline_id': result.get('id')
            }), 200

        elif noteable_type == 'MergeRequest':
            # Comment on an MR
            mr = data['merge_request']
            branch = mr['source_branch']
            context_url = mr.get('url', '')
            commit_sha = mr['last_commit']['id']

            # Trigger pipeline
            result = trigger_pipeline(
                project_id=project_id,
                ref=branch,
                instruction=instruction,
                context_url=context_url,
                commit_sha=commit_sha,
                mr_iid=mr['iid'],
                author_email=author_email,
            )

            return jsonify({
                'status': 'triggered',
                'branch': branch,
                'mr': f"!{mr['iid']}",
                'pipeline_id': result.get('id')
            }), 200

        else:
            logger.warning(f"Unsupported noteable type: {noteable_type}")
            return jsonify({
                'status': 'ignored',
                'reason': f'unsupported type: {noteable_type}'
            }), 200

    except Exception as e:
        logger.error(f"Error handling webhook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def get_commit_branch(project_id, commit_sha):
    """Resolve a branch containing the commit; prefer feature/* branches."""
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/commits/{commit_sha}/refs"
    headers = {'PRIVATE-TOKEN': GITLAB_API_TOKEN}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        refs = resp.json()

        # Prefer feature/* branches
        for ref in refs:
            if ref['type'] == 'branch' and ref['name'].startswith('feature/'):
                return ref['name']

        # Otherwise first branch ref
        for ref in refs:
            if ref['type'] == 'branch':
                return ref['name']

        return None

    except Exception as e:
        logger.error(f"Error getting commit branch: {e}")
        return None

def trigger_pipeline(
    project_id,
    ref,
    instruction,
    context_url,
    commit_sha=None,
    mr_iid=None,
    author_email=None,
):
    """POST to trigger a pipeline via the trigger token API."""
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/trigger/pipeline"

    variables = {
        'AI_FLOW_INPUT': instruction,
        'AI_FLOW_CONTEXT': context_url,
        'AI_FLOW_EVENT': 'comment',
        'AI_FLOW_BRANCH': ref,
    }

    if commit_sha:
        variables['AI_FLOW_COMMIT_SHA'] = commit_sha
    if mr_iid is not None:
        variables['AI_FLOW_MR_IID'] = str(mr_iid)
    if author_email:
        variables['AI_FLOW_AUTHOR_EMAIL'] = author_email

    payload = {
        'token': GITLAB_TRIGGER_TOKEN,
        'ref': ref,
        'variables': variables
    }

    logger.info(f"Triggering pipeline on {ref} with instruction: {instruction[:50]}...")

    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"Pipeline triggered: {result.get('web_url')}")
        return result

    except requests.exceptions.HTTPError as e:
        logger.error(f"Failed to trigger pipeline: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error triggering pipeline: {e}")
        raise

if __name__ == '__main__':
    # Dev-only entrypoint
    app.run(host='0.0.0.0', port=5000, debug=True)
