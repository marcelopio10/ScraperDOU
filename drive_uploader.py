# drive_uploader.py
import os
import mimetypes
import io
import json
import base64
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", "servicescraperdou.json")

# Se o arquivo não existir, cria a partir da variável de ambiente
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    service_json_content = os.getenv("SERVICE_ACCOUNT_JSON")
    if service_json_content:
        try:
            json_data = json.loads(service_json_content)
        except json.JSONDecodeError:
            decoded = base64.b64decode(service_json_content).decode("utf-8")
            json_data = json.loads(decoded)
        if "private_key" in json_data:
            json_data["private_key"] = json_data["private_key"].replace("\\n", "\n")
        with open(SERVICE_ACCOUNT_FILE, "w") as f:
            json.dump(json_data, f)

def authenticate_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    return build('drive', 'v3', credentials=credentials, cache_discovery=False)

def upload_to_drive(file_path):
    service = authenticate_service()
    file_name = os.path.basename(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)

    drive_folder = os.getenv("DRIVE_FOLDER_ID") or os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    file_metadata = {
        'name': file_name,
        'parents': [drive_folder] if drive_folder else []
    }
    media = MediaFileUpload(file_path, mimetype=mime_type)

    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    service.permissions().create(
        fileId=uploaded_file.get('id'),
        body={'role': 'reader', 'type': 'anyone'}
    ).execute()

    file_id = uploaded_file.get('id')
    link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    return link

def download_file_from_drive(file_id, output_path):
    """Download a file from Google Drive.

    If the file is a native Google document (e.g. a spreadsheet), it will be
    exported to a suitable format before saving locally.
    """
    service = authenticate_service()

    meta = service.files().get(fileId=file_id, fields="mimeType,name").execute()
    mime_type = meta.get("mimeType", "")

    if mime_type == "application/vnd.google-apps.spreadsheet":
        request = service.files().export_media(
            fileId=file_id,
            mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    elif mime_type.startswith("application/vnd.google-apps"):
        request = service.files().export_media(fileId=file_id, mimeType="application/pdf")
    else:
        request = service.files().get_media(fileId=file_id)

    fh = io.FileIO(output_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()
        if status:
            print(f"Download {int(status.progress() * 100)}%.")

    return output_path

def list_files_in_drive():
    service = authenticate_service()
    results = service.files().list(
        pageSize=20,
        fields="files(id, name)"
    ).execute()
    return results.get('files', [])
