# Deployment Guide

---

## Prerequisites

| Requirement | Version | Notes |
|------------|---------|-------|
| Python | 3.11+ (3.14 recommended) | `python --version` |
| Node.js | 18+ | For frontend build |
| FFmpeg | 6.x+ | In PATH |
| MediaMTX | 1.x | Binary in `infrastructure/mediamtx/` |
| Git | Any | For source control |
| OpenCV | 4.x | Via pip |
| YOLOv8n weights | `yolov8n.pt` | In project root |

---

## Single-Node Windows Setup (Current Dev)

### Step 1 — Clone and Install

```powershell
cd C:\Users\dell\Projects
# (already cloned as IBVAP)

# Install Python dependencies
C:\Python314\python.exe -m pip install -r requirements\base.txt

# Install frontend dependencies
cd apps\frontend
npm install
cd ..\..
```

### Step 2 — Environment Configuration

```powershell
copy .env.example .env
# Edit .env with your actual values:
#   IBVAP_JWT_SECRET=<generate a 256-bit random string>
#   CORS_ALLOWED_ORIGINS=["http://localhost:5173"]
```

### Step 3 — Start All Services

```powershell
# One-command demo start:
.\scripts\ibvap.ps1 demo

# Or start individually:
.\scripts\ibvap.ps1 start-mediamtx
.\scripts\ibvap.ps1 start-ffmpeg
.\scripts\ibvap.ps1 start-backend
.\scripts\ibvap.ps1 start-frontend
.\scripts\ibvap.ps1 start-inference
```

### Step 4 — Verify

```powershell
.\scripts\ibvap.ps1 status
# All services should show RUNNING

# Run tests:
C:\Python314\python.exe -m pytest tests/ -v

# Check health:
Invoke-RestMethod http://localhost:8000/health/live
Invoke-RestMethod http://localhost:8000/health/ready
```

### Step 5 — Access Dashboard

- Dashboard: http://localhost:5173
- API docs: http://localhost:8000/docs
- RTSP stream: rtsp://localhost:8554/CAM-01

---

## Phone Camera Integration

```powershell
# Verify phone is on same network:
Invoke-WebRequest http://10.63.26.249:8080/video -Method Head

# Phone stream is auto-proxied via:
# GET http://localhost:8000/api/v1/stream/phone
```

---

## Production Deployment (Linux Recommended)

> ⚠️ This section describes the recommended path — not yet validated on production hardware.

### Recommended Stack

```
nginx (TLS termination + reverse proxy)
  → uvicorn (FastAPI, multiple workers)
  → SQLite (dev) / PostgreSQL (production)
  → Redis (future: alert queue, session store)
MediaMTX (RTSP gateway, dedicated process)
FFmpeg (camera relay processes)
Inference Worker (one per camera or GPU-batched)
```

### Docker (PLANNED — template only)

```bash
# Template docker-compose is at deployment/single_node/docker-compose.yml
# Edit environment variables before use
docker compose up -d
```

### Database Migration to PostgreSQL

```python
# In apps/backend/database/connection.py:
# Change DATABASE_URL from sqlite+aiosqlite:/// to postgresql+asyncpg://
# Run: alembic upgrade head
```

### TLS / HTTPS

```nginx
# nginx.conf example
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/ibvap.crt;
    ssl_certificate_key /etc/ssl/ibvap.key;
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

---

## Stopping Services

```powershell
.\scripts\ibvap.ps1 stop
# Or individually:
Stop-Process -Name mediamtx -Force
Stop-Process -Name ffmpeg -Force
# Kill Python processes by port
Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }
```

---

## Backup and Restore

```powershell
# Backup database and evidence:
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item data\ibvap_dev.db "backups\ibvap_$timestamp.db"
Compress-Archive data\evidence "backups\evidence_$timestamp.zip"

# Restore:
Copy-Item "backups\ibvap_20260905_120000.db" data\ibvap_dev.db
```

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `IBVAP_JWT_SECRET` | `""` | JWT signing secret (required for auth) |
| `APP_ENV` | `development` | `development` or `production` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/ibvap_dev.db` | Database connection string |
| `CORS_ALLOWED_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins |
| `API_VERSION` | `1.0.0` | API version string |
