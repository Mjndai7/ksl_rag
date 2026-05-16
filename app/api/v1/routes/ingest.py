from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.ingestion.sync_service import IngestionSyncService
from app.core.settings import settings

router = APIRouter()

class IngestRequest(BaseModel):
    folder_id: str

@router.post("/ingest")
def ingest_drive_folder(request: IngestRequest):
    try:
        service = IngestionSyncService(
            credentials_path=settings.GOOGLE_CREDENTIALS_PATH
        )
        service.sync_drive_folder(folder_id=request.folder_id)
        return {
            "status": "success",
            "message": f"Started ingestion for folder {request.folder_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
