"""WebSocket Connection and Broadcast Manager.
Maintains active real-time client connections and broadcasts telemetry updates.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("conveyor_ai.websocket")


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
        self.latest_packet: Optional[Dict[str, Any]] = None

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection and send current state."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

        # Send latest state if available
        if self.latest_packet is not None:
            try:
                await websocket.send_text(json.dumps(self.latest_packet))
            except Exception as e:
                logger.warning(f"Failed to send initial packet to client: {e}")

    async def disconnect(self, websocket: WebSocket):
        """Remove disconnected client."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast JSON message to all connected clients."""
        self.latest_packet = message
        payload = json.dumps(message)
        dead_connections: List[WebSocket] = []

        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(payload)
                except Exception as e:
                    logger.debug(f"Error broadcasting to client: {e}")
                    dead_connections.append(connection)

            for dead in dead_connections:
                if dead in self.active_connections:
                    self.active_connections.remove(dead)


# Singleton instance
ws_manager = WebSocketManager()
