"""Minimal WebSocket push layer.

Notifies connected clients when the background scanner completes a cycle so
the frontend can refresh instead of polling. The payload is a lightweight
signal, not the full dataset — clients still fetch the real data from the
REST endpoint, which now just reads the scanner's latest cached state.
"""

import json

from fastapi import WebSocket

_connections: list[WebSocket] = []


async def connect(ws: WebSocket) -> None:
    await ws.accept()
    _connections.append(ws)


def disconnect(ws: WebSocket) -> None:
    if ws in _connections:
        _connections.remove(ws)


async def broadcast_update(summary: dict) -> None:
    if not _connections:
        return
    message = json.dumps({"type": "opportunities_updated", **summary})
    stale = []
    for ws in _connections:
        try:
            await ws.send_text(message)
        except Exception:
            stale.append(ws)
    for ws in stale:
        disconnect(ws)
