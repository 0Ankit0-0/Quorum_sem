# Quorum v1.1.0 — Full Upgrade Notes
## Features: Real-Time Streaming + Device Scanning + Multi-Node Hub Aggregation

---

## Files Delivered in This Package

```
upgrades/
├── UPGRADE_NOTES_v110.md               ← this file
│
├── models/
│   └── node.py                         NEW — QuorumNode, AttachedDevice, SyncPackage
│
├── core/
│   ├── device_monitor.py               NEW — USB hotplug, VID/PID classifier, LAN ping
│   ├── realtime_monitor.py             NEW — tail -f engine, SSE queue, quick scorer
│   └── database_additions.py           NEW — SQL for 5 new tables
│
├── services/
│   ├── hub_service.py                  NEW — node registry, sync export/import, correlations
│   ├── analysis_service.py             UPD — ensemble default, realistic scoring
│   ├── report_service.py               UPD — session folders, 4 graph types
│   └── log_service.py                  UPD — scan/collect system logs, USB scan
│
├── ai_engine/
│   ├── ensemble.py                     UPD — hybrid 4-component weighted ensemble
│   └── feature_extractor.py            UPD — 12 → 20 features, keyword risk
│
├── api/routes/
│   ├── hub.py                          NEW — /hub/* aggregation endpoints
│   ├── devices.py                      NEW — /devices/* scan endpoints
│   └── stream.py                       NEW — /stream/logs SSE endpoint
│
└── cli/
    ├── main.py                         UPD — registers monitor, hub, devices
    └── commands/
        ├── monitor.py                  NEW — quorum monitor watch/status
        ├── hub.py                      NEW — quorum hub register/export/import/…
        ├── devices.py                  NEW — quorum devices scan/watch/history/…
        ├── ingest.py                   UPD — scan + collect commands
        ├── analyze.py                  UPD — ensemble default, color output
        └── report.py                   UPD — session folder listing
```

---

## Step-by-Step Installation

### 1. Copy Files Into Your Project

| From upgrades/          | To backend/                    |
|-------------------------|--------------------------------|
| models/node.py          | models/node.py                 |
| core/device_monitor.py  | core/device_monitor.py         |
| core/realtime_monitor.py| core/realtime_monitor.py       |
| core/database_additions.py | core/database_additions.py  |
| services/hub_service.py | services/hub_service.py        |
| services/analysis_service.py | services/analysis_service.py |
| services/report_service.py | services/report_service.py  |
| services/log_service.py | services/log_service.py        |
| ai_engine/ensemble.py   | ai_engine/ensemble.py          |
| ai_engine/feature_extractor.py | ai_engine/feature_extractor.py |
| api/routes/hub.py       | api/routes/hub.py              |
| api/routes/devices.py   | api/routes/devices.py          |
| api/routes/stream.py    | api/routes/stream.py           |
| cli/main.py             | cli/main.py                    |
| cli/commands/monitor.py | cli/commands/monitor.py        |
| cli/commands/hub.py     | cli/commands/hub.py            |
| cli/commands/devices.py | cli/commands/devices.py        |
| cli/commands/ingest.py  | cli/commands/ingest.py         |
| cli/commands/analyze.py | cli/commands/analyze.py        |
| cli/commands/report.py  | cli/commands/report.py         |

### 2. Register New API Routes

In `api/main.py`, add these 3 lines in the router registration section:

```python
from api.routes.hub     import router as hub_router
from api.routes.devices import router as devices_router
from api.routes.stream  import router as stream_router

app.include_router(hub_router)
app.include_router(devices_router)
app.include_router(stream_router)
```

### 3. Delete Old Trained Models (Required!)

The new ensemble uses different feature dimensions (20 vs 12).
Old .pkl models will crash. Delete them:

```cmd
del backend\data\models\isolation_forest.pkl
del backend\data\models\one_class_svm.pkl
del backend\data\models\statistical.pkl
```

### 4. Re-initialize (applies new DB schema)

```cmd
python main.py init
```

This will:
- Create 5 new database tables (node_registry, hub_anomalies,
  node_sync_log, device_log, stream_sessions)
- Register this machine as a Quorum node
- Keep all existing logs and anomalies intact

### 5. Install Optional Dependency

Device monitoring uses psutil (already in requirements.txt).
Verify it's installed:

```cmd
pip install psutil --break-system-packages
```

---

## Complete New Command Reference

### Real-Time Log Monitoring

```cmd
# Watch specific files (live tail with AI scoring)
python main.py monitor watch C:\logs\Security.log

# Auto-discover and watch all system logs
python main.py monitor watch --auto

# Filter: only show HIGH+ severity, score >= 0.70
python main.py monitor watch --auto --severity HIGH --threshold 0.70

# Watch Linux auth log
python main.py monitor watch /var/log/auth.log /var/log/syslog

# Monitor status
python main.py monitor status
```

**What you see:**
```
TIME       SEV        SCORE   SOURCE             MESSAGE
────────────────────────────────────────────────────────────────────────────────
14:32:01   HIGH       0.780   sshd               Failed password for invalid user
14:32:03   CRITICAL   0.952   sshd               Failed password for invalid user
14:32:05   MEDIUM     0.601   sudo               gaura : TTY=pts/0 ; USER=root
14:32:10   INFO       0.201   CRON               (root) CMD (/usr/local/bin/backup)
```

**SSE API (for frontend later):**
```
curl -N "http://localhost:8000/stream/logs?min_score=0.70&severity=HIGH"
```

---

### Device Scanning

```cmd
# Full scan: USB devices + LAN nodes
python main.py devices scan

# USB only (no network scan)
python main.py devices scan --usb-only

# JSON output
python main.py devices scan --json

# Watch for hotplug events (real-time connect/disconnect)
python main.py devices watch

# Only alert on new/risky devices
python main.py devices watch --alert-only

# View device connection history
python main.py devices history

# Scan USB storage devices for log files
python main.py devices scan-logs

# Scan specific mount points and auto-ingest
python main.py devices scan-logs D:\ E:\ --ingest
```

**What scan detects:**

| Device Type | Example | Risk Level |
|-------------|---------|------------|
| STORAGE | SanDisk USB drive, SD card | HIGH |
| AUDIO | USB headphones, microphone | MEDIUM |
| HID | Keyboard, mouse | LOW |
| NETWORK | USB Ethernet adapter | HIGH |
| SMARTPHONE | Android (MTP), iPhone | HIGH |
| LAN_NODE | Any machine on subnet | INFO |

**Device watch output:**
```
TIME       EVENT          CLASS        NAME                           RISK
────────────────────────────────────────────────────────────────────────────────
14:45:12   CONNECTED      STORAGE      SanDisk Cruzer Blade           [HIGH]
           VID:PID: 0781:5567  Serial: 4C530001140516116282
14:46:33   CONNECTED      AUDIO        USB Headset                    [MEDIUM]
14:47:01   DISCONNECTED   STORAGE      SanDisk Cruzer Blade           [HIGH]
```

---

### Hub Aggregation

```cmd
# Register this machine
python main.py hub register --role terminal   # on analyst workstation
python main.py hub register --role hub        # on central admin machine

# List all known nodes
python main.py hub nodes

# === On TERMINAL node ===
# Export local results as signed package
python main.py hub export
# Output: data/sync_<node-id>_<timestamp>.qsp
# Copy .qsp file to USB → carry to hub

# === On HUB node ===
# Scan USB for packages and auto-import
python main.py hub scan-usb

# Manually import a package
python main.py hub import data\sync_abc123_20260217.qsp

# View aggregated dashboard
python main.py hub dashboard

# Find attacks across multiple nodes
python main.py hub correlate
```

**Hub dashboard output:**
```
Per-Node Threat Summary:
Node          Total  Critical  High  Avg Score  Last Sync
──────────────────────────────────────────────────────────
DESKTOP-A1B2  42     5         12    0.743      2026-02-17 10:52
LAPTOP-C3D4   18     2         6     0.681      2026-02-17 09:30
WORKST-E5F6   7      0         2     0.512      2026-02-16 18:00

Aggregated Severity:
  CRITICAL   7   ███████
  HIGH       20  ████████████████████
  MEDIUM     28  ████████████████████████████
  LOW        12  ████████████
```

**Cross-node correlation output:**
```
[CRITICAL] T1110.001 — credential_access
  Nodes affected:  3 (DESKTOP-A1B2,LAPTOP-C3D4,WORKST-E5F6)
  Total hits:      27
  Avg score:       0.924
  First seen:      2026-02-16 12:14:10
  Last seen:       2026-02-17 10:52:00
```
→ This means the SAME brute-force technique was detected on 3 machines —
  likely a coordinated attack.

---

## Architecture Overview (Updated)

```
                    ┌─────────────────────────────────────┐
                    │         QUORUM v1.1.0               │
                    │                                     │
  Physical World    │  ┌──────────────────────────────┐   │
  ───────────────   │  │   Device Monitor             │   │
  USB Drive    ──→  │  │   • USB VID/PID classifier   │   │
  Headphones   ──→  │  │   • Hotplug detection        │   │
  Keyboard     ──→  │  │   • LAN node discovery       │   │
  LAN machine  ──→  │  │   • Risk assessment          │   │
                    │  └──────────┬───────────────────┘   │
                    │             │                        │
  Log Files         │  ┌──────────▼───────────────────┐   │
  ───────────────   │  │   Real-Time Monitor          │   │
  Security.evtx ──→ │  │   • tail -f engine           │   │
  auth.log      ──→ │  │   • Quick keyword scorer     │   │
  syslog        ──→ │  │   • SSE event queue          │   │
                    │  └──────────┬───────────────────┘   │
                    │             │                        │
                    │  ┌──────────▼───────────────────┐   │
                    │  │   Hybrid AI Engine           │   │
                    │  │   • Isolation Forest (35%)   │   │
                    │  │   • One-Class SVM (25%)      │   │
                    │  │   • Statistical Z-score (20%)│   │
                    │  │   • Keyword Engine (20%)     │   │
                    │  └──────────┬───────────────────┘   │
                    │             │                        │
                    │  ┌──────────▼───────────────────┐   │
                    │  │   Hub Service                │   │
                    │  │   • Node registry            │   │
                    │  │   • USB sync packages (.qsp) │   │
                    │  │   • Cross-node correlation   │   │
                    │  │   • MITRE ATT&CK heatmap     │   │
                    │  └──────────────────────────────┘   │
                    └─────────────────────────────────────┘
```

---

## New Database Tables

```sql
node_registry     -- Registered Quorum nodes (terminal/hub)
node_sync_log     -- History of all sync operations
hub_anomalies     -- Aggregated anomalies from all nodes
device_log        -- Every device connect/disconnect event
stream_sessions   -- Real-time monitoring session history
```

---

## Blackbook Updates

### Features Implemented (remove from Future Scope):
- ✅ Real-time log streaming (tail -f with AI scoring)
- ✅ USB device scanning (storage, audio, HID, smartphones)
- ✅ LAN-connected device discovery
- ✅ Device classification by USB VID/PID
- ✅ Multi-node hub aggregation
- ✅ Cross-node attack correlation
- ✅ Sync package export/import (USB transfer)
- ✅ MITRE ATT&CK heatmap across nodes

### Remaining Future Scope (still valid):
- ⏳ NLP/LLM-based log parsing
- ⏳ Graph database for attack path visualization
- ⏳ Mobile alert companion app
- ⏳ Differential privacy for shared threat intel
- ⏳ Automated incident response playbooks
- ⏳ Hardware security key (FIDO2) for node auth

### Limitations Removed:
- ❌ ~~"No real-time monitoring"~~ → monitor watch --auto
- ❌ ~~"Manual file ingestion only"~~ → devices scan + collect
- ❌ ~~"Single machine only"~~ → hub aggregation
- ❌ ~~"No physical security awareness"~~ → device monitor

---

## Verification After Installation

```cmd
python main.py init
python main.py status
python main.py devices scan
python main.py monitor watch --auto
# (in another terminal)
python main.py hub register
python main.py hub dashboard
```

Expected output after `python main.py status`:
```
  Database:
    Logs:           45
    Anomalies:      12
    Sessions:       3
    Hub Nodes:      1
    Hub Anomalies:  0

  Real-Time Monitor:
    Status:   RUNNING
    Files:    4
    Lines:    0
    Alerts:   0

  Environment:
    Status:   internet_connected
    Role:     terminal
    OS:       Windows

✓ System operational
```