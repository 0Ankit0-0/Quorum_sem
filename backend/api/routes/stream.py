"""
API Routes — Stream (stream.py)
Server-Sent Events (SSE) endpoint for real-time log streaming.
Frontend/CLI can subscribe and receive live anomaly alerts as they happen.
"""
import asyncio
import json
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/stream", tags=["Streaming"])


async def _event_generator(
    min_score: float = 0.0,
    severity_filter: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE-formatted events from the real-time monitor.
    Runs in an async loop, pulling from the monitor's thread-safe queue.
    """
    from core.realtime_monitor import realtime_monitor

    yield f"data: {json.dumps({'event': 'connected', 'message': 'Stream started'})}\n\n"

    loop = asyncio.get_event_loop()

    while True:
        # Run blocking queue.get in thread pool to stay async-friendly
        entry = await loop.run_in_executor(
            None,
            lambda: realtime_monitor.get_event(timeout=1.0)
        )

        if entry is None:
            # Keepalive ping every second
            yield ": ping\n\n"
            continue

        # Apply filters
        if entry.anomaly_score < min_score:
            continue

        if severity_filter:
            sev_order = {'INFO': 0, 'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}
            if sev_order.get(entry.severity, 0) < sev_order.get(severity_filter.upper(), 0):
                continue

        payload = json.dumps(entry.to_dict(), default=str)
        yield f"data: {payload}\n\n"

        await asyncio.sleep(0)   # Yield control to event loop


@router.get(
    "/logs",
    response_class=StreamingResponse,
    summary="SSE: Real-time log stream",
    description=(
        "Subscribe to a Server-Sent Events stream of live log entries. "
        "Emits events as new log lines are detected in watched files. "
        "Connect with EventSource in browser or curl --no-buffer."
    )
)
async def stream_logs(
    min_score: float = Query(0.0, description="Minimum anomaly score to emit"),
    severity:  Optional[str] = Query(None, description="Minimum severity (INFO/LOW/MEDIUM/HIGH/CRITICAL)")
):
    """
    SSE stream of real-time log entries.

    Connect with:\n
      curl -N http://localhost:8000/stream/logs\n
      curl -N "http://localhost:8000/stream/logs?min_score=0.70&severity=HIGH"\n
    """
    return StreamingResponse(
        _event_generator(min_score=min_score, severity_filter=severity),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@router.get("/status")
async def stream_status():
    """Current real-time monitor status"""
    from core.realtime_monitor import realtime_monitor
    return {
        "running": realtime_monitor.is_running(),
        "stats":   realtime_monitor.get_stats()
    }


@router.post("/start")
async def start_stream(files: Optional[list] = None):
    """Start the real-time monitor with specified files"""
    from core.realtime_monitor import realtime_monitor

    added = []
    if files:
        for f in files:
            if realtime_monitor.add_file(f):
                added.append(f)

    if not realtime_monitor.is_running():
        realtime_monitor.start()

    return {
        "status":      "started",
        "files_added": added,
        "total_watched": len(realtime_monitor.list_files())
    }


@router.post("/stop")
async def stop_stream():
    """Stop the real-time monitor"""
    from core.realtime_monitor import realtime_monitor
    realtime_monitor.stop()
    return {"status": "stopped"}


@router.post("/watch")
async def add_watch_file(file_path: str):
    """Add a file to the real-time watch list"""
    from core.realtime_monitor import realtime_monitor
    success = realtime_monitor.add_file(file_path)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Cannot open file: {file_path}")
    return {"status": "watching", "file": file_path}


@router.delete("/watch")
async def remove_watch_file(file_path: str):
    """Remove a file from the watch list"""
    from core.realtime_monitor import realtime_monitor
    realtime_monitor.remove_file(file_path)
    return {"status": "removed", "file": file_path}