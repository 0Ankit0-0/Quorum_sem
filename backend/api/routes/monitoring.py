"""
Monitoring Routes
Persistent system monitoring service with WebSocket streaming and polling fallback.
"""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.monitoring_service import monitoring_service

router = APIRouter(prefix="/monitor", tags=["Monitoring"])


@router.post("/start")
async def start_monitoring():
    return {"status": "started", "state": monitoring_service.start()}


@router.post("/stop")
async def stop_monitoring():
    return {"status": "stopped", "state": monitoring_service.stop()}


@router.get("/status")
async def monitoring_status():
    return monitoring_service.status()


@router.get("/snapshot")
async def monitoring_snapshot(limit: int = 120):
    return monitoring_service.snapshot(limit=max(1, min(limit, 5000)))


@router.websocket("/ws")
async def monitoring_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(monitoring_service.snapshot(limit=10))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return

