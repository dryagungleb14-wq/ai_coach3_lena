import logging
import asyncio
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self._loop = None
    
    def set_event_loop(self, loop):
        self._loop = loop
    
    async def connect(self, websocket: WebSocket, call_id: int):
        await websocket.accept()
        if call_id not in self.active_connections:
            self.active_connections[call_id] = set()
        self.active_connections[call_id].add(websocket)
        logger.info(f"WebSocket подключен для звонка {call_id}")
    
    def disconnect(self, websocket: WebSocket, call_id: int):
        if call_id in self.active_connections:
            self.active_connections[call_id].discard(websocket)
            if not self.active_connections[call_id]:
                del self.active_connections[call_id]
        logger.info(f"WebSocket отключен для звонка {call_id}")
    
    async def send_progress(self, call_id: int, progress: int, status: str, message: str = None):
        if call_id not in self.active_connections:
            return
        
        data = {
            "call_id": call_id,
            "progress": progress,
            "status": status
        }
        if message:
            data["message"] = message
        
        disconnected = set()
        for websocket in self.active_connections[call_id]:
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Ошибка отправки WebSocket сообщения: {e}")
                disconnected.add(websocket)
        
        for ws in disconnected:
            self.disconnect(ws, call_id)
    
    def send_progress_sync(self, call_id: int, progress: int, status: str, message: str = None):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.send_progress(call_id, progress, status, message),
                self._loop
            )
        else:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.send_progress(call_id, progress, status, message))
                else:
                    loop.run_until_complete(self.send_progress(call_id, progress, status, message))
            except Exception as e:
                logger.warning(f"Ошибка отправки WebSocket обновления: {e}")

manager = WebSocketManager()

