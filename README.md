# 🛡️ Project Quorum

**AI-Powered Log Analysis for Secure Offline Environments**

Project Quorum is a self-contained forensic analysis platform designed for air-gapped and offline environments. It provides AI-driven threat detection, deep forensic capabilities, and log analysis without requiring internet connectivity.

---

## ✨ Key Features

- **Offline AI Analysis**: Embedded machine learning (Isolation Forest, One-Class SVM) for anomaly detection.
- **Multi-Format Support**: Parse Windows EVTX and Linux Syslog entries natively.
- **MITRE ATT&CK Integration**: Automatic mapping of detected threats to the MITRE ATT&CK framework.
- **Secure Updates (SOUP)**: Cryptographically-signed offline update mechanism (RSA-2048 & SHA-256).
- **Cross-Platform Support**: Compatible with Windows, macOS, and Linux.
- **Modern User Interface**: Fast, responsive frontend built with React, TypeScript, and Vite.
- **Versatile Backend**: Full-featured Command-Line Interface (CLI) and a FastAPI-based REST API.

---

## 🏗️ Architecture & Tech Stack

This repository is structured as a monorepo containing both the frontend and backend applications.

### **Frontend** (`/frontend`)
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS / PostCSS
- **Desktop Packaging**: Tauri (available via `src-tauri`)

### **Backend** (`/backend`)
- **Core**: Python 3.9+
- **API Framework**: FastAPI
- **Database**: DuckDB (Optimized for fast, analytical queries)
- **Machine Learning**: Scikit-Learn
- **Log Parsing**: `python-evtx`

---

## 🚀 Getting Started

### Prerequisites
- **Python**: v3.9 or higher
- **Node.js**: v18 or higher (for the frontend)
- **Hardware**: Minimum 8 GB RAM (16 GB recommended), 10 GB free disk space

### 1. Clone the Repository
```bash
git clone [https://github.com/yourusername/quorum.git](https://github.com/yourusername/quorum.git)
cd quorum
```

### 2. Backend Setup
Navigate to the backend directory and set up the Python environment:
```bash
cd backend
python -m venv venv

# Activate virtual environment
# On Windows: venv\Scripts\activate
# On Linux/macOS: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt --break-system-packages

# Initialize Quorum Database & Environment
python main.py init
```

**Starting the Backend Server:**
```bash
# Start FastAPI server (Development)
python -m api.main

# Or run via CLI interface
python main.py interactive
```
*API Documentation will be available at: http://localhost:8000/docs*

### 3. Frontend Setup
Open a new terminal, navigate to the frontend directory, and start the Vite dev server:
```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```
*The frontend will typically run at: http://localhost:5173*

---

## 💻 CLI Usage

The backend comes with a powerful CLI for offline administrative tasks. Run these from the `/backend` directory:

**Ingest Logs**
```bash
python main.py ingest file /path/to/logfile.evtx
python main.py ingest directory /path/to/logs --recursive
```

**Run Analysis**
```bash
python main.py analyze run --algorithm isolation_forest
python main.py analyze anomalies --severity CRITICAL
```

**Generate Reports**
```bash
python main.py report generate --type pdf --graphs
```

---

## 🔒 Security Considerations

- **Air-Gapped Operation**: Quorum is designed to make zero network calls in offline mode. All dependencies are bundled, and model training/inference happens locally.
- **SOUP Security**: The Secure Offline Update Protocol ensures integrity using public key verification and tamper detection before applying any model or MITRE data updates.

---

## 🎓 Academic Project Information

This platform was developed as a student project for academic purposes.

- **Author**: Ankit Vishwakarma
- **Institution**: Shree L. R. Tiwari Degree College
- **Department**: Computer Science
- **Academic Year**: 2025-26

## 📜 License

This project is intended for **Academic/Educational Use**.

---
*Acknowledgments: MITRE ATT&CK Framework, scikit-learn community, DuckDB team, FastAPI framework, and python-evtx library.*
```
