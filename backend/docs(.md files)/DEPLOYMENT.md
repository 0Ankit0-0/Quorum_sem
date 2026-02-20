# Deployment Guide

## Development Deployment

### 1. Setup Development Environment
```bash
# Clone repository
git clone <repo-url>
cd quorum

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt --break-system-packages

# Copy environment template
cp .env.example .env

# Initialize
python main.py init
```

### 2. Run Development Server

**CLI Mode**:
```bash
python main.py status
python main.py ingest file sample.evtx
python main.py analyze run
```

**API Mode**:
```bash
# Start API server
python -m api.main

# Or with auto-reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Load Sample Data
```bash
# Download sample logs (if available)
wget https://example.com/sample-logs.zip
unzip sample-logs.zip

# Ingest
python main.py ingest directory ./sample-logs --recursive

# Analyze
python main.py analyze run --algorithm ensemble
```

## Production Deployment

### Option 1: Standalone Executable (Recommended)

**Using PyInstaller**:
```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile \
  --name quorum \
  --add-data "data:data" \
  --hidden-import duckdb \
  --hidden-import sklearn \
  main.py

# Output: dist/quorum
```

**Distribution**:
1. Package `dist/quorum` with `data/` directory
2. Create USB installer
3. Distribute to air-gapped systems

### Option 2: Docker Container

**Dockerfile**:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p data/databases data/models data/keys

# Initialize
RUN python main.py init

# Expose API port
EXPOSE 8000

# Run API server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and Run**:
```bash
# Build
docker build -t quorum:latest .

# Run CLI
docker run -it --rm -v $(pwd)/data:/app/data quorum:latest python main.py status

# Run API
docker run -d -p 8000:8000 -v $(pwd)/data:/app/data quorum:latest
```

### Option 3: System Service (Linux)

**systemd service** (`/etc/systemd/system/quorum.service`):
```ini
[Unit]
Description=Quorum API Service
After=network.target

[Service]
Type=simple
User=quorum
WorkingDirectory=/opt/quorum
Environment="PATH=/opt/quorum/venv/bin"
ExecStart=/opt/quorum/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

**Setup**:
```bash
# Create user
sudo useradd -r -s /bin/false quorum

# Install to /opt
sudo cp -r quorum /opt/
sudo chown -R quorum:quorum /opt/quorum

# Enable service
sudo systemctl enable quorum
sudo systemctl start quorum
sudo systemctl status quorum
```

## Air-Gapped Deployment

### 1. Prepare Offline Package

**On Internet-connected system**:
```bash
# Create directory
mkdir quorum-offline
cd quorum-offline

# Download dependencies
pip download -r requirements.txt -d ./packages

# Package application
cp -r ../quorum ./app

# Create installer script
cat > install.sh << 'EOF'
#!/bin/bash
pip install --no-index --find-links=./packages -r requirements.txt
cd app
python main.py init
EOF

chmod +x install.sh

# Create archive
cd ..
tar -czf quorum-offline.tar.gz quorum-offline/
```

### 2. Transfer to Air-Gapped System

- Copy `quorum-offline.tar.gz` to USB drive
- Transfer to target system
- Extract and run installer

### 3. Install on Air-Gapped System
```bash
# Extract
tar -xzf quorum-offline.tar.gz
cd quorum-offline

# Install
./install.sh

# Verify
cd app
python main.py status
```

## Configuration for Different Environments

### High-Security Environment
```env
# Disable API (CLI only)
# Comment out API startup in main.py

# Minimal logging
LOG_LEVEL=WARNING

# Restrict database
DB_MEMORY=False
DB_MAX_MEMORY=2GB
```

### High-Performance Environment
```env
# Maximize resources
DB_THREADS=16
DB_MAX_MEMORY=16GB
BATCH_SIZE=100000
AI_N_JOBS=-1

# API workers
API_WORKERS=8
```

### Resource-Constrained Environment
```env
# Minimize resource usage
DB_THREADS=2
DB_MAX_MEMORY=1GB
BATCH_SIZE=5000
AI_N_JOBS=2
```

## Health Monitoring

### Check System Health
```bash
# CLI
python main.py status

# API
curl http://localhost:8000/system/health
```

### Log Monitoring
```bash
# Tail logs
tail -f logs/quorum.log

# Parse JSON logs
tail -f logs/quorum.log | jq .
```

### Database Maintenance
```bash
# Check size
ls -lh data/databases/quorum.duckdb

# Backup
cp data/databases/quorum.duckdb data/databases/quorum_backup_$(date +%Y%m%d).duckdb

# Compact (run in Python)
python -c "
from core.database import db
db.execute('VACUUM')
"
```

## Scaling Considerations

### Vertical Scaling

- Increase RAM allocation
- More CPU cores
- Faster storage (SSD/NVMe)

### Horizontal Scaling

For multiple systems:

1. **Central Hub**: Aggregates results
2. **Terminal Nodes**: Local analysis
3. **Shared Storage**: Network file system (if LAN available)

## Security Hardening

### File Permissions
```bash
# Restrict access
chmod 700 data/keys
chmod 600 data/keys/*.pem

# Database
chmod 600 data/databases/*.duckdb
```

### Network Isolation
```bash
# Firewall rules (if needed)
sudo ufw deny 8000/tcp  # Block API in air-gap mode
```

### Audit Logging

Enable comprehensive logging:
```env
LOG_LEVEL=DEBUG
LOG_FORMAT=json
```

## Backup Strategy

### Automated Backup Script
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/quorum"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
cp data/databases/quorum.duckdb "$BACKUP_DIR/quorum_$DATE.duckdb"

# Backup reports
tar -czf "$BACKUP_DIR/reports_$DATE.tar.gz" reports_output/

# Keep last 7 days
find "$BACKUP_DIR" -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

### Restore
```bash
# Restore database
cp /backup/quorum/quorum_20250216.duckdb data/databases/quorum.duckdb

# Restart services
sudo systemctl restart quorum
```

## Update Deployment

### Distributing Updates

1. Create update package on secure system
2. Sign with private key
3. Transfer to USB
4. Distribute to air-gapped systems
5. Verify and apply

### Rolling Updates

For multiple systems:
```bash
# Test on one system first
python main.py update verify update.qup
python main.py update apply update.qup

# If successful, deploy to others
```

## Troubleshooting Deployment

### Permission Errors
```bash
# Fix ownership
sudo chown -R $(whoami):$(whoami) quorum/

# Fix permissions
chmod -R 755 quorum/
chmod 600 quorum/data/keys/*.pem
```

### Port Already in Use
```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn api.main:app --port 8001
```

### Database Lock
```bash
# Remove lock file
rm data/databases/quorum.duckdb.wal

# Restart application
```

## Performance Tuning

### Database Optimization
```sql
-- Add indexes
CREATE INDEX idx_logs_timestamp ON logs(timestamp);
CREATE INDEX idx_anomalies_score ON anomalies(anomaly_score);

-- Vacuum
VACUUM;

-- Analyze
ANALYZE;
```

### Memory Tuning

Monitor memory usage:
```bash
# Check memory
free -h

# Monitor Python process
top -p $(pgrep -f "python main.py")
```

Adjust settings based on available RAM.

---

**End of Deployment Guide**