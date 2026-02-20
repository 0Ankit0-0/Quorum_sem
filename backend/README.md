# Project Quorum

AI-Powered Log Analysis for Secure Offline Environments

## Overview

Project Quorum is a self-contained forensic analysis platform designed for air-gapped and offline environments. It provides AI-driven threat detection, deep forensic capabilities, and log analysis without requiring internet connectivity.

## Features

- **Offline AI Analysis**: Embedded machine learning for anomaly detection
- **Multi-Format Support**: Windows EVTX and Linux Syslog parsing
- **MITRE ATT&CK Integration**: Automatic mapping of threats to ATT&CK framework
- **Secure Updates (SOUP)**: Cryptographically-signed offline update mechanism
- **Cross-Platform**: Windows, macOS, and Linux support
- **REST API**: FastAPI-based API for frontend integration
- **CLI Interface**: Full-featured command-line interface

## Architecture
```
quorum/
├── api/              # FastAPI REST API
├── ai_engine/        # ML models and anomaly detection
├── cli/              # Command-line interface
├── config/           # Configuration management
├── core/             # Core infrastructure (DB, security, environment)
├── models/           # Data models
├── parsers/          # Log parsers (EVTX, Syslog)
├── services/         # Business logic services
├── reports/          # Report generation
├── utils/            # Utilities
├── data/             # Data storage (databases, models, keys)
├── scripts/          # Setup and utility scripts
└── tests/            # Test suite
```

## Installation

### Prerequisites

- Python 3.9 or higher
- 8 GB RAM minimum (16 GB recommended)
- 10 GB free disk space

### Quick Start

1. **Clone the repository**
```bash
   git clone <repository-url>
   cd quorum
```

2. **Create virtual environment**
```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
   pip install -r requirements.txt --break-system-packages
```

4. **Initialize Quorum**
```bash
   python main.py init
```

## Usage

### CLI Commands

#### Ingest Logs
```bash
# Ingest a single log file
python main.py ingest file /path/to/logfile.evtx

# Ingest directory
python main.py ingest directory /path/to/logs --recursive

# Collect system logs automatically
python main.py ingest system
```

#### Run Analysis
```bash
# Run anomaly detection
python main.py analyze run --algorithm isolation_forest

# View results
python main.py analyze results <session-id>

# List anomalies
python main.py analyze anomalies --severity CRITICAL
```

#### Query Database
```bash
# Execute SQL query
python main.py query execute "SELECT * FROM logs WHERE severity='HIGH' LIMIT 10"

# View saved queries
python main.py query saved

# Query history
python main.py query history
```

#### Generate Reports
```bash
# Generate CSV report
python main.py report generate --type csv --session <session-id>

# Generate PDF report with graphs
python main.py report generate --type pdf --graphs

# List reports
python main.py report list
```

#### Manage Updates
```bash
# Scan for updates
python main.py update scan

# Verify update package
python main.py update verify /path/to/update.qup

# Apply update
python main.py update apply /path/to/update.qup

# Rollback
python main.py update rollback model
```

#### System Status
```bash
# Check system status
python main.py status

# Interactive mode
python main.py interactive
```

### API Server

Start the API server:
```bash
# Development
python -m api.main

# Production with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Access API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration

Edit `.env` file to customize settings:
```env
# Database
DB_THREADS=4
DB_MAX_MEMORY=4GB

# AI Engine
AI_ANOMALY_THRESHOLD=0.95
AI_CONTAMINATION=0.01

# API
API_PORT=8000
```

## AI Models

### Supported Algorithms

1. **Isolation Forest** (Default)
   - Fast, tree-based anomaly detection
   - Best for high-dimensional data
   - Low false positive rate

2. **One-Class SVM**
   - Support vector machine for novelty detection
   - Good for complex boundaries
   - Slower but more accurate

3. **Statistical Detection**
   - Z-score and IQR methods
   - Fast, interpretable results
   - Best for normally distributed data

4. **Ensemble**
   - Combines all algorithms
   - Highest accuracy
   - Slowest performance

### Model Training

Models are trained automatically during first analysis. To pre-train:
```python
from ai_engine.isolation_forest import IsolationForestDetector

detector = IsolationForestDetector()
detector.fit(training_data)
detector.save()
```

## SOUP (Secure Offline Update Protocol)

### Creating Update Packages

1. **Generate keys** (one-time):
```bash
   python scripts/generate_keys.py
```

2. **Create update package**:
```bash
   python scripts/create_update_package.py \
     --type model \
     --version 1.1.0 \
     --output update_v1.1.0.qup
```

3. **Distribute** package via USB or secure file transfer

4. **Apply** on target system:
```bash
   python main.py update apply update_v1.1.0.qup
```

### Update Types

- **model**: ML model updates
- **rules**: Detection rule updates
- **mitre**: MITRE ATT&CK data updates

## Environment Detection

Quorum automatically detects:

- **Network Status**: Air-gapped, LAN, or Internet
- **System Role**: Terminal node or admin hub
- **Connected Devices**: USB drives, external storage
- **LAN Nodes**: Other systems on local network

## Database Schema

### Main Tables

- **logs**: Parsed log entries
- **anomalies**: Detected anomalies
- **mitre_techniques**: MITRE ATT&CK techniques
- **analysis_sessions**: Analysis session metadata

### Querying
```sql
-- Recent critical anomalies
SELECT * FROM anomalies 
WHERE severity = 'CRITICAL' 
ORDER BY detected_at DESC 
LIMIT 10;

-- Logs by MITRE technique
SELECT l.*, a.mitre_technique_id 
FROM logs l 
JOIN anomalies a ON l.id = a.log_id 
WHERE a.mitre_technique_id IS NOT NULL;
```

## Reporting

### CSV Reports

- Flat structure
- Easy to import into Excel
- Contains: Score, Severity, Timestamp, Source, Event Type

### PDF Reports

- Executive summary
- Severity distribution charts
- Top anomalies table
- MITRE ATT&CK coverage
- Professional formatting

## Testing

Run tests:
```bash
# All tests
pytest

# Specific test
pytest tests/test_parsers.py

# With coverage
pytest --cov=. --cov-report=html
```

## Performance Optimization

### For Large Datasets (1M+ logs)

1. Increase database memory:
```env
   DB_MAX_MEMORY=8GB
```

2. Use more threads:
```env
   DB_THREADS=8
```

3. Increase batch size:
```env
   BATCH_SIZE=50000
```

### For Faster Analysis

1. Use Isolation Forest (fastest)
2. Reduce contamination rate
3. Filter by time range
4. Use specific event types

## Troubleshooting

### Common Issues

**Issue**: "python-evtx not installed"
- **Solution**: `pip install python-evtx --break-system-packages`

**Issue**: Database locked
- **Solution**: Close other Quorum instances, check `quorum.duckdb.wal`

**Issue**: Out of memory during analysis
- **Solution**: Reduce batch size, analyze smaller time ranges

**Issue**: Slow queries
- **Solution**: Add indexes, reduce result set, optimize WHERE clauses

### Logs

Check logs at:
- `logs/quorum.log` (JSON format)
- Console output (text format)

## Security Considerations

### Air-Gapped Operation

- No network calls in offline mode
- All dependencies bundled
- Local model training and inference

### SOUP Security

- RSA-2048 signatures
- SHA-256 integrity hashing
- Public key verification
- Tamper detection

### Best Practices

1. Keep private keys secure (offline, encrypted storage)
2. Verify all updates before applying
3. Maintain update logs
4. Regular backups of database
5. Use strong passwords for any authentication

## Contributing

This is a student project for academic purposes.

## License

Academic/Educational Use

## Project Information

- **Author**: Ankit Vishwakarma
- **Institution**: Shree L. R. Tiwari Degree College
- **Department**: Computer Science
- **Year**: 2025-26

## Support

For issues or questions:
- Check documentation
- Review logs
- Consult MITRE ATT&CK framework documentation

## Acknowledgments

- MITRE ATT&CK Framework
- scikit-learn community
- DuckDB team
- FastAPI framework
- python-evtx library