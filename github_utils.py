import base64
import logging
import os
import shutil
import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO") or os.getenv("TARGET_REPO")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH") or os.getenv("TARGET_BRANCH") or "main"
LOCAL_OUTPUT_DIR = os.getenv("LOCAL_OUTPUT_DIR", "output_files")


def save_file_locally(file_path, dest_dir=LOCAL_OUTPUT_DIR):
    """Salva uma cópia do arquivo no diretório especificado."""
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, os.path.basename(file_path))
    shutil.copy(file_path, dest_path)
    logging.info("Arquivo salvo localmente em %s", dest_path)
    return dest_path


def upload_file_to_github(file_path, repo_path=None, message="Add highlighted PDF"):
    """Envia um arquivo para um repositório do GitHub via API REST."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        logging.error("Variáveis GITHUB_TOKEN ou GITHUB_REPO não configuradas")
        return save_file_locally(file_path)

    repo_path = repo_path or os.path.basename(file_path)
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}"
    logging.debug("Enviando %s para %s em %s", file_path, GITHUB_REPO, GITHUB_BRANCH)

    with open(file_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    params = {"ref": GITHUB_BRANCH}
    resp = requests.get(url, headers=headers, params=params)
    logging.debug("GET %s -> %s", url, resp.status_code)
    sha = resp.json().get("sha") if resp.status_code == 200 else None

    payload = {
        "message": message,
        "branch": GITHUB_BRANCH,
        "content": content,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=headers, json=payload)
    logging.debug("PUT %s -> %s", url, resp.status_code)
    if resp.status_code not in (200, 201):
        logging.error("Erro ao enviar para o GitHub: %s", resp.text)
        return save_file_locally(file_path)

    html_url = resp.json().get("content", {}).get("html_url")
    logging.info("Arquivo enviado para o GitHub em %s", html_url)
    return html_url
