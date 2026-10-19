import logging
from pathlib import Path
from typing import Optional

from app.core.settings import settings
from app.db import repository
from app.workflows.langgraph_flow import run_ingestion

logger = logging.getLogger(__name__)


class IngestionSyncService:
    """Runs ingestion jobs (Drive folder or uploaded file) through the LangGraph workflow."""

    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or settings.GOOGLE_CREDENTIALS_PATH
        self._drive = None

    @property
    def drive(self):
        if self._drive is None:
            from app.ingestion.drive_client import GoogleDriveClient

            if not self.credentials_path or not Path(self.credentials_path).exists():
                raise RuntimeError(
                    f"Google credentials not found at {self.credentials_path!r}; set GOOGLE_CREDENTIALS_PATH"
                )
            self._drive = GoogleDriveClient(credentials_path=self.credentials_path, download_dir=settings.DOWNLOAD_DIR)
        return self._drive

    def sync_drive_folder(
        self,
        folder_id: Optional[str] = None,
        job_id: Optional[str] = None,
        extract_graph: Optional[bool] = None,
        force: bool = False,
        limit: Optional[int] = None,
    ) -> list[dict]:
        folder_id = folder_id or settings.GOOGLE_DRIVE_FOLDER_ID
        files = self.drive.list_pdfs(folder_id=folder_id)
        if limit:
            files = files[:limit]
        logger.info("Found %d PDFs in folder %s", len(files), folder_id)
        if job_id:
            repository.update_job(job_id, total_files=len(files))

        results = []
        for file_meta in files:
            try:
                pdf_path = self.drive.download_file(file_id=file_meta["id"], filename=file_meta["name"])
                result = run_ingestion(
                    pdf_path,
                    title=file_meta["name"],
                    source="google_drive",
                    source_id=file_meta["id"],
                    source_link=file_meta.get("webViewLink"),
                    extract_graph=extract_graph,
                    force=force,
                )
            except Exception as e:
                logger.exception("Failed to ingest %s", file_meta.get("name"))
                result = {"title": file_meta.get("name"), "status": "failed", "error": str(e)}
            results.append(result)
            if job_id:
                repository.append_job_result(job_id, result)
        return results

    def run_job(self, job_id: str, **kwargs) -> None:
        """Background entry point: runs a Drive or upload job and records its outcome."""
        job = repository.get_job(job_id)
        repository.update_job(job_id, status="running")
        try:
            if job["source"] == "drive":
                results = self.sync_drive_folder(folder_id=job["target"], job_id=job_id, **kwargs)
            else:
                repository.update_job(job_id, total_files=1)
                upload_path = kwargs.pop("pdf_path")
                result = run_ingestion(upload_path, title=job["target"], source="upload", **kwargs)
                repository.append_job_result(job_id, result)
                results = [result]
            failed = [r for r in results if r.get("status") == "failed"]
            repository.update_job(
                job_id,
                status="failed" if failed and len(failed) == len(results) else "completed",
                error=f"{len(failed)} of {len(results)} files failed" if failed else None,
            )
        except Exception as e:
            logger.exception("Ingestion job %s failed", job_id)
            repository.update_job(job_id, status="failed", error=str(e))


if __name__ == "__main__":
    import json
    import logging as _logging

    _logging.basicConfig(level=_logging.INFO)
    print(json.dumps(IngestionSyncService().sync_drive_folder(), indent=2, default=str))
