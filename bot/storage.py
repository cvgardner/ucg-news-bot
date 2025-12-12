"""Cloud Storage integration for database persistence"""
import os
from pathlib import Path
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)

# GCS bucket name from environment variable
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
DATABASE_BLOB_NAME = "bot_data.db"


def is_gcs_enabled() -> bool:
    """Check if GCS integration is enabled"""
    return bool(GCS_BUCKET_NAME)


def download_database_from_gcs(local_path: str) -> bool:
    """
    Download database from Google Cloud Storage.

    Args:
        local_path: Local path where database should be saved

    Returns:
        True if download successful, False otherwise
    """
    if not is_gcs_enabled():
        logger.debug("GCS not configured, skipping database download")
        return False

    try:
        from google.cloud import storage

        logger.info(f"Downloading database from gs://{GCS_BUCKET_NAME}/{DATABASE_BLOB_NAME}...")

        # Initialize GCS client
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(DATABASE_BLOB_NAME)

        # Check if blob exists
        if not blob.exists():
            logger.info("No existing database in GCS, will create new one")
            return False

        # Ensure parent directory exists
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        # Download the blob
        blob.download_to_filename(local_path)

        logger.info(f"✓ Database downloaded successfully to {local_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to download database from GCS: {e}")
        return False


def upload_database_to_gcs(local_path: str) -> bool:
    """
    Upload database to Google Cloud Storage.

    Args:
        local_path: Local path of database file to upload

    Returns:
        True if upload successful, False otherwise
    """
    if not is_gcs_enabled():
        logger.debug("GCS not configured, skipping database upload")
        return False

    if not os.path.exists(local_path):
        logger.warning(f"Database file not found at {local_path}, skipping upload")
        return False

    try:
        from google.cloud import storage

        logger.info(f"Uploading database to gs://{GCS_BUCKET_NAME}/{DATABASE_BLOB_NAME}...")

        # Initialize GCS client
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(DATABASE_BLOB_NAME)

        # Upload the file
        blob.upload_from_filename(local_path)

        logger.info(f"✓ Database uploaded successfully to GCS")
        return True

    except Exception as e:
        logger.error(f"Failed to upload database to GCS: {e}")
        return False


def ensure_gcs_bucket_exists(bucket_name: Optional[str] = None) -> bool:
    """
    Ensure the GCS bucket exists, create if it doesn't.

    Args:
        bucket_name: Optional bucket name override

    Returns:
        True if bucket exists or was created, False otherwise
    """
    bucket_name = bucket_name or GCS_BUCKET_NAME

    if not bucket_name:
        logger.warning("No GCS bucket name configured")
        return False

    try:
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(bucket_name)

        if bucket.exists():
            logger.info(f"✓ GCS bucket '{bucket_name}' exists")
            return True

        # Create bucket
        logger.info(f"Creating GCS bucket '{bucket_name}'...")
        bucket = client.create_bucket(bucket_name)
        logger.info(f"✓ Created GCS bucket '{bucket_name}'")
        return True

    except Exception as e:
        logger.error(f"Failed to check/create GCS bucket: {e}")
        return False
