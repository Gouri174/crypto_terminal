from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws import connect, disconnect

router = APIRouter()


@router.websocket("/ws/opportunities")
async def opportunities_ws(websocket: WebSocket):
    await connect(websocket)
    try:
        while True:
            # Nothing expected from the client — just keep the socket open
            # and drop it cleanly on disconnect.
            await websocket.receive_text()
    except WebSocketDisconnect:
        disconnect(websocket)
