import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core.settings import settings
from app.db import repository
from app.ingestion.sync_service import IngestionSyncService

router = APIRouter()

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class IngestRequest(BaseModel):
    folder_id: Optional[str] = Field(None, description="Drive folder id; defaults to GOOGLE_DRIVE_FOLDER_ID")
    extract_graph: Optional[bool] = Field(None, description="Override GRAPH_EXTRACTION_ENABLED for this job")
    force: bool = Field(False, description="Re-ingest even if the document is already up to date")
    limit: Optional[int] = Field(None, ge=1, description="Only ingest the first N PDFs")


def _job_response(job: dict) -> dict:
    return {"job_id": job["id"], "status": job["status"], "status_url": f"/api/v1/ingest/jobs/{job['id']}"}


@router.post("/ingest", status_code=202)
def ingest_drive_folder(request: IngestRequest, background_tasks: BackgroundTasks):
    folder_id = request.folder_id or settings.GOOGLE_DRIVE_FOLDER_ID
    if not folder_id:
        raise HTTPException(status_code=400, detail="folder_id is required (no GOOGLE_DRIVE_FOLDER_ID configured)")
    if not settings.GOOGLE_CREDENTIALS_PATH or not Path(settings.GOOGLE_CREDENTIALS_PATH).exists():
        raise HTTPException(status_code=503, detail="Google Drive credentials are not configured")

    job = repository.create_job(source="drive", target=folder_id)
    background_tasks.add_task(
        IngestionSyncService().run_job,
        job["id"],
        extract_graph=request.extract_graph,
        force=request.force,
        limit=request.limit,
    )
    return _job_response(job)


@router.post("/ingest/upload", status_code=202)
async def ingest_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    extract_graph: Optional[bool] = Form(None),
    force: bool = Form(False),
):
    filename = Path(file.filename or "upload.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File is not a valid PDF")

    upload_dir = Path(settings.DOWNLOAD_DIR) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / f"{uuid.uuid4().hex}_{filename}"
    path.write_bytes(data)

    job = repository.create_job(source="upload", target=filename)
    background_tasks.add_task(
        IngestionSyncService().run_job,
        job["id"],
        pdf_path=str(path),
        extract_graph=extract_graph,
        force=force,
    )
    return _job_response(job)


@router.get("/ingest/jobs/{job_id}")
def get_ingest_job(job_id: str):
    job = repository.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
