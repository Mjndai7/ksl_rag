import io
import logging
from pathlib import Path
from typing import Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.core.settings import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _quote(value: str) -> str:
    """Escape a value for a Drive API `q` string literal."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


class GoogleDriveClient:
    def __init__(self, credentials_path: str, download_dir: str = "data/raw"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        self.service = build("drive", "v3", credentials=credentials, cache_discovery=False)

    def _list(self, query: str, fields: str, page_size: int = 100) -> List[Dict]:
        files: List[Dict] = []
        page_token = None
        while True:
            response = (
                self.service.files()
                .list(
                    q=query,
                    pageSize=page_size,
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    fields=f"nextPageToken, files({fields})",
                )
                .execute()
            )
            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                return files

    def list_pdfs(self, folder_id: Optional[str] = None) -> List[Dict]:
        """List all PDFs (following pagination), optionally inside a Drive folder."""
        query = "mimeType='application/pdf' and trashed=false"
        if folder_id:
            query += f" and '{_quote(folder_id)}' in parents"
        return self._list(query, "id,name,mimeType,createdTime,modifiedTime,webViewLink,parents")

    def get_file_metadata(self, file_id: str) -> Dict:
        return self.service.files().get(fileId=file_id, supportsAllDrives=True, fields="*").execute()

    def download_file(self, file_id: str, filename: str) -> Path:
        """Download a file locally for parsing and return its path."""
        request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
        # Drive names are user-controlled; keep only the final path component.
        filepath = self.download_dir / Path(filename).name

        with io.FileIO(filepath, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug("Downloading %s: %d%%", filename, int(status.progress() * 100))
        return filepath

    def search_files(self, name_contains: str) -> List[Dict]:
        query = f"name contains '{_quote(name_contains)}' and trashed=false"
        return self._list(query, "id,name,webViewLink")


if __name__ == "__main__":
    client = GoogleDriveClient(credentials_path=settings.GOOGLE_CREDENTIALS_PATH)
    pdfs = client.list_pdfs(settings.GOOGLE_DRIVE_FOLDER_ID)
    print(f"Found {len(pdfs)} PDFs")
    for pdf in pdfs[:5]:
        print(pdf["name"], pdf["id"])
