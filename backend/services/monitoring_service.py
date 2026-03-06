"""
Monitoring Service
Persistent singleton system monitor with in-memory cache and tmp disk flush.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime
import json
from pathlib import Path
import threading
import time
from typing import Any, Deque, Dict, List, Optional

import psutil

from config.settings import settings
from config.logging_config import get_logger

logger = get_logger(__name__)


class MonitoringService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._state_lock = threading.RLock()
        self._samples: Deque[Dict[str, Any]] = deque(maxlen=3600)
        self._status: Dict[str, Any] = {
            "running": False,
            "started_at": None,
            "last_sample_at": None,
            "samples": 0,
        }
        self._tmp_dir = settings.DATA_DIR / "tmp"
        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        self._runtime_file = self._tmp_dir / "monitor_runtime.jsonl"
        self._prev_disk = None
        self._prev_net = None
        self._device_events: Deque[Dict[str, Any]] = deque(maxlen=500)

    def register_device_event(self, device_name: str, event: str, device_class: str) -> None:
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "device_name": device_name,
            "event": event,
            "device_class": device_class,
        }
        with self._state_lock:
            self._device_events.append(payload)

    def start(self) -> Dict[str, Any]:
        with self._state_lock:
            if self._running:
                return self.status()
            self._running = True
            self._status["running"] = True
            self._status["started_at"] = datetime.utcnow().isoformat()
            self._thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="QuorumSystemMonitor",
            )
            self._thread.start()
            logger.info("Monitoring service started")
            return self.status()

    def stop(self) -> Dict[str, Any]:
        with self._state_lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        with self._state_lock:
            self._status["running"] = False
        logger.info("Monitoring service stopped")
        return self.status()

    def status(self) -> Dict[str, Any]:
        with self._state_lock:
            return dict(self._status)

    def snapshot(self, limit: int = 120) -> Dict[str, Any]:
        with self._state_lock:
            samples = list(self._samples)[-limit:]
            events = list(self._device_events)[-limit:]
            return {
                "status": dict(self._status),
                "samples": samples,
                "device_events": events,
            }

    def _run_loop(self) -> None:
        self._prev_disk = psutil.disk_io_counters()
        self._prev_net = psutil.net_io_counters()

        while True:
            with self._state_lock:
                if not self._running:
                    break
            try:
                sample = self._collect_sample()
                with self._state_lock:
                    self._samples.append(sample)
                    self._status["samples"] = len(self._samples)
                    self._status["last_sample_at"] = sample["timestamp"]
                self._append_to_disk(sample)
            except Exception as exc:
                logger.error(f"Monitoring collection error: {exc}")
            time.sleep(1)

    def _collect_sample(self) -> Dict[str, Any]:
        ts = datetime.utcnow().isoformat()

        cpu = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        disk = psutil.disk_io_counters()
        net = psutil.net_io_counters()

        disk_read_bps = 0.0
        disk_write_bps = 0.0
        net_recv_bps = 0.0
        net_send_bps = 0.0
        if self._prev_disk:
            disk_read_bps = float(disk.read_bytes - self._prev_disk.read_bytes)
            disk_write_bps = float(disk.write_bytes - self._prev_disk.write_bytes)
        if self._prev_net:
            net_recv_bps = float(net.bytes_recv - self._prev_net.bytes_recv)
            net_send_bps = float(net.bytes_sent - self._prev_net.bytes_sent)

        self._prev_disk = disk
        self._prev_net = net

        return {
            "timestamp": ts,
            "cpu_percent": cpu,
            "memory_percent": vm.percent,
            "memory_used_bytes": int(vm.used),
            "memory_total_bytes": int(vm.total),
            "disk_read_bps": max(disk_read_bps, 0.0),
            "disk_write_bps": max(disk_write_bps, 0.0),
            "network_recv_bps": max(net_recv_bps, 0.0),
            "network_send_bps": max(net_send_bps, 0.0),
        }

    def _append_to_disk(self, sample: Dict[str, Any]) -> None:
        with self._runtime_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sample) + "\n")


monitoring_service = MonitoringService()

