"""
Device Monitor
Detects USB hotplug events, enumerates all attached devices by USB VID/PID,
classifies them (storage, audio, HID, network, smartphone…), and scans LAN.
"""
import platform
import threading
import time
import uuid
import socket
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from models.node import AttachedDevice, DeviceClass, DeviceScanResult
from config.logging_config import get_logger

logger = get_logger(__name__)

# ─── USB Device Class codes (bDeviceClass / bInterfaceClass) ─────────────────
USB_CLASS_MAP: Dict[str, DeviceClass] = {
    '00': DeviceClass.UNKNOWN,
    '01': DeviceClass.AUDIO,
    '02': DeviceClass.NETWORK,        # CDC (comm devices)
    '03': DeviceClass.HID,
    '06': DeviceClass.CAMERA,         # Still imaging
    '07': DeviceClass.PRINTER,
    '08': DeviceClass.STORAGE,        # Mass storage
    '0a': DeviceClass.NETWORK,        # CDC-data
    'e0': DeviceClass.NETWORK,        # Wireless / Bluetooth
    'ef': DeviceClass.SMARTPHONE,     # Miscellaneous (Android MTP)
    'ff': DeviceClass.UNKNOWN,
}

# VID → vendor name lookup (subset)
VENDOR_NAMES: Dict[str, str] = {
    '0781': 'SanDisk',
    '058f': 'Alcor (Generic USB)',
    '13fe': 'Kingston',
    '0951': 'Kingston DataTraveler',
    '8564': 'Transcend',
    '14cd': 'Super Top',
    '05ac': 'Apple',
    '18d1': 'Google (Android)',
    '0e8d': 'MediaTek (Android)',
    '2717': 'Xiaomi',
    '04e8': 'Samsung',
    '0bb4': 'HTC',
    '12d1': 'Huawei',
    '046d': 'Logitech',
    '045e': 'Microsoft',
    '04f2': 'Chicony',
    '0bda': 'Realtek (USB Network)',
    '0b95': 'ASIX (USB Ethernet)',
    '0403': 'FTDI (USB-Serial)',
    '04d8': 'Microchip',
    '0d8c': 'C-Media (USB Audio)',
    '08bb': 'Texas Instruments (Audio)',
    '1a86': 'QinHeng (USB-Serial)',
}


class DeviceMonitor:
    """
    Monitors and enumerates all devices attached to the system.

    Supports:
    - USB enumeration (Windows: WMI, Linux: /sys/bus/usb, macOS: system_profiler)
    - USB hotplug detection (background thread)
    - LAN node discovery (subnet ping + port scan)
    - Device classification by USB VID/PID/class
    - Risk assessment for air-gapped environments
    """

    def __init__(self):
        self._system = platform.system()
        self._known_devices: Dict[str, AttachedDevice] = {}   # device_id → device
        self._hotplug_thread: Optional[threading.Thread] = None
        self._hotplug_running = False
        self._callbacks: List[Callable[[AttachedDevice, str], None]] = []  # (device, event)
        self._lock = threading.Lock()

    # ─── Public API ──────────────────────────────────────────────────────────

    def scan_all(self, include_lan: bool = True) -> DeviceScanResult:
        """Full device scan: USB + LAN"""
        start = time.time()
        scan_id = str(uuid.uuid4())
        logger.info("Starting full device scan...")

        usb_devices = self.enumerate_usb_devices()
        lan_nodes   = self.discover_lan_nodes() if include_lan else []

        all_devices  = usb_devices + lan_nodes
        new_devices  = [d for d in all_devices if d.is_new]
        risky_devices = [d for d in all_devices if d.risk_level in ('HIGH', 'CRITICAL')]

        # Update known devices cache
        with self._lock:
            for d in all_devices:
                self._known_devices[d.device_id] = d

        result = DeviceScanResult(
            scan_id         = scan_id,
            scanned_at      = datetime.utcnow(),
            usb_devices     = usb_devices,
            lan_nodes       = lan_nodes,
            new_devices     = new_devices,
            risky_devices   = risky_devices,
            scan_duration_s = round(time.time() - start, 2)
        )

        logger.info(
            f"Scan complete: {len(usb_devices)} USB, {len(lan_nodes)} LAN "
            f"({len(new_devices)} new, {len(risky_devices)} risky)"
        )
        return result

    def enumerate_usb_devices(self) -> List[AttachedDevice]:
        """Enumerate all USB devices with VID/PID classification"""
        try:
            if self._system == 'Windows':
                return self._enum_windows_usb()
            elif self._system == 'Linux':
                return self._enum_linux_usb()
            elif self._system == 'Darwin':
                return self._enum_macos_usb()
        except Exception as e:
            logger.error(f"USB enumeration failed: {e}")
        return []

    def discover_lan_nodes(self, timeout: float = 1.0) -> List[AttachedDevice]:
        """Discover LAN-connected machines via ARP + ping sweep"""
        try:
            local_ip = self._get_local_ip()
            if not local_ip:
                return []

            subnet = '.'.join(local_ip.split('.')[:3])
            logger.info(f"Scanning subnet {subnet}.0/24 for nodes...")

            nodes = []
            threads = []
            results = []
            lock = threading.Lock()

            def probe(ip):
                try:
                    # Ping probe
                    if self._system == 'Windows':
                        cmd = ['ping', '-n', '1', '-w', '300', ip]
                    else:
                        cmd = ['ping', '-c', '1', '-W', '1', ip]

                    r = subprocess.run(cmd, capture_output=True, timeout=2)
                    if r.returncode == 0:
                        hostname = self._resolve_hostname(ip)
                        mac = self._get_mac_address(ip)
                        device = AttachedDevice(
                            device_id    = f"lan_{ip.replace('.','_')}",
                            device_class = DeviceClass.LAN_NODE,
                            name         = hostname or ip,
                            ip_address   = ip,
                            mac_address  = mac,
                            connected_at = datetime.utcnow(),
                            is_new       = f"lan_{ip}" not in self._known_devices,
                            risk_level   = 'INFO',
                            metadata     = {'hostname': hostname, 'mac': mac}
                        )
                        with lock:
                            results.append(device)
                except Exception:
                    pass

            # Scan first 50 IPs (balance speed vs coverage)
            for i in range(1, 51):
                ip = f"{subnet}.{i}"
                t = threading.Thread(target=probe, args=(ip,), daemon=True)
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=3)

            return results

        except Exception as e:
            logger.error(f"LAN discovery failed: {e}")
            return []

    def start_hotplug_monitor(self):
        """Start background thread that detects USB hotplug events"""
        if self._hotplug_running:
            return

        self._hotplug_running = True
        self._hotplug_thread = threading.Thread(
            target=self._hotplug_loop,
            daemon=True,
            name="QuorumDeviceMonitor"
        )
        self._hotplug_thread.start()
        logger.info("USB hotplug monitor started")

    def stop_hotplug_monitor(self):
        """Stop the hotplug background thread"""
        self._hotplug_running = False
        if self._hotplug_thread:
            self._hotplug_thread.join(timeout=3)
        logger.info("USB hotplug monitor stopped")

    def on_device_event(self, callback: Callable[[AttachedDevice, str], None]):
        """Register callback for device connect/disconnect events"""
        self._callbacks.append(callback)

    # ─── OS-Specific USB Enumeration ─────────────────────────────────────────

    def _enum_windows_usb(self) -> List[AttachedDevice]:
        """Windows USB enumeration via WMI"""
        devices = []
        try:
            import subprocess, re

            # Get USB devices via PowerShell WMI
            ps_cmd = (
                "Get-WmiObject Win32_PnPEntity | "
                "Where-Object {$_.PNPDeviceID -like 'USB*'} | "
                "Select-Object Name,PNPDeviceID,Manufacturer,Description | "
                "ConvertTo-Json"
            )
            result = subprocess.run(
                ['powershell', '-Command', ps_cmd],
                capture_output=True, text=True, timeout=15
            )

            if result.returncode == 0 and result.stdout.strip():
                import json
                raw = result.stdout.strip()
                # PowerShell may return single object or array
                if raw.startswith('{'):
                    raw = f'[{raw}]'
                items = json.loads(raw)

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    pnp_id = item.get('PNPDeviceID', '')
                    name   = item.get('Name', 'Unknown USB Device')

                    # Extract VID/PID from PNPDeviceID
                    vid_match = re.search(r'VID_([0-9A-Fa-f]{4})', pnp_id)
                    pid_match = re.search(r'PID_([0-9A-Fa-f]{4})', pnp_id)

                    vid = vid_match.group(1).lower() if vid_match else None
                    pid = pid_match.group(1).lower() if pid_match else None

                    device_class = self._classify_by_name_and_vid(name, vid)
                    vendor       = VENDOR_NAMES.get(vid, item.get('Manufacturer', 'Unknown'))

                    d = AttachedDevice(
                        device_id    = f"usb_{vid}_{pid}_{hash(pnp_id) % 99999}",
                        device_class = device_class,
                        name         = name,
                        vendor       = vendor,
                        vendor_id    = vid,
                        product_id   = pid,
                        connected_at = datetime.utcnow(),
                        is_new       = f"usb_{vid}_{pid}" not in self._known_devices,
                        metadata     = {'pnp_id': pnp_id}
                    )
                    d.risk_level = d.assess_risk()
                    devices.append(d)

            # Also get removable drives with mount points
            drives = self._get_windows_removable_drives()
            for drv in drives:
                # Match with existing device or add new
                matched = False
                for d in devices:
                    if d.device_class == DeviceClass.STORAGE and not d.mount_point:
                        d.mount_point = drv
                        matched = True
                        break
                if not matched:
                    d = AttachedDevice(
                        device_id    = f"drive_{drv.replace(':','')}",
                        device_class = DeviceClass.STORAGE,
                        name         = f"Removable Drive ({drv})",
                        mount_point  = drv,
                        connected_at = datetime.utcnow(),
                        is_new       = f"drive_{drv}" not in self._known_devices,
                        risk_level   = 'HIGH'
                    )
                    devices.append(d)

        except Exception as e:
            logger.error(f"Windows USB enum failed: {e}")

        return devices

    def _enum_linux_usb(self) -> List[AttachedDevice]:
        """Linux USB enumeration via /sys/bus/usb/devices"""
        devices = []
        usb_root = Path('/sys/bus/usb/devices')

        if not usb_root.exists():
            return devices

        try:
            for entry in usb_root.iterdir():
                try:
                    vid_file = entry / 'idVendor'
                    pid_file = entry / 'idProduct'
                    if not vid_file.exists():
                        continue

                    vid  = vid_file.read_text().strip().lower()
                    pid  = pid_file.read_text().strip().lower() if pid_file.exists() else None

                    # Product name
                    prod_file = entry / 'product'
                    name = prod_file.read_text().strip() if prod_file.exists() else 'USB Device'

                    # Manufacturer
                    mfr_file = entry / 'manufacturer'
                    vendor = mfr_file.read_text().strip() if mfr_file.exists() else VENDOR_NAMES.get(vid, 'Unknown')

                    # Device class
                    cls_file = entry / 'bDeviceClass'
                    cls_code = cls_file.read_text().strip().lower() if cls_file.exists() else 'ff'
                    # Remove leading zeros for lookup
                    cls_code_hex = format(int(cls_code, 16), '02x')
                    device_class = USB_CLASS_MAP.get(cls_code_hex, DeviceClass.UNKNOWN)

                    # Override by name if class is generic
                    if device_class == DeviceClass.UNKNOWN:
                        device_class = self._classify_by_name_and_vid(name, vid)

                    # Serial
                    ser_file = entry / 'serial'
                    serial = ser_file.read_text().strip() if ser_file.exists() else None

                    d = AttachedDevice(
                        device_id    = f"usb_{vid}_{pid}_{entry.name}",
                        device_class = device_class,
                        name         = name,
                        vendor       = vendor,
                        vendor_id    = vid,
                        product_id   = pid,
                        serial       = serial,
                        connected_at = datetime.utcnow(),
                        is_new       = f"usb_{vid}_{pid}" not in self._known_devices,
                        metadata     = {'sysfs_path': str(entry)}
                    )
                    d.risk_level = d.assess_risk()

                    # Find mount point for storage
                    if device_class == DeviceClass.STORAGE:
                        d.mount_point = self._find_linux_mount(entry.name)

                    devices.append(d)

                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Linux USB enum failed: {e}")

        return devices

    def _enum_macos_usb(self) -> List[AttachedDevice]:
        """macOS USB enumeration via system_profiler"""
        devices = []
        try:
            result = subprocess.run(
                ['system_profiler', 'SPUSBDataType', '-json'],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return devices

            import json, re
            data = json.loads(result.stdout)

            def parse_items(items):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    name     = item.get('_name', 'USB Device')
                    vendor   = item.get('manufacturer', 'Unknown')
                    vid_raw  = item.get('vendor_id', '')
                    pid_raw  = item.get('product_id', '')
                    serial   = item.get('serial_num')

                    vid = re.sub(r'0x', '', vid_raw).lower().zfill(4)[:4]
                    pid = re.sub(r'0x', '', pid_raw).lower().zfill(4)[:4]

                    device_class = self._classify_by_name_and_vid(name, vid)
                    vendor_name  = VENDOR_NAMES.get(vid, vendor)

                    d = AttachedDevice(
                        device_id    = f"usb_{vid}_{pid}_{hash(name) % 99999}",
                        device_class = device_class,
                        name         = name,
                        vendor       = vendor_name,
                        vendor_id    = vid,
                        product_id   = pid,
                        serial       = serial,
                        connected_at = datetime.utcnow(),
                        is_new       = f"usb_{vid}_{pid}" not in self._known_devices
                    )
                    d.risk_level = d.assess_risk()
                    devices.append(d)

                    # Recurse into sub-items
                    for sub_key in item:
                        if isinstance(item[sub_key], list):
                            parse_items(item[sub_key])

            for top in data.get('SPUSBDataType', []):
                if isinstance(top, dict):
                    parse_items(top.get('_items', []))

        except Exception as e:
            logger.error(f"macOS USB enum failed: {e}")

        return devices

    # ─── Hotplug Loop ────────────────────────────────────────────────────────

    def _hotplug_loop(self):
        """Background thread: poll for device changes every 3 seconds"""
        previous_ids = set(self._known_devices.keys())

        while self._hotplug_running:
            try:
                current_devices = self.enumerate_usb_devices()
                current_ids     = {d.device_id for d in current_devices}

                new_ids  = current_ids - previous_ids
                gone_ids = previous_ids - current_ids

                for d in current_devices:
                    if d.device_id in new_ids:
                        d.is_new = True
                        logger.info(f"Device CONNECTED: {d.name} [{d.device_class.value}]")
                        self._persist_device(d, 'connected')
                        for cb in self._callbacks:
                            try:
                                cb(d, 'connected')
                            except Exception:
                                pass

                for gone_id in gone_ids:
                    d = self._known_devices.get(gone_id)
                    if d:
                        logger.info(f"Device DISCONNECTED: {d.name}")
                        self._persist_device(d, 'disconnected')
                        for cb in self._callbacks:
                            try:
                                cb(d, 'disconnected')
                            except Exception:
                                pass

                with self._lock:
                    for d in current_devices:
                        self._known_devices[d.device_id] = d
                    for gone_id in gone_ids:
                        self._known_devices.pop(gone_id, None)

                previous_ids = current_ids

            except Exception as e:
                logger.error(f"Hotplug loop error: {e}")

            time.sleep(3)

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _classify_by_name_and_vid(self, name: str, vid: Optional[str]) -> DeviceClass:
        """Classify device by name keywords and vendor ID"""
        name_lower = (name or '').lower()

        if any(w in name_lower for w in ['storage', 'flash', 'disk', 'drive', 'card', 'pendrive']):
            return DeviceClass.STORAGE
        if any(w in name_lower for w in ['audio', 'headphone', 'headset', 'speaker', 'microphone', 'sound']):
            return DeviceClass.AUDIO
        if any(w in name_lower for w in ['keyboard', 'mouse', 'hid', 'input']):
            return DeviceClass.HID
        if any(w in name_lower for w in ['network', 'ethernet', 'wifi', 'wlan', 'adapter']):
            return DeviceClass.NETWORK
        if any(w in name_lower for w in ['camera', 'webcam', 'imaging']):
            return DeviceClass.CAMERA
        if any(w in name_lower for w in ['android', 'iphone', 'phone', 'mtp', 'adb']):
            return DeviceClass.SMARTPHONE
        if any(w in name_lower for w in ['print']):
            return DeviceClass.PRINTER

        # VID-based
        if vid:
            if vid in ('18d1', '0e8d', '2717', '04e8', '0bb4', '12d1', '05ac'):
                return DeviceClass.SMARTPHONE
            if vid in ('0781', '058f', '13fe', '0951', '8564', '14cd'):
                return DeviceClass.STORAGE
            if vid in ('0d8c', '08bb'):
                return DeviceClass.AUDIO
            if vid in ('0bda', '0b95'):
                return DeviceClass.NETWORK

        return DeviceClass.UNKNOWN

    def _get_windows_removable_drives(self) -> List[str]:
        """Get drive letters of removable USB drives on Windows"""
        drives = []
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i in range(26):
                if bitmask & (1 << i):
                    drive = f"{chr(65 + i)}:\\"
                    dtype = ctypes.windll.kernel32.GetDriveTypeW(drive)
                    if dtype == 2:  # DRIVE_REMOVABLE
                        drives.append(drive)
        except Exception:
            pass
        return drives

    def _find_linux_mount(self, sysfs_name: str) -> Optional[str]:
        """Find mount point for a Linux USB storage device"""
        try:
            import psutil
            for partition in psutil.disk_partitions():
                if 'removable' in partition.opts or 'usb' in partition.device.lower():
                    return partition.mountpoint
        except Exception:
            pass
        return None

    def _get_local_ip(self) -> Optional[str]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

    def _resolve_hostname(self, ip: str) -> Optional[str]:
        try:
            return socket.gethostbyaddr(ip)[0]
        except Exception:
            return None

    def _get_mac_address(self, ip: str) -> Optional[str]:
        """Get MAC from ARP cache"""
        try:
            if self._system == 'Windows':
                out = subprocess.check_output(['arp', '-a', ip], text=True, timeout=3)
            else:
                out = subprocess.check_output(['arp', ip], text=True, timeout=3)

            import re
            mac = re.search(r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}', out)
            return mac.group(0) if mac else None
        except Exception:
            return None

    def _persist_device(self, device: AttachedDevice, event: str):
        """Save device event to database"""
        try:
            from core.database import db
            import json
            db.execute(
                "INSERT INTO device_log (device_id, device_class, name, vendor_id, "
                "product_id, serial, mount_point, ip_address, mac_address, "
                "connected_at, event, risk_level, metadata) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    device.device_id, device.device_class.value, device.name,
                    device.vendor_id, device.product_id, device.serial,
                    device.mount_point, device.ip_address, device.mac_address,
                    device.connected_at or datetime.utcnow(), event,
                    device.risk_level, json.dumps(device.metadata)
                )
            )
        except Exception as e:
            logger.debug(f"Device persist error: {e}")


# Global singleton
device_monitor = DeviceMonitor()