"""
API Routes — Hub (hub.py)
Endpoints for multi-node aggregation, sync, and cross-correlation.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Optional

router = APIRouter(prefix="/hub", tags=["Hub"])


@router.get("/dashboard")
async def get_dashboard():
    """Aggregated threat dashboard across all nodes"""
    from services.hub_service import hub_service
    return hub_service.get_aggregated_dashboard()

@router.get("/info")
async def get_hub_info():
    """Basic info about this node for hub screen header."""
    from services.hub_service import hub_service
    node = hub_service.register_this_node(role="terminal")
    return node.to_dict()


@router.get("/nodes")
async def list_nodes():
    """List all registered Quorum nodes"""
    from services.hub_service import hub_service
    return {"nodes": hub_service.list_nodes()}


@router.post("/nodes/register")
async def register_node(role: str = "terminal"):
    """Register this machine as a Quorum node"""
    from services.hub_service import hub_service
    node = hub_service.register_this_node(role=role)
    return node.to_dict()


@router.get("/correlations")
async def get_correlations():
    """Find cross-node attack correlations"""
    from services.hub_service import hub_service
    return {"correlations": hub_service.get_cross_node_correlations()}


@router.get("/heatmap")
async def get_mitre_heatmap():
    """MITRE ATT&CK technique heatmap across nodes"""
    from services.hub_service import hub_service
    return hub_service.get_mitre_heatmap()


@router.post("/export")
async def export_sync_package(target_node: str = "hub", sign: bool = True):
    """Export local anomalies as a signed sync package"""
    from services.hub_service import hub_service
    try:
        path = hub_service.export_sync_package(
            target_node_id=target_node, sign=sign
        )
        return FileResponse(
            path=str(path),
            filename=path.name,
            media_type="application/octet-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_sync_package(package_path: str):
    """Import a sync package from a terminal node"""
    from services.hub_service import hub_service
    p = Path(package_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Package file not found")
    return hub_service.import_sync_package(p)


@router.get("/scan-usb")
async def scan_usb_packages():
    """Scan USB drives for .qsp sync packages"""
    from services.hub_service import hub_service
    packages = hub_service.scan_usb_for_sync_packages()
    return {"packages": [str(p) for p in packages]}
