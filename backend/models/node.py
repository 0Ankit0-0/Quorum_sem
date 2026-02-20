"""
Node & Device Data Models
Covers terminal nodes, hub registration, and physical device inventory
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class NodeStatus(str, Enum):
    ACTIVE    = "active"
    INACTIVE  = "inactive"
    SYNCING   = "syncing"
    ERROR     = "error"


class NodeRole(str, Enum):
    TERMINAL  = "terminal"
    HUB       = "hub"


class SyncMethod(str, Enum):
    USB       = "usb"
    LAN       = "lan"
    MANUAL    = "manual"


class DeviceClass(str, Enum):
    STORAGE        = "storage"       # USB drives, SD cards
    AUDIO          = "audio"         # Headphones, speakers, mics
    HID            = "hid"           # Keyboards, mice
    NETWORK        = "network"       # USB network adapters
    PRINTER        = "printer"
    CAMERA         = "camera"
    SMARTPHONE     = "smartphone"
    UNKNOWN        = "unknown"
    LAN_NODE       = "lan_node"      # Network-discovered machines


# ─── Node Model ──────────────────────────────────────────────────────────────

@dataclass
class QuorumNode:
    """A registered Quorum terminal or hub node"""
    node_id: str
    hostname: str
    role: NodeRole
    status: NodeStatus
    ip_address: Optional[str] = None
    os_info: Optional[str] = None
    quorum_version: Optional[str] = None
    last_seen: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    total_logs: int = 0
    total_anomalies: int = 0
    sync_method: SyncMethod = SyncMethod.MANUAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        import json
        return {
            'node_id':         self.node_id,
            'hostname':        self.hostname,
            'role':            self.role.value,
            'status':          self.status.value,
            'ip_address':      self.ip_address,
            'os_info':         self.os_info,
            'quorum_version':  self.quorum_version,
            'last_seen':       self.last_seen,
            'last_sync':       self.last_sync,
            'total_logs':      self.total_logs,
            'total_anomalies': self.total_anomalies,
            'sync_method':     self.sync_method.value,
            'metadata':        json.dumps(self.metadata)
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'QuorumNode':
        import json
        return cls(
            node_id         = d['node_id'],
            hostname        = d['hostname'],
            role            = NodeRole(d.get('role', 'terminal')),
            status          = NodeStatus(d.get('status', 'inactive')),
            ip_address      = d.get('ip_address'),
            os_info         = d.get('os_info'),
            quorum_version  = d.get('quorum_version'),
            last_seen       = d.get('last_seen'),
            last_sync       = d.get('last_sync'),
            total_logs      = d.get('total_logs', 0),
            total_anomalies = d.get('total_anomalies', 0),
            sync_method     = SyncMethod(d.get('sync_method', 'manual')),
            metadata        = json.loads(d['metadata']) if d.get('metadata') else {}
        )

    def get_threat_level(self) -> str:
        """Compute threat level from anomaly count"""
        if self.total_anomalies == 0:
            return 'CLEAN'
        rate = self.total_anomalies / max(self.total_logs, 1)
        if rate >= 0.20:
            return 'CRITICAL'
        elif rate >= 0.10:
            return 'HIGH'
        elif rate >= 0.05:
            return 'MEDIUM'
        return 'LOW'


@dataclass
class SyncPackage:
    """Data package exchanged between nodes during sync"""
    package_id:   str
    source_node:  str
    target_node:  str
    sync_method:  SyncMethod
    created_at:   datetime
    anomalies:    List[Dict[str, Any]] = field(default_factory=list)
    logs_summary: Dict[str, Any]       = field(default_factory=dict)
    metadata:     Dict[str, Any]       = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        import json
        return {
            'package_id':   self.package_id,
            'source_node':  self.source_node,
            'target_node':  self.target_node,
            'sync_method':  self.sync_method.value,
            'created_at':   self.created_at.isoformat(),
            'anomalies':    self.anomalies,
            'logs_summary': self.logs_summary,
            'metadata':     self.metadata
        }


# ─── Device Model ─────────────────────────────────────────────────────────────

@dataclass
class AttachedDevice:
    """A physical or network device detected on the system"""
    device_id:    str
    device_class: DeviceClass
    name:         str
    vendor:       Optional[str] = None
    vendor_id:    Optional[str] = None    # USB VID (e.g. 0x0781)
    product_id:   Optional[str] = None    # USB PID (e.g. 0x5567)
    serial:       Optional[str] = None
    mount_point:  Optional[str] = None    # For storage devices
    ip_address:   Optional[str] = None    # For LAN nodes
    mac_address:  Optional[str] = None
    connected_at: Optional[datetime] = None
    is_new:       bool = False            # First time seen?
    risk_level:   str = 'INFO'
    metadata:     Dict[str, Any] = field(default_factory=dict)

    # Known safe vendor IDs (keyboards, mice, monitors)
    SAFE_VENDOR_IDS = {
        '046d',  # Logitech
        '045e',  # Microsoft
        '04f2',  # Chicony (keyboards)
        '0461',  # Primax (mice)
        '04b3',  # IBM
        '413c',  # Dell
        '05ac',  # Apple
        '0b05',  # ASUS
    }

    # Known risky device classes for air-gapped environments
    RISKY_CLASSES = {
        DeviceClass.STORAGE,
        DeviceClass.NETWORK,
        DeviceClass.SMARTPHONE,
    }

    def to_dict(self) -> Dict[str, Any]:
        import json
        return {
            'device_id':    self.device_id,
            'device_class': self.device_class.value,
            'name':         self.name,
            'vendor':       self.vendor,
            'vendor_id':    self.vendor_id,
            'product_id':   self.product_id,
            'serial':       self.serial,
            'mount_point':  self.mount_point,
            'ip_address':   self.ip_address,
            'mac_address':  self.mac_address,
            'connected_at': self.connected_at.isoformat() if self.connected_at else None,
            'is_new':       self.is_new,
            'risk_level':   self.risk_level,
            'metadata':     json.dumps(self.metadata)
        }

    def assess_risk(self) -> str:
        """Assess risk level of this device"""
        if self.device_class in self.RISKY_CLASSES:
            if self.vendor_id and self.vendor_id.lower() in self.SAFE_VENDOR_IDS:
                return 'LOW'
            return 'HIGH'
        if self.device_class == DeviceClass.AUDIO:
            return 'MEDIUM'   # Possible covert channel
        if self.device_class == DeviceClass.HID:
            return 'LOW'
        return 'INFO'


@dataclass
class DeviceScanResult:
    """Result of a full device scan"""
    scan_id:         str
    scanned_at:      datetime
    usb_devices:     List[AttachedDevice] = field(default_factory=list)
    lan_nodes:       List[AttachedDevice] = field(default_factory=list)
    new_devices:     List[AttachedDevice] = field(default_factory=list)
    risky_devices:   List[AttachedDevice] = field(default_factory=list)
    scan_duration_s: float = 0.0

    def get_summary(self) -> Dict[str, Any]:
        all_devices = self.usb_devices + self.lan_nodes
        by_class = {}
        for d in all_devices:
            cls = d.device_class.value
            by_class[cls] = by_class.get(cls, 0) + 1

        return {
            'total_devices':  len(all_devices),
            'usb_count':      len(self.usb_devices),
            'lan_count':      len(self.lan_nodes),
            'new_devices':    len(self.new_devices),
            'risky_devices':  len(self.risky_devices),
            'by_class':       by_class,
            'scan_duration_s': self.scan_duration_s
        }