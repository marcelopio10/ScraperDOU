import os
import io
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account

SCOPES = ["https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = "service_account.json"

# Autenticação
def authenticate_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build("drive", "v3", credentials=credentials)

service = authenticate_service()
DRIVE_FOLDER_ID = os.getenv("FOLDER_ID")  # Suporta Meu Drive ou Shared Drive

def upload_to_drive(file_path, mime_type="application/pdf"):
    file_metadata = {
        "name": os.path.basename(file_path),
        "parents": [DRIVE_FOLDER_ID] if DRIVE_FOLDER_ID else None
    }
    media = MediaFileUpload(file_path, mimetype=mime_type)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id",
        supportsAllDrives=True
    ).execute()

    logging.info(f"Upload concluído. File ID: {file.get('id')}")
    return file.get("id")


def download_file_from_drive(file_id, dest_path):
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    with io.FileIO(dest_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                logging.info(f"Download {int(status.progress() * 100)}%.")


def list_files_in_drive():
    query = f"'{DRIVE_FOLDER_ID}' in parents" if DRIVE_FOLDER_ID else None
    results = service.files().list(
        q=query,
        pageSize=20,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    files = results.get("files", [])
    for file in files:
        logging.info(f"{file['name']} ({file['id']})")
    return files