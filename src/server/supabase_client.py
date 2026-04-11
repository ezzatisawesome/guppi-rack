"""Supabase client — service-role access for Supabase Storage.

The rack server uses the service-role key (bypasses RLS) to download
test scripts from the ``project-data`` storage bucket.
"""

import os
import logging

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

logger = logging.getLogger(__name__)

BUCKET = "project-data"

_client: Client | None = None


def _init_client() -> Client:
    """Create the Supabase client from environment variables."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables must be set"
        )

    client = create_client(url, key)
    logger.info("Supabase client initialized (url=%s)", url)
    return client


def get_supabase() -> Client:
    """Return the module-level Supabase client, creating it on first call."""
    global _client
    if _client is None:
        _client = _init_client()
    return _client


def download_file(storage_path: str) -> bytes | None:
    """Download a file from the ``project-data`` bucket.

    Args:
        storage_path: Full path within the bucket
            (e.g. ``projects/abc123/scripts/voltage_ramp.py``).

    Returns:
        File content as bytes, or None if not found.
    """
    client = get_supabase()
    try:
        data = client.storage.from_(BUCKET).download(storage_path)
        return data
    except Exception as exc:
        logger.error(
            "Failed to download file from storage: path=%s, error=%s",
            storage_path,
            exc,
        )
        return None
