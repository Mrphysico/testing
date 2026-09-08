from fastapi import WebSocket
from typing import List
import json
import logging

logger = logging.getLogger("app.websocket")

class ConnectionManager:
    def __init__(self):
        # Store active WebSocket connections
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        """
        Broadcast JSON messages to all connected clients.
        If a connection fails (e.g. client closed without closing WS handshake),
        we gracefully handle and clean up the dead connection.
        """
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message to connection: {e}")
                dead_connections.append(connection)
                
        # Clean up closed connections
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()
