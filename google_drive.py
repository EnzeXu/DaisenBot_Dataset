# google_drive.py
"""
Utilities to authenticate with Google Drive API and download/upload files
using a human-friendly path like "My Drive/Dataset/file.csv".

Requires:
  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

Place your OAuth client credentials as 'credentials.json' in the working directory.
"""

import os
import io
from typing import Optional, List, Tuple
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# ---- Config ----
# Scopes:
# - 'drive' gives full access (use only if needed). For safer scope, use 'drive.file'.
SCOPES = [
    "https://www.googleapis.com/auth/drive"   # full Drive access
    # OR "https://www.googleapis.com/auth/drive.file"  # read/write files created/opened by the app
]

CREDENTIALS_FILE = ".credentials.json"   # download from Google Cloud Console
TOKEN_FILE = ".token.json"               # will be created on first consent

# ---- Auth helpers ----
def get_service(token_path: str = TOKEN_FILE,
                credentials_path: str = CREDENTIALS_FILE,
                scopes: List[str] = SCOPES):
    """
    Returns an authorized Google Drive v3 service object.
    Handles saving/loading token.json with refresh tokens.
    """
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    # If there are no valid creds, run the flow.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"{credentials_path} not found. Create OAuth client credentials in Google Cloud and save here."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return service, creds

# ---- Path resolution ----
def _find_child_id(service, parent_id: str, name: str, is_folder: Optional[bool]=None) -> Optional[str]:
    """
    Search for a child with given name under parent_id.
    If is_folder is True, restrict to folders; if False, restrict non-folders.
    Returns the first matching ID or None.
    WARNING: multiple matches may exist. Adjust logic if you need disambiguation.
    """
    # form query
    escaped_name = name.replace("'", "\\'")
    q_parts = [f"'{parent_id}' in parents", f"name = '{escaped_name}'", "trashed = false"]
    if is_folder is True:
        q_parts.append("mimeType = 'application/vnd.google-apps.folder'")
    elif is_folder is False:
        q_parts.append("mimeType != 'application/vnd.google-apps.folder'")
    q = " and ".join(q_parts)
    try:
        res = service.files().list(q=q, spaces='drive', fields="files(id, name, mimeType)", pageSize=10).execute()
        files = res.get("files", [])
        if not files:
            return None
        # return first — if ambiguous, caller may need extra logic
        return files[0]["id"]
    except HttpError as e:
        raise

def path_to_id(service, path: str) -> str:
    """
    Resolve a path like "My Drive/Folder1/Sub/file.txt" to a file ID.
    Google Drive's top-level 'My Drive' is represented by 'root'.
    - path can be absolute (starting with 'My Drive' or '/My Drive') or relative.
    - If path is just 'My Drive', returns 'root'.
    Raises FileNotFoundError if any segment is missing.
    """
    p = Path(path)
    parts = [seg for seg in p.parts if seg not in ("", "/")]
    if not parts:
        return "root"
    # Accept 'My Drive' or 'MyDrive' as root marker; map to 'root'
    if parts[0].lower() in ("my drive", "mydrive", "root"):
        parts = parts[1:]
        current_id = "root"
    else:
        # If user doesn't include 'My Drive', start from root.
        current_id = "root"
    # Walk segments
    for i, seg in enumerate(parts):
        # if this is last segment we don't know if it's folder or file; try folder first then file
        if i < len(parts) - 1:
            next_id = _find_child_id(service, current_id, seg, is_folder=True)
            if not next_id:
                raise FileNotFoundError(f"Folder '{seg}' not found under parent id {current_id}")
            current_id = next_id
        else:
            # last segment: prefer file, but check folder too
            fid = _find_child_id(service, current_id, seg, is_folder=False)
            if fid:
                return fid
            fid = _find_child_id(service, current_id, seg, is_folder=True)
            if fid:
                return fid
            raise FileNotFoundError(f"Item '{seg}' not found under parent id {current_id}")
    return current_id

# ---- Download / upload single file ----
def download_file(google_drive_relative_path: str, dst_path: str,
                  service=None, creds=None, token: Optional[str]=None):
    """
    Download a file from Drive path to dst_path.
    - google_drive_relative_path: e.g. "My Drive/Dataset/example.csv"
    - dst_path: local filesystem path to save to
    - service/creds: optional; if not provided, will start auth flow
    - token: kept for signature with your request for compatibility; not required if using service
    """
    if service is None:
        service, creds = get_service()

    file_id = path_to_id(service, google_drive_relative_path)

    # inspect mimeType to decide whether to use get_media or export_media
    meta = service.files().get(fileId=file_id, fields="mimeType").execute()
    mime = meta.get("mimeType", "")

    fh = io.FileIO(dst_path, mode='wb')
    try:
        if mime.startswith("application/vnd.google-apps."):
            # Google Docs/Sheets/Slides need export; choose a sensible export type
            if mime == "application/vnd.google-apps.document":
                export_mime = "text/plain"
            elif mime == "application/vnd.google-apps.spreadsheet":
                export_mime = "text/csv"
            elif mime == "application/vnd.google-apps.presentation":
                export_mime = "application/pdf"
            else:
                raise HttpError(
                    resp=None,
                    content=f"Cannot export Drive-native mimeType: {mime}".encode()
                )
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            downloader = MediaIoBaseDownload(fh, request)
        else:
            request = service.files().get_media(fileId=file_id)
            downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.close()
    except HttpError:
        fh.close()
        raise

def upload_file(src_path: str, google_drive_relative_path: str,
                service=None, creds=None, token: Optional[str]=None, overwrite: bool=False):
    """
    Upload a local file to a Drive folder specified by google_drive_relative_path.
    If google_drive_relative_path ends with '/', or resolves to a folder, the file name from src_path is used.
    If the final path points to an existing file and overwrite==True, the existing file will be updated.
    Returns the uploaded file's Drive ID.
    """
    if service is None:
        service, creds = get_service()

    # try to resolve path. If path resolves to a folder id -> upload into that folder
    try:
        target_id = path_to_id(service, google_drive_relative_path)
        # if target is folder: upload inside with same basename
        meta = service.files().get(fileId=target_id, fields="id, mimeType").execute()
        if meta["mimeType"] == "application/vnd.google-apps.folder":
            parent_id = target_id
            file_name = os.path.basename(src_path)
            existing_file_id = None
        else:
            # target is a file
            if overwrite:
                parent_id_res = service.files().get(fileId=target_id, fields="parents").execute()
                parent_list = parent_id_res.get("parents", [])
                parent_id = parent_list[0] if parent_list else "root"
                file_name = os.path.basename(google_drive_relative_path)
                existing_file_id = target_id
            else:
                raise FileExistsError(f"Target file exists at {google_drive_relative_path}. Use overwrite=True.")
    except FileNotFoundError:
        # path doesn't exist; assume last segment is folder name that should be created?
        # Simplest behaviour: treat path as folder path to create, then upload file inside last folder name
        parent_path = os.path.dirname(google_drive_relative_path)
        folder_name = os.path.basename(google_drive_relative_path)
        if parent_path == "":
            parent_id = "root"
        else:
            parent_id = path_to_id(service, parent_path)
        # create folder
        file_metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder", "parents":[parent_id]}
        created = service.files().create(body=file_metadata, fields="id").execute()
        parent_id = created["id"]
        file_name = os.path.basename(src_path)
        existing_file_id = None

    media = MediaFileUpload(src_path, resumable=True)
    if existing_file_id:
        updated = service.files().update(fileId=existing_file_id, media_body=media).execute()
        return updated["id"]
    else:
        file_metadata = {"name": file_name, "parents": [parent_id]}
        uploaded = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        return uploaded["id"]

# ---- Bulk helpers ----
def download_files(paths: List[Tuple[str, str]], service=None):
    """
    paths: list of tuples (drive_path, local_dst_path)
    Downloads each file; returns list of (drive_path, local_dst, success_bool, error_or_None)
    """
    if service is None:
        service, _ = get_service()
    results = []
    for drive_path, local_dst in paths:
        try:
            os.makedirs(os.path.dirname(local_dst) or ".", exist_ok=True)
            download_file(drive_path, local_dst, service=service)
            results.append((drive_path, local_dst, True, None))
        except Exception as e:
            results.append((drive_path, local_dst, False, e))
    return results

def upload_files(src_and_targets: List[Tuple[str, str]], service=None, overwrite=False):
    """
    src_and_targets: list of (local_src_path, drive_target_path)
    Returns list of (local_src, drive_target, success_bool, file_id_or_error)
    """
    if service is None:
        service, _ = get_service()
    results = []
    for src, drive_target in src_and_targets:
        try:
            file_id = upload_file(src, drive_target, service=service, overwrite=overwrite)
            results.append((src, drive_target, True, file_id))
        except Exception as e:
            results.append((src, drive_target, False, e))
    return results


