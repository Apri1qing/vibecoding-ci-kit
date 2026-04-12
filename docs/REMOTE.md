# Publishing to a remote

This repository is initialized locally without a remote. Add one after you create an **empty** project on GitLab, GitHub, or another host.

```bash
cd /path/to/gitlab-ai-ci-pipeline
git remote add origin <YOUR_SSH_OR_HTTPS_URL>
git branch -M main
git push -u origin main
```

Replace `<YOUR_SSH_OR_HTTPS_URL>` with the clone URL from your hosting provider.

If the remote already has commits (e.g. README-only), use `git pull origin main --rebase` before the first push, or follow your host’s import instructions.
