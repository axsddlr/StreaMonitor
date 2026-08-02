import asyncio
import json
from dataclasses import asdict

from litestar import websocket, WebSocket
from litestar.exceptions import WebSocketDisconnect

from streamonitor.managers.httpmanager_v2.auth import validate_token
from streamonitor.managers.httpmanager_v2.serializers import streamer_to_dto, disk_space_dto
from parameters import WEBSERVER_PASSWORD


def _serialize_state(manager) -> str:
    streamers = [asdict(streamer_to_dto(s)) for s in manager.streamers]
    disk = asdict(disk_space_dto())
    return json.dumps({"streamers": streamers, "disk": disk})


@websocket("/ws/status")
async def status_feed(socket: WebSocket) -> None:
    manager = socket.app.state.manager

    # Auth check
    if WEBSERVER_PASSWORD:
        token = socket.query_params.get("token", "")
        if not validate_token(token):
            await socket.close(code=4001)
            return

    await socket.accept()
    previous = None

    try:
        while True:
            current = _serialize_state(manager)
            if current != previous:
                await socket.send_text(current)
                previous = current

            # Wait up to 3s for a client message (there won't be one — this is
            # a push-only feed), which doubles as a disconnect probe: a closed
            # connection raises WebSocketDisconnect immediately instead of
            # only being noticed on the next failed send_text(). Without this,
            # a client that disconnects while the state happens to stay
            # unchanged (e.g. disk usage/streamer list static) would never be
            # detected, leaking the handler task forever.
            try:
                await asyncio.wait_for(socket.receive_data(mode="text"), timeout=3)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
