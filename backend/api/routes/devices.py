"""
API Routes — Devices (devices.py)
Scan USB, LAN, physical devices and retrieve device history.
"""
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("/scan")
async def scan_devices(include_lan: bool = True):
    """Full device scan: USB + LAN nodes"""
    from core.device_monitor import device_monitor
    result = device_monitor.scan_all(include_lan=include_lan)
    summary = result.get_summary()
    return {
        "summary": summary,
        "usb_devices": [d.to_dict() for d in result.usb_devices],
        "lan_nodes":   [d.to_dict() for d in result.lan_nodes],
        "new_devices": [d.to_dict() for d in result.new_devices],
        "risky_devices": [d.to_dict() for d in result.risky_devices],
    }


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