# PetroFlow Docker Deployment Guide
## Phase 5 — Production-Ready Containerization

---

## Overview

PetroFlow is packaged as a **multi-container Docker application** consisting of:

| Container | Image | Role |
|---|---|---|
| `petroflow_app` | `petroflow:latest` (custom build) | Streamlit web application |
| `petroflow_mosquitto` | `eclipse-mosquitto:2.0` | MQTT broker for IoT telemetry |
| `petroflow_simulator` | `petroflow:latest` | Synthetic sensor data (dev only) |

### Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│              Docker Network: petroflow_net        │
│              Subnet: 172.28.0.0/24               │
│                                                  │
│  ┌─────────────────┐    ┌─────────────────────┐ │
│  │  petroflow_app  │    │ petroflow_mosquitto  │ │
│  │  172.28.0.20    │◄──►│  172.28.0.10        │ │
│  │  Port: 8501     │    │  Port: 1883 / 9001   │ │
│  └────────┬────────┘    └─────────────────────┘ │
│           │                                      │
└───────────┼──────────────────────────────────────┘
            │
   ┌────────┴───────────────────────────┐
   │         Named Volumes              │
   │  petroflow_data    → SQLite DB     │
   │  petroflow_logs    → Audit logs    │
   │  petroflow_storage → Uploads/3D    │
   │  mosquitto_data    → MQTT store    │
   └────────────────────────────────────┘
```

---

## Prerequisites

| Requirement | Minimum Version | Check |
|---|---|---|
| Docker Engine | 24.0+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| Available RAM | 2 GB | — |
| Available Disk | 5 GB | — |

---

## Quick Start (Development)

### 1. Clone / navigate to project

```bash
cd /path/to/Software
```

### 2. Copy and configure environment

```bash
cp .env.example .env
# Edit .env with your settings (especially SECRET_KEY)
```

### 3. Build and start

```bash
docker compose up --build
```

### 4. Access the application

Open your browser at: **http://localhost:8501**

### 5. Stop

```bash
docker compose down
```

---

## Step-by-Step First Setup

### Step 1 — Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and at minimum change:

```ini
# Generate a secure secret key:
# openssl rand -hex 32
SECRET_KEY=your_generated_secret_here

# Set your environment
APP_ENV=development

# MQTT settings (defaults work for local docker-compose)
MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=1883
```

### Step 2 — Build the Docker Image

```bash
# Standard build
docker compose build

# Force full rebuild (no cache)
docker compose build --no-cache

# Build only the app service
docker compose build app
```

**Expected build time**: 3–8 minutes on first build (downloading Python packages).
**Subsequent builds**: 30–90 seconds (Docker layer cache).

### Step 3 — Start Services

```bash
# Start all services (foreground)
docker compose up

# Start in background (detached)
docker compose up -d

# Start and rebuild if needed
docker compose up --build -d
```

### Step 4 — Verify Services are Healthy

```bash
# Check service status
docker compose ps

# Expected output:
# NAME                    STATUS              PORTS
# petroflow_app           running (healthy)   0.0.0.0:8501->8501/tcp
# petroflow_mosquitto     running (healthy)   0.0.0.0:1883->1883/tcp
```

### Step 5 — View Logs

```bash
# All services
docker compose logs -f

# App only
docker compose logs -f app

# Mosquitto only
docker compose logs -f mosquitto
```

---

## Run Modes

The entrypoint script supports multiple run modes, selectable via `docker compose run` or by overriding `CMD`:

### Streamlit Application (default)

```bash
docker compose up app
```

### MQTT Simulator (development)

Start synthetic sensor data publishing to the MQTT broker:

```bash
# Requires the 'dev' profile
docker compose --profile dev up simulator
```

### Run Tests Inside Container

```bash
docker compose run --rm app test
```

### Interactive Shell (debug)

```bash
docker compose run --rm app shell
```

---

## Production Deployment

### Using the Production Override

```bash
# Apply production settings on top of base compose file
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  up -d
```

**Production differences**:
- Config files are **not** bind-mounted (baked into image at build time)
- MQTT anonymous access is **disabled** (requires password file)
- Resource limits are **higher** (4 GB RAM, 4 CPUs)
- Log rotation is stricter (50 MB max, 5 files)
- MQTT port is **not** exposed to host (internal network only)

### Building a Tagged Production Image

```bash
# Tag with version
docker build -t petroflow:1.0.0 -t petroflow:latest .

# Push to registry (replace with your registry)
docker tag petroflow:latest your-registry.com/petroflow:1.0.0
docker push your-registry.com/petroflow:1.0.0
```

### Production Environment File

Create a production `.env` (keep it secret, use a secrets manager):

```ini
APP_ENV=production
LOG_LEVEL=WARNING
SECRET_KEY=<64-char-random-hex>
MQTT_BROKER_HOST=mosquitto
MQTT_USERNAME=petroflow_user
MQTT_PASSWORD=<strong-password>
MQTT_USE_TLS=false
DATABASE_PATH=/app/data/petroflow.db
```

---

## Volume Management

### List Named Volumes

```bash
docker volume ls | grep petroflow
```

### Backup the Database

```bash
# Copy SQLite database from the container volume to host
docker run --rm \
  -v petroflow_data:/data \
  -v $(pwd)/backups:/backup \
  alpine \
  cp /data/petroflow.db /backup/petroflow_$(date +%Y%m%d_%H%M%S).db
```

### Backup Logs

```bash
docker run --rm \
  -v petroflow_logs:/logs \
  -v $(pwd)/backups/logs:/backup \
  alpine \
  sh -c "cp -r /logs/* /backup/"
```

### Restore the Database

```bash
docker run --rm \
  -v petroflow_data:/data \
  -v $(pwd)/backups:/backup \
  alpine \
  cp /backup/petroflow_20240101_120000.db /data/petroflow.db
```

### Wipe All Volumes (destructive)

```bash
docker compose down -v
# WARNING: This deletes all persistent data!
```

---

## MQTT Configuration

### Default (Development) — Anonymous, No TLS

```conf
# mosquitto/config/mosquitto.conf
allow_anonymous true
listener 1883
```

### Production — Password Authentication

```bash
# Create password file
docker run --rm \
  -v $(pwd)/mosquitto/config:/mosquitto/config \
  eclipse-mosquitto:2.0 \
  mosquitto_passwd -c /mosquitto/config/passwd petroflow_user

# Update .env
MQTT_USERNAME=petroflow_user
MQTT_PASSWORD=<the-password-you-set>

# Update mosquitto.conf
# allow_anonymous false
# password_file /mosquitto/config/passwd
```

### Test MQTT Connectivity

```bash
# Subscribe (in one terminal)
docker compose exec mosquitto \
  mosquitto_sub -h localhost -t "petroflow/#" -v

# Publish test message (in another terminal)
docker compose exec mosquitto \
  mosquitto_pub -h localhost -t "petroflow/test" -m '{"test": true}'
```

---

## Troubleshooting

### Application doesn't start

```bash
# Check logs
docker compose logs app

# Common causes:
# - Missing .env file → cp .env.example .env
# - Port 8501 already in use → change STREAMLIT_PORT in .env
# - Mosquitto not ready → wait for healthy status
```

### MQTT connection refused

```bash
# Check mosquitto is running
docker compose ps mosquitto

# Check mosquitto logs
docker compose logs mosquitto

# Test from app container
docker compose exec app \
  python3 -c "import socket; s=socket.socket(); s.connect(('mosquitto', 1883)); print('OK')"
```

### Database errors

```bash
# Check database volume is mounted
docker compose exec app ls -la /app/data/

# Re-initialize database
docker compose exec app \
  python3 -c "from modules.database import init_database; init_database()"
```

### Out of memory

```bash
# Check container memory usage
docker stats petroflow_app

# Increase memory limit in docker-compose.yml:
# deploy.resources.limits.memory: 4G
```

### View container healthcheck status

```bash
docker inspect petroflow_app | python3 -c "
import json, sys
data = json.load(sys.stdin)
health = data[0]['State']['Health']
print('Status:', health['Status'])
for log in health.get('Log', [])[-3:]:
    print(' -', log.get('Output', '').strip())
"
```

---

## Useful Commands Reference

```bash
# Build image
docker compose build

# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart app only
docker compose restart app

# View live logs
docker compose logs -f

# Open shell in app container
docker compose exec app sh

# Run tests inside container
docker compose run --rm app test

# Check service health
docker compose ps

# Show resource usage
docker stats

# Pull latest base images
docker compose pull

# Start with simulator (dev profile)
docker compose --profile dev up

# Production mode
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# List volumes
docker volume ls | grep petroflow

# Backup database
docker run --rm -v petroflow_data:/data -v $(pwd):/backup alpine \
  cp /data/petroflow.db /backup/petroflow_backup.db
```

---

## Image Size Optimization

The multi-stage build achieves a small runtime image by:

1. **Stage 1 (builder)**: Compiles all Python C extensions (numpy, scipy, etc.) using build tools
2. **Stage 2 (runtime)**: Copies only the compiled `.whl` files — no build tools in final image
3. **`.dockerignore`**: Excludes tests, logs, database, backups, and dev files from build context
4. **`python:3.11-slim`**: Debian slim base — ~130 MB vs ~900 MB for the full image
5. **`--no-cache-dir`**: pip doesn't store downloaded packages in the image

**Typical image sizes**:

| Layer | Size |
|---|---|
| Base `python:3.11-slim` | ~130 MB |
| System runtime libs | ~50 MB |
| Python packages | ~600–700 MB |
| Application code | ~1 MB |
| **Total (estimated)** | **~780 MB** |

> **Note**: The 500 MB target in the spec is difficult to achieve with the full ML/scientific
> stack (numpy, scipy, scikit-learn, lifelines, plotly, trimesh). To reduce size further,
> consider using a separate lightweight prediction API (FastAPI) for inference-only deployments.

---

## Security Checklist

Before going to production:

- [ ] Change `SECRET_KEY` to a 64-character random hex value
- [ ] Set `MQTT_USERNAME` and `MQTT_PASSWORD`
- [ ] Set `allow_anonymous false` in `mosquitto.conf`
- [ ] Set `APP_ENV=production` and `LOG_LEVEL=WARNING`
- [ ] Remove `.env` from version control (it's in `.gitignore`)
- [ ] Use Docker secrets or a vault for sensitive credentials in orchestrated environments
- [ ] Configure TLS certificates for MQTT if sending data over public networks
- [ ] Review and restrict network access using firewall rules
- [ ] Enable log monitoring for the `security.log` audit category
