import base64
import logging
import os
import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO") or os.getenv("TARGET_REPO")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH") or os.getenv("TARGET_BRANCH") or "main"


def upload_file_to_github(file_path, repo_path=None, message="Add highlighted PDF"):
    """Envia um arquivo para um repositório do GitHub via API REST."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        logging.error("Variáveis GITHUB_TOKEN ou GITHUB_REPO não configuradas")
        return None

    repo_path = repo_path or os.path.basename(file_path)
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}"

    with open(file_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    params = {"ref": GITHUB_BRANCH}
    resp = requests.get(url, headers=headers, params=params)
    sha = resp.json().get("sha") if resp.status_code == 200 else None

    payload = {
        "message": message,
        "branch": GITHUB_BRANCH,
        "content": content,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=headers, json=payload)
    if resp.status_code not in (200, 201):
        logging.error("Erro ao enviar para o GitHub: %s", resp.text)
        return None

    html_url = resp.json().get("content", {}).get("html_url")
    logging.info("Arquivo enviado para o GitHub em %s", html_url)
    return html_url
