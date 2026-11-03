"""Kết nối Google Drive bằng Service Account (Task 1.1.2).

Yêu cầu:
- .env có GOOGLE_SERVICE_ACCOUNT_JSON (đường dẫn file key, tính từ thư mục gốc dự án)
- Folder trên Drive đã được share cho email của service account (quyền Viewer)
"""
import io
import os
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / '.env')

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
FOLDER_MIME = 'application/vnd.google-apps.folder'
GOOGLE_SHEET_MIME = 'application/vnd.google-apps.spreadsheet'
XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
NUM_RETRIES = 3  # số lần tự thử lại khi lỗi mạng / lỗi 5xx từ Google

_service = None


def get_drive_service():
    """Tạo Drive API v3 client từ service account key (tạo 1 lần, dùng lại)."""
    global _service
    if _service is None:
        key_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not key_path:
            raise RuntimeError('Thiếu GOOGLE_SERVICE_ACCOUNT_JSON trong .env')
        key_path = (PROJECT_ROOT / key_path).resolve()
        if not key_path.exists():
            raise FileNotFoundError(f'Không tìm thấy service account key: {key_path}')
        creds = service_account.Credentials.from_service_account_file(str(key_path), scopes=SCOPES)
        _service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    return _service


def list_files_in_folder(folder_id):
    """Liệt kê file trong folder (không gồm sub-folder và file trong thùng rác).

    Trả về list[{'id', 'name', 'mimeType', 'modifiedTime', 'size'}], sắp xếp theo tên.
    File Google Sheets gốc được thêm đuôi '.xlsx' vào 'name' vì khi tải sẽ export sang xlsx.
    """
    service = get_drive_service()
    files, page_token = [], None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false and mimeType != '{FOLDER_MIME}'",
            fields='nextPageToken, files(id, name, mimeType, modifiedTime, size)',
            orderBy='name',
            pageSize=1000,
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute(num_retries=NUM_RETRIES)
        files.extend(resp.get('files', []))
        page_token = resp.get('nextPageToken')
        if not page_token:
            break

    for f in files:
        if f['mimeType'] == GOOGLE_SHEET_MIME and not f['name'].lower().endswith('.xlsx'):
            f['name'] += '.xlsx'
    return files


def download_file_as_bytes(file_id, mime_type=None):
    """Tải nội dung file về RAM. mime_type = GOOGLE_SHEET_MIME -> export sang .xlsx."""
    service = get_drive_service()
    if mime_type == GOOGLE_SHEET_MIME:
        request = service.files().export_media(fileId=file_id, mimeType=XLSX_MIME)
    else:
        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk(num_retries=NUM_RETRIES)
    return buf.getvalue()
