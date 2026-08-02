from pathlib import Path

from litestar import get
from litestar.response import File
from litestar.exceptions import NotFoundException

STATIC_DIR = Path(__file__).parent.parent / "static"


@get("/{path:path}", include_in_schema=False)
async def spa_fallback(path: str) -> File:
    """Serve React SPA. Falls back to index.html for client-side routing."""
    # Try to serve exact file first (assets, etc.)
    file_path = STATIC_DIR / path
    if file_path.is_file():
        return File(path=str(file_path))

    # SPA fallback
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        # No build yet — return a minimal placeholder
        raise NotFoundException(detail="Frontend not built. Run: cd frontend && npm run build")
    return File(path=str(index), filename="index.html")


@get("/", include_in_schema=False)
async def spa_root() -> File:
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        raise NotFoundException(detail="Frontend not built. Run: cd frontend && npm run build")
    return File(path=str(index), filename="index.html")
