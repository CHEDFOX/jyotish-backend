"""
STATIC MEDIA MANIFEST
Auto-scans /static/ directory, returns every file with its last-modified timestamp.
App uses this to cache-bust only changed files.

Add to public.py:
  from app.services.media_manifest import get_manifest
  
  @router.get("/media-manifest")
  async def media_manifest():
      return get_manifest()
"""

import os
from pathlib import Path

STATIC_DIR = Path(__file__).parent.parent.parent / "static"


def get_manifest():
    """Scan static dir, return {path: modified_timestamp} for every file."""
    files = {}
    if not STATIC_DIR.exists():
        return {"files": {}, "version": 0}

    for root, _, filenames in os.walk(STATIC_DIR):
        for fname in filenames:
            if fname.startswith('.'):
                continue
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, STATIC_DIR).replace("\\", "/")
            mtime = int(os.path.getmtime(full))
            files[rel] = mtime

    # Global version = max mtime across all files
    version = max(files.values()) if files else 0

    return {
        "files": files,
        "version": version,
    }
