"""Azure Blob Storage integration for audit log file archiving and proxy downloads."""

import os
import json
import logging
from typing import Optional, List, Dict

logger = logging.getLogger("rsli.blob_store")

class BlobAuditStore:
    def __init__(self, connection_string: Optional[str] = None):
        self.enabled = bool(connection_string)
        self.container_name = os.environ.get("RSLI_BLOB_CONTAINER", "rsli-audit")
        self.container = None
        self.client = None
        
        if self.enabled:
            try:
                from azure.storage.blob import BlobServiceClient
                self.client = BlobServiceClient.from_connection_string(connection_string)
                self.container = self.client.get_container_client(self.container_name)
                # Try to create container if it doesn't exist
                try:
                    self.container.create_container()
                except Exception:
                    pass  # already exists or other error
                logger.info(f"BlobAuditStore successfully initialized with container: {self.container_name}")
            except Exception as e:
                logger.error(f"Failed to initialize BlobAuditStore: {e}")
                self.enabled = False

    async def upload_file(self, session_id: str, category: str, filename: str, data: bytes):
        """Upload a file to Blob. Categories: 'source_files', 'output_files', 'llm_logs', 'overrides'."""
        if not self.enabled:
            return
        blob_path = f"{session_id}/{category}/{filename}"
        try:
            import asyncio
            blob_client = self.container.get_blob_client(blob_path)
            await asyncio.to_thread(blob_client.upload_blob, data, overwrite=True)
            logger.info(f"Successfully uploaded {blob_path} to Azure Blob")
        except Exception as e:
            logger.error(f"Failed to upload file {blob_path} to Blob: {e}")

    async def upload_json(self, session_id: str, category: str, filename: str, data: dict):
        """Upload a JSON document to Blob."""
        await self.upload_file(
            session_id, 
            category, 
            filename, 
            json.dumps(data, default=str, indent=2).encode("utf-8")
        )

    async def download_file(self, session_id: str, category: str, filename: str) -> Optional[bytes]:
        """Download a file from Blob. Returns None if not found or if store disabled."""
        if not self.enabled:
            return None
        blob_path = f"{session_id}/{category}/{filename}"
        try:
            import asyncio
            blob_client = self.container.get_blob_client(blob_path)
            stream = await asyncio.to_thread(blob_client.download_blob)
            return await asyncio.to_thread(stream.readall)
        except Exception as e:
            logger.warning(f"Failed to download file {blob_path} from Blob: {e}")
            return None

    async def list_files(self, session_id: str, category: str) -> List[str]:
        """List files in a session category."""
        if not self.enabled:
            return []
        prefix = f"{session_id}/{category}/"
        try:
            import asyncio
            blobs = await asyncio.to_thread(self.container.list_blobs, name_starts_with=prefix)
            names = []
            for b in blobs:
                # name is like "{session_id}/{category}/{filename}"
                parts = b.name.split("/")
                if len(parts) > 2:
                    names.append(parts[-1])
            return names
        except Exception as e:
            logger.error(f"Failed to list files with prefix {prefix} in Blob: {e}")
            return []

    async def upload_session_files(self, session_id: str, temp_dir: str, overrides: Optional[dict] = None):
        """Upload source files, output files, and optional overrides JSON to Blob."""
        if not self.enabled:
            return
        
        # 1. Upload source files
        uploads_dir = os.path.join(temp_dir, "uploads")
        if os.path.isdir(uploads_dir):
            for name in os.listdir(uploads_dir):
                fp = os.path.join(uploads_dir, name)
                if os.path.isfile(fp):
                    try:
                        with open(fp, "rb") as f:
                            data = f.read()
                        await self.upload_file(session_id, "source_files", name, data)
                    except Exception as e:
                        logger.error(f"Failed uploading source file {name}: {e}")

        # 2. Upload output files
        output_dir = os.path.join(temp_dir, "output")
        if os.path.isdir(output_dir):
            for name in os.listdir(output_dir):
                fp = os.path.join(output_dir, name)
                if os.path.isfile(fp):
                    try:
                        with open(fp, "rb") as f:
                            data = f.read()
                        await self.upload_file(session_id, "output_files", name, data)
                    except Exception as e:
                        logger.error(f"Failed uploading output file {name}: {e}")

        # 3. Upload overrides.json
        if overrides is not None:
            await self.upload_json(session_id, "overrides", "overrides.json", overrides)
