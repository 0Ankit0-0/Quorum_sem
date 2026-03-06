"""
API Routes - Devices (devices.py)
Scan USB, LAN, physical devices and retrieve device history.
"""
from fastapi import APIRouter, Query
import time

router = APIRouter(prefix="/devices", tags=["Devices"])

SCAN_CACHE_TTL_SECONDS = 20
_scan_cache = {
    True: {"expires_at": 0.0, "payload": None},
    False: {"expires_at": 0.0, "payload": None},
}


@router.get("/scan")
async def scan_devices(include_lan: bool = True, force_refresh: bool = False):
    """Full device scan: USB + LAN nodes"""
    cache_entry = _scan_cache[include_lan]
    now = time.time()

    if (
        not force_refresh
        and cache_entry["payload"] is not None
        and now < float(cache_entry["expires_at"])
    ):
        return cache_entry["payload"]

    from core.device_monitor import device_monitor

    result = device_monitor.scan_all(include_lan=include_lan)
    summary = result.get_summary()

    payload = {
        "summary": summary,
        "usb_devices": [d.to_dict() for d in result.usb_devices],
        "lan_nodes": [d.to_dict() for d in result.lan_nodes],
        "new_devices": [d.to_dict() for d in result.new_devices],
        "risky_devices": [d.to_dict() for d in result.risky_devices],
    }
    cache_entry["payload"] = payload
    cache_entry["expires_at"] = now + SCAN_CACHE_TTL_SECONDS
    return payload


@router.get("/usb")
async def list_usb_devices():
    """List currently attached USB devices"""
    from core.device_monitor import device_monitor

    devices = device_monitor.enumerate_usb_devices()
    return {"devices": [d.to_dict() for d in devices], "count": len(devices)}


@router.get("/lan")
async def discover_lan_nodes():
    """Discover machines on local network"""
    from core.device_monitor import device_monitor

    nodes = device_monitor.discover_lan_nodes()
    return {"nodes": [d.to_dict() for d in nodes], "count": len(nodes)}


@router.get("/history")
async def device_history(limit: int = Query(50, le=200)):
    """Device connection/disconnection history"""
    from core.database import db

    rows = db.fetch_all(
        "SELECT * FROM device_log ORDER BY connected_at DESC LIMIT ?",
        (limit,)
    )
    return {"history": rows, "count": len(rows)}


@router.get("/events")
async def device_events(limit: int = Query(100, le=1000)):
    """Device connect/remove events with connection duration."""
    from core.database import db

    rows = db.fetch_all(
        """
        SELECT
            device_id,
            name,
            device_class,
            connected_at,
            removed_at,
            duration_seconds,
            event,
            risk_level
        FROM device_log
        ORDER BY COALESCE(removed_at, connected_at) DESC
        LIMIT ?
        """,
        (limit,),
    )
    return {"events": rows, "count": len(rows)}


@router.post("/monitor/start")
async def start_device_monitor():
    """Start USB hotplug background monitor"""
    from core.device_monitor import device_monitor

    device_monitor.start_hotplug_monitor()
    return {"status": "started"}


@router.post("/monitor/stop")
async def stop_device_monitor():
    """Stop USB hotplug background monitor"""
    from core.device_monitor import device_monitor

    device_monitor.stop_hotplug_monitor()
    return {"status": "stopped"}
