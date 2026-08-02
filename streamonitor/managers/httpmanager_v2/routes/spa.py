import mimetypes
from pathlib import Path

from litestar import get
from litestar.exceptions import NotFoundException
from litestar.response import Response

STATIC_DIR = Path(__file__).parent.parent / "static"

_INDEX_HEADERS = {"Cache-Control": "no-cache, no-store, must-revalidate"}


def _serve_index() -> Response:
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        raise NotFoundException(detail="Frontend not built. Run: cd frontend && npm run build")
    return Response(content=index.read_bytes(), media_type="text/html", headers=_INDEX_HEADERS)


@get("/", include_in_schema=False)
async def spa_root() -> Response:
    return _serve_index()


@get("/{path:path}", include_in_schema=False)
async def spa_fallback(path: str) -> Response:
    # Serve real files (JS/CSS assets, favicon, ...) with a proper MIME type.
    # Uses Response (not File) because File always emits Content-Disposition,
    # which makes the browser download index.html/assets instead of rendering
    # or loading them.
    # Litestar's {path:path} converter yields a leading slash; strip it before
    # joining so pathlib doesn't treat the request path as absolute and
    # discard STATIC_DIR.
    file_path = STATIC_DIR / path.lstrip("/")
    if file_path.is_file():
        media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        return Response(content=file_path.read_bytes(), media_type=media_type)

    # Client-side routing fallback: any unknown path is a React Router route,
    # so serve index.html.
    return _serve_index()
