import os, hashlib
from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/public", tags=["Media"])
STATIC_DIR = "/var/www/jyotish/backend/static"
_cache = {"data": None, "mtime": 0}

def _build_manifest():
    files = {}
    for root, dirs, filenames in os.walk(STATIC_DIR):
        for fn in filenames:
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, STATIC_DIR)
            stat = os.stat(fp)
            quick_hash = hashlib.md5(f"{stat.st_mtime}:{stat.st_size}:{rel}".encode()).hexdigest()[:12]
            files[rel] = {"hash": quick_hash, "size": int(stat.st_size)}
    return files

@router.get("/media-manifest")
async def get_manifest():
    now = datetime.now().timestamp()
    if _cache["data"] and now - _cache["mtime"] < 60:
        return _cache["data"]
    manifest = {"version": int(now), "files": _build_manifest()}
    _cache["data"] = manifest
    _cache["mtime"] = now
    return manifest

media_manifest_router = router
