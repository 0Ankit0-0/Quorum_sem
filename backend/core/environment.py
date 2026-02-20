"""
Environment Detection
Detects network connectivity, air-gap status, and system role
"""
import socket
import platform
import subprocess
from typing import Dict, Any, List, Optional
from enum import Enum
import psutil
from config.logging_config import get_logger

logger = get_logger(__name__)


class EnvironmentType(Enum):
    """Environment classification"""
    AIR_GAPPED = "air_gapped"
    LAN_CONNECTED = "lan_connected"
    INTERNET_CONNECTED = "internet_connected"


class SystemRole(Enum):
    """System role classification"""
    TERMINAL = "terminal"
    HUB = "hub"
    UNKNOWN = "unknown"


class EnvironmentDetector:
    """Detects system environment and network status"""
    
    def __init__(self):
        self.os_type = platform.system()
        self.hostname = socket.gethostname()
        self.detection_cache: Optional[Dict[str, Any]] = None
    
    def detect_all(self) -> Dict[str, Any]:
        """Perform complete environment detection"""
        if self.detection_cache:
            return self.detection_cache
        
        logger.info("Starting environment detection...")
        
        detection = {
            "os": self.os_type,
            "hostname": self.hostname,
            "environment_type": self._detect_environment_type(),
            "system_role": self._detect_system_role(),
            "network_interfaces": self._get_network_interfaces(),
            "connected_devices": self._detect_connected_devices(),
            "lan_nodes": self._scan_lan_nodes() if self._has_lan_access() else [],
            "usb_devices": self._detect_usb_devices(),
            "system_info": self._get_system_info()
        }
        
        self.detection_cache = detection
        logger.info(f"Environment detected: {detection['environment_type'].value}")
        
        return detection
    
    def _detect_environment_type(self) -> EnvironmentType:
        """Detect if system is air-gapped, LAN-only, or internet-connected"""
        # Check internet connectivity
        if self._has_internet_access():
            return EnvironmentType.INTERNET_CONNECTED
        
        # Check LAN connectivity
        if self._has_lan_access():
            return EnvironmentType.LAN_CONNECTED
        
        # No network connectivity
        return EnvironmentType.AIR_GAPPED
    
    def _has_internet_access(self) -> bool:
        """Check for internet connectivity"""
        test_hosts = [
            ("8.8.8.8", 53),  # Google DNS
            ("1.1.1.1", 53),  # Cloudflare DNS
        ]
        
        for host, port in test_hosts:
            try:
                socket.create_connection((host, port), timeout=3)
                logger.debug(f"Internet access confirmed via {host}")
                return True
            except (socket.timeout, socket.error):
                continue
        
        logger.debug("No internet access detected")
        return False
    
    def _has_lan_access(self) -> bool:
        """Check for LAN connectivity"""
        try:
            interfaces = psutil.net_if_addrs()
            for interface_name, addresses in interfaces.items():
                for addr in addresses:
                    if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                        logger.debug(f"LAN access detected via {interface_name}: {addr.address}")
                        return True
        except Exception as e:
            logger.warning(f"LAN detection failed: {e}")
        
        return False
    
    def _detect_system_role(self) -> SystemRole:
        """Detect if system is a terminal node or admin hub"""
        try:
            # Hub indicators: multiple network interfaces, higher CPU/RAM, running services
            network_count = len(self._get_active_interfaces())
            total_ram = psutil.virtual_memory().total / (1024**3)  # GB
            cpu_count = psutil.cpu_count()
            
            # Simple heuristic
            if network_count > 1 and (total_ram > 16 or cpu_count > 8):
                return SystemRole.HUB
            elif network_count == 1 or total_ram < 8:
                return SystemRole.TERMINAL
            
            return SystemRole.UNKNOWN
            
        except Exception as e:
            logger.warning(f"System role detection failed: {e}")
            return SystemRole.UNKNOWN
    
    def _get_network_interfaces(self) -> List[Dict[str, Any]]:
        """Get all network interfaces with details"""
        interfaces = []
        
        try:
            net_if = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for interface_name, addresses in net_if.items():
                interface_info = {
                    "name": interface_name,
                    "addresses": [],
                    "is_up": stats[interface_name].isup if interface_name in stats else False
                }
                
                for addr in addresses:
                    if addr.family == socket.AF_INET:
                        interface_info["addresses"].append({
                            "type": "IPv4",
                            "address": addr.address,
                            "netmask": addr.netmask
                        })
                    elif addr.family == socket.AF_INET6:
                        interface_info["addresses"].append({
                            "type": "IPv6",
                            "address": addr.address
                        })
                
                interfaces.append(interface_info)
        
        except Exception as e:
            logger.warning(f"Network interface detection failed: {e}")
        
        return interfaces
    
    def _get_active_interfaces(self) -> List[str]:
        """Get list of active network interfaces"""
        active = []
        try:
            stats = psutil.net_if_stats()
            for interface, stat in stats.items():
                if stat.isup and not interface.startswith('lo'):
                    active.append(interface)
        except Exception as e:
            logger.warning(f"Active interface detection failed: {e}")
        
        return active
    
    def _detect_connected_devices(self) -> List[Dict[str, Any]]:
        """Detect connected storage devices"""
        devices = []
        
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:
                device_info = {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "opts": partition.opts
                }
                devices.append(device_info)
        
        except Exception as e:
            logger.warning(f"Device detection failed: {e}")
        
        return devices
    
    def _detect_usb_devices(self) -> List[Dict[str, Any]]:
        """Detect USB storage devices"""
        usb_devices = []
        
        try:
            if self.os_type == "Windows":
                # Windows: Check for removable drives
                partitions = psutil.disk_partitions()
                for partition in partitions:
                    if 'removable' in partition.opts.lower():
                        usb_devices.append({
                            "device": partition.device,
                            "mountpoint": partition.mountpoint,
                            "fstype": partition.fstype
                        })
            
            elif self.os_type == "Linux":
                # Linux: Check /sys/block for removable devices
                import os
                block_path = "/sys/block"
                if os.path.exists(block_path):
                    for device in os.listdir(block_path):
                        removable_file = f"{block_path}/{device}/removable"
                        if os.path.exists(removable_file):
                            with open(removable_file, 'r') as f:
                                if f.read().strip() == '1':
                                    usb_devices.append({"device": f"/dev/{device}"})
            
            elif self.os_type == "Darwin":  # macOS
                # macOS: Use diskutil
                result = subprocess.run(
                    ['diskutil', 'list', '-plist'],
                    capture_output=True,
                    text=True
                )
                # Parse plist output (simplified)
                # Full implementation would use plistlib
        
        except Exception as e:
            logger.warning(f"USB detection failed: {e}")
        
        logger.info(f"Detected {len(usb_devices)} USB device(s)")
        return usb_devices
    
    def _scan_lan_nodes(self) -> List[Dict[str, str]]:
        """Scan for other nodes on LAN (basic implementation)"""
        nodes = []
        
        try:
            # Get local IP and subnet
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            # Basic ping sweep (simplified - full implementation would use nmap or scapy)
            subnet = '.'.join(local_ip.split('.')[:-1])
            
            logger.info(f"Scanning subnet {subnet}.0/24 (limited scan)")
            
            # Scan only first 10 IPs for demonstration
            for i in range(1, 11):
                ip = f"{subnet}.{i}"
                if ip == local_ip:
                    continue
                
                try:
                    socket.create_connection((ip, 445), timeout=0.5)  # Try SMB port
                    nodes.append({"ip": ip, "reachable": True})
                except (socket.timeout, socket.error):
                    pass
        
        except Exception as e:
            logger.warning(f"LAN scan failed: {e}")
        
        logger.info(f"Found {len(nodes)} LAN node(s)")
        return nodes
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                "platform": platform.platform(),
                "processor": platform.processor(),
                "architecture": platform.machine(),
                "cpu_count": psutil.cpu_count(),
                "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "disk_total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2)
            }
        except Exception as e:
            logger.warning(f"System info collection failed: {e}")
            return {}
    
    def is_air_gapped(self) -> bool:
        """Check if environment is air-gapped"""
        env = self.detect_all()
        return env["environment_type"] == EnvironmentType.AIR_GAPPED
    
    def has_lan(self) -> bool:
        """Check if LAN access is available"""
        env = self.detect_all()
        return env["environment_type"] in [
            EnvironmentType.LAN_CONNECTED,
            EnvironmentType.INTERNET_CONNECTED
        ]


# Global environment detector instance
env_detector = EnvironmentDetector()