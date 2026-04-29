from pathlib import Path
from typing import List, Dict, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

import io


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class GoogleDriveClient:
    def __init__(
        self,
        credentials_path: str,
        download_dir: str = "data/raw",
    ):
        self.credentials_path = credentials_path
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=SCOPES,
        )

        self.service = build(
            "drive",
            "v3",
            credentials=self.credentials,
            cache_discovery=False,
        )

# Internal helper to get the base files() call with shared drive support, to avoid repeating parameters everywhere.

    def _base_files_call(self):
        """
        Shared drives support enabled.
        """
        return self.service.files()

# list files with optional folder filter, return metadata including name, link, etc.

    def list_pdfs(
        self,
        folder_id: Optional[str] = None,
        page_size: int = 100,
    ) -> List[Dict]:
        """
        List PDFs optionally inside a Drive folder.
        """

        query = "mimeType='application/pdf' and trashed=false"

        if folder_id:
            query += f" and '{folder_id}' in parents"

        response = (
            self._base_files_call()
            .list(
                q=query,
                pageSize=page_size,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="""
                    files(
                        id,
                        name,
                        mimeType,
                        createdTime,
                        modifiedTime,
                        owners,
                        webViewLink,
                        parents
                    )
                """,
            )
            .execute()
        )

        return response.get("files", [])
        
# get file metadata by ID, including name, link, etc.

    def get_file_metadata(
        self,
        file_id: str
    ) -> Dict:
        return (
            self._base_files_call()
            .get(
                fileId=file_id,
                supportsAllDrives=True,
                fields="*",
            )
            .execute()
        )
        
# download file by ID, save to local disk, return path

    def download_file(
        self,
        file_id: str,
        filename: str,
    ) -> Path:
        """
        Downloads PDF locally for parsing.
        """

        request = self._base_files_call().get_media(
            fileId=file_id,
            supportsAllDrives=True,
        )

        filepath = self.download_dir / filename

        fh = io.FileIO(filepath, "wb")
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(
                    f"Downloading {filename}: "
                    f"{int(status.progress() * 100)}%"
                )

        return filepath
# bunch of helper functions to pull files, search, etc.

    def sync_folder(
        self,
        folder_id: Optional[str] = None
    ) -> List[Path]:
        """
        Pull all PDFs in a folder.
        """

        files = self.list_pdfs(folder_id=folder_id)

        downloaded = []

        for file in files:
            path = self.download_file(
                file_id=file["id"],
                filename=file["name"],
            )
            downloaded.append(path)

        return downloaded

# simple search by name, not recursive

    def search_files(
        self,
        name_contains: str
    ) -> List[Dict]:

        query = (
            f"name contains '{name_contains}' "
            "and trashed=false"
        )

        response = (
            self._base_files_call()
            .list(
                q=query,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="files(id,name,webViewLink)"
            )
            .execute()
        )

        return response.get("files", [])

# local testing

if __name__ == "__main__":

    client = GoogleDriveClient(
        credentials_path="credentials/google_service_account.json"
    )

    pdfs = client.list_pdfs()

    print(f"Found {len(pdfs)} PDFs")

    for pdf in pdfs[:5]:
        print(pdf["name"], pdf["id"])
