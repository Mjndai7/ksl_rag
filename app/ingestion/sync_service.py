from pathlib import Path
import hashlib
import time
import logging
from app.core.settings import settings
from app.ingestion.drive_client import GoogleDriveClient
from app.parser.pdf_parser import parse_pdf
from app.db.postgres import SessionLocal
from app.db.models import Document
from app.vectorstore.indexing import upsert_chunks
from app.chunking.splitter import chunk_text
from app.embeddings.embedder import embed_chunks
from app.graph.graph_builder import graph_builder

logger = logging.getLogger(__name__)

class IngestionSyncService:
    def __init__(self, credentials_path: str):
        self.drive = GoogleDriveClient(credentials_path=credentials_path)
    
    # utility to hash content for deduplication
    def file_hash(self, text: str):
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    
    def document_exists(self, checksum: str):
        db = SessionLocal()

        try:
            doc = (
                db.query(Document)
                .filter(Document.checksum == checksum)
                .first()
            )
            return doc is not None
        finally:
            db.close()

    
    def store_document_metadata(self, title: str, source: str, content: str, checksum: str):
        db = SessionLocal()

        try:
            doc = Document(
                title=title,
                source=source,
                content=content,
                checksum=checksum,
            )
            db.add(doc)
            db.commit()
            return doc
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    

    # single file ingestion flow: download, parse, deduplicate, store metadata, chunk, embed, index
    def process_pdf(self, pdf_path: Path, metadata: dict):
        
        logger.info(f"Processing {pdf_path.name}")

        # parse pdf
        start_time = time.time()
        text = parse_pdf(str(pdf_path))
        logger.info(f"[TIMING] PDF parsing: {time.time() - start_time:.2f}s")

        if not text.strip():
            logger.info("Empty file skipped")
            return
        # deduplication check
        checksum = self.file_hash(text)
        if self.document_exists(checksum):
            logger.info(f"{pdf_path.name} already exists, skipping")
            return


        # Chunk, embed, index
        start_time = time.time()
        chunks = chunk_text(text)
        logger.info(f"[TIMING] Chunking: {time.time() - start_time:.2f}s ({len(chunks)} chunks)")

        if not chunks:
            return

        start_time = time.time()
        vectors = embed_chunks(chunks)
        logger.info(f"[TIMING] Embedding: {time.time() - start_time:.2f}s")

        start_time = time.time()
        upsert_chunks(
            chunks=chunks,
            embeddings=vectors,
            metadata={
                "document_name": metadata["name"],
                "drive_file_id": metadata["id"],
                "source_link": metadata.get("webViewLink"),
            },
        )
        logger.info(f"[TIMING] Vector indexing: {time.time() - start_time:.2f}s")
        
        logger.info("[GRAPH] Building knowledge graph from text")

        start_time = time.time()
        graph_results = graph_builder.build_graph_from_chunks(
            chunks=chunks,
            document_id=metadata["id"]
        )
        logger.info(f"[TIMING] Graph building: {time.time() - start_time:.2f}s")

        # persist metadata and content for reference
        self.store_document_metadata(
            title=metadata["name"],
            source="Google Drive",
            content=text,
            checksum=checksum,
        )
        print(f"Ingested {pdf_path.name} with {len(chunks)} chunks")
        print(f"Chunks: {len(chunks)}, Graph Results: {graph_results}")
    

    # folder sync flow: list files, for each file check if exists, if not process
    def sync_drive_folder(self, folder_id=None):
        files = self.drive.list_pdfs(folder_id=folder_id)

        print(f"Found {len(files)} PDFs in folder")

        for file_meta in files:
            try:
                pdf_path = self.drive.download_file(
                    file_id=file_meta["id"],
                    filename=file_meta["name"],
                )
                self.process_pdf(
                    pdf_path=pdf_path,
                    metadata=file_meta,
                )
            except Exception as e:
                print(f"Failed to process {file_meta['name']}: {e}")

    
    # incremental sync flow: search for new files by name pattern, process if not exists
    def sync_new_or_updated(self, folder_id=None):
        """
        Incrementally sync new or updated files in the specified folder.
        """
        self.sync_drive_folder(folder_id=folder_id)

if __name__ == "__main__":
    service = IngestionSyncService(
        credentials_path=settings.GOOGLE_CREDENTIALS_PATH
    )
    service.sync_drive_folder(folder_id=settings.GOOGLE_DRIVE_FOLDER_ID)
            
