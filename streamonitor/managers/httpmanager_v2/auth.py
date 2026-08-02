import secrets
import base64

from litestar.connection import ASGIConnection
from litestar.handlers import BaseRouteHandler
from litestar.exceptions import NotAuthorizedException

from parameters import WEBSERVER_PASSWORD


# In-memory token store: token -> True
_valid_tokens: set[str] = set()


def generate_token() -> str:
    token = secrets.token_urlsafe(32)
    _valid_tokens.add(token)
    return token


def validate_token(token: str) -> bool:
    return token in _valid_tokens


def revoke_token(token: str) -> None:
    _valid_tokens.discard(token)


def _check_basic_auth(authorization: str | None) -> bool:
    if not authorization or not authorization.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(authorization[6:]).decode("utf-8")
        username, _, password = decoded.partition(":")
        return username == "admin" and secrets.compare_digest(password, WEBSERVER_PASSWORD)
    except Exception:
        return False


def _check_bearer_token(authorization: str | None) -> bool:
    if not authorization or not authorization.startswith("Bearer "):
        return False
    token = authorization[7:]
    return validate_token(token)


async def auth_guard(connection: ASGIConnection, handler: BaseRouteHandler) -> None:
    """Litestar guard: allows if no password set, or valid basic/bearer auth.

    Async (not sync) deliberately: sync guards run inside a thread pool via
    sync_to_thread, and exceptions raised there were observed to escape the
    exception middleware under a live uvicorn server (returning 500 instead
    of 401). This guard does no blocking I/O, so running it on the event
    loop keeps NotAuthorizedException mapping intact.
    """
    if not WEBSERVER_PASSWORD:
        return

    authorization = connection.headers.get("authorization")

    if _check_basic_auth(authorization):
        return
    if _check_bearer_token(authorization):
        return

    # For WebSocket, also accept token as query param
    token_param = connection.query_params.get("token")
    if token_param and validate_token(token_param):
        return

    raise NotAuthorizedException(
        detail="Unauthorized",
        headers={"WWW-Authenticate": 'Basic realm="StreaMonitor"'},
    )
