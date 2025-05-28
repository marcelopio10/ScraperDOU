# drive_uploader.py
import os
import mimetypes
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'servicescraperdou.json'

def authenticate_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    return build('drive', 'v3', credentials=credentials)

def upload_to_drive(file_path):
    service = authenticate_service()
    file_name = os.path.basename(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)

    file_metadata = {
        'name': file_name,
        # Se quiser salvar numa pasta compartilhada:
        'parents': ['1tlVQIWHdTt1hMkTo5ory31tRGKpNYSYi']
    }
    media = MediaFileUpload(file_path, mimetype=mime_type)

    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    # Torna o arquivo compartilhável por link
    service.permissions().create(
        fileId=uploaded_file.get('id'),
        body={'role': 'reader', 'type': 'anyone'}
    ).execute()

    file_id = uploaded_file.get('id')
    link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    return link

def download_file_from_drive(file_id, output_path):
    service = authenticate_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(output_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}%.")

    return output_path

def list_files_in_drive():
    service = authenticate_service()
    results = service.files().list(
        pageSize=20,
        fields="files(id, name)"
    ).execute()
    return results.get('files', [])
