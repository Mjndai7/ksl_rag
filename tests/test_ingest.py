from app.ingestion.sync_service import IngestionSyncService

service = IngestionSyncService(
   credentials_path="credentials/google_service_account.json"
)


service.sync_drive_folder(folder_id="1XYcInS9yHldcszPaQrusRyNbsEbp7nOm")
