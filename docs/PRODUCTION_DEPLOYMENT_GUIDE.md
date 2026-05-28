# PetroFlow Production Deployment Guide

**Version:** 1.0.0  
**Date:** 2026-05-19  
**Status:** Production Ready  
**Compliance:** ISO/IEC 27001, OWASP Top 10

---

## Table of Contents

1. [Overview](#1-overview)
2. [Pre-Deployment Checklist](#2-pre-deployment-checklist)
3. [Infrastructure Requirements](#3-infrastructure-requirements)
4. [Docker Production Configuration](#4-docker-production-configuration)
5. [Database Setup](#5-database-setup)
6. [Reverse Proxy & TLS Configuration](#6-reverse-proxy--tls-configuration)
7. [Security Hardening](#7-security-hardening)
8. [Monitoring and Logging](#8-monitoring-and-logging)
9. [CI/CD Pipeline](#9-cicd-pipeline)
10. [Scaling Considerations](#10-scaling-considerations)
11. [Maintenance Procedures](#11-maintenance-procedures)
12. [Troubleshooting Guide](#12-troubleshooting-guide)

---

## 1. Overview

### 1.1 Architecture Overview

PetroFlow is a containerized microservices application with the following components:

```
┌─────────────────────────────────────────────────────────────┐
│                    Internet (HTTPS)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │ Traefik │ (TLS 1.3 Termination)
                    │  v3.0   │ (Let's Encrypt)
                    └────┬────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼─────┐    ┌────▼─────┐    ┌────▼─────┐
   │ Frontend │    │ Backend  │    │  Flower  │
   │  Nginx   │    │ FastAPI  │    │ Monitor  │
   │  React   │    │ Uvicorn  │    └──────────┘
   └──────────┘    └────┬─────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────▼─────┐   ┌────▼─────┐   ┌────▼─────┐
   │PostgreSQL│   │  Redis   │   │  MQTT    │
   │    15    │   │  Cache   │   │Mosquitto │
   └──────────┘   └──────────┘   └──────────┘
                        │
                   ┌────▼─────┐
                   │  Celery  │
                   │ Workers  │
                   └──────────┘
```

### 1.2 Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Frontend** | React + Material-UI | 18.x | User interface |
| **Web Server** | Nginx | 1.25+ | Static file serving, reverse proxy |
| **Backend** | FastAPI | 0.109+ | REST API, WebSocket |
| **ASGI Server** | Uvicorn | 0.27+ | Async Python server |
| **Database** | PostgreSQL | 15+ | Primary data store |
| **Cache** | Redis | 7.x | Session, rate limiting, caching |
| **Message Broker** | MQTT (Mosquitto) | 2.0 | IoT telemetry |
| **Task Queue** | Celery | 5.3+ | Background jobs |
| **Reverse Proxy** | Traefik | 3.0 | TLS termination, routing |
| **Container Runtime** | Docker | 24.0+ | Containerization |
| **Orchestration** | Docker Compose | 2.20+ | Multi-container management |

### 1.3 Key Features

- **Zero-Trust Security Model**: TLS 1.3, mutual authentication, network isolation
- **Multi-Stage Docker Builds**: Optimized images < 500 MB
- **Comprehensive Logging**: 7 audit log categories, SIEM-ready JSON format
- **High Availability**: Health checks, auto-restart, graceful shutdown
- **Scalability**: Horizontal scaling ready, load balancing support
- **Monitoring**: Prometheus metrics, Grafana dashboards, Flower for Celery

---

## 2. Pre-Deployment Checklist

### 2.1 System Requirements

#### Minimum Requirements (Development/Testing)
- **CPU**: 4 cores (2.0 GHz+)
- **RAM**: 8 GB
- **Storage**: 50 GB SSD
- **Network**: 100 Mbps

#### Recommended Requirements (Production)
- **CPU**: 8 cores (3.0 GHz+)
- **RAM**: 16 GB
- **Storage**: 200 GB SSD (NVMe preferred)
- **Network**: 1 Gbps
- **Backup Storage**: 500 GB (separate volume)

### 2.2 Software Prerequisites

```bash
# Check Docker version (minimum 24.0)
docker --version

# Check Docker Compose version (minimum 2.20)
docker compose version

# Check available disk space (minimum 50 GB free)
df -h

# Check available memory (minimum 8 GB)
free -h

# Verify network connectivity
ping -c 4 8.8.8.8
```

### 2.3 Network Requirements

| Port | Protocol | Service | Exposure | Purpose |
|------|----------|---------|----------|---------|
| 80 | TCP | HTTP | Public | Redirect to HTTPS |
| 443 | TCP | HTTPS | Public | Application access |
| 5432 | TCP | PostgreSQL | Internal | Database |
| 6379 | TCP | Redis | Internal | Cache |
| 1883 | TCP | MQTT | Internal | IoT telemetry |
| 8883 | TCP | MQTTS | Internal | Secure MQTT |
| 5555 | TCP | Flower | Internal | Celery monitoring |

### 2.4 DNS Configuration

Configure DNS records before deployment:

```dns
# A Record for main application
app.petroflow.com.     IN  A     <YOUR_SERVER_IP>

# A Record for API (optional, can use subdomain)
api.petroflow.com.     IN  A     <YOUR_SERVER_IP>

# CNAME for www (optional)
www.petroflow.com.     IN  CNAME app.petroflow.com.
```

### 2.5 SSL/TLS Certificates

**Option 1: Let's Encrypt (Recommended)**
- Automatic certificate generation via Traefik
- Auto-renewal every 60 days
- Free and trusted by all browsers

**Option 2: Custom Certificates**
- Place certificates in `./traefik/certs/`
- Update `docker-compose.prod.yml` to mount certificates
- Ensure certificates are valid for at least 90 days

### 2.6 Backup Strategy

Before deployment, establish:

1. **Database Backups**
   - Daily automated backups
   - 30-day retention minimum
   - Off-site backup storage
   - Tested restore procedures

2. **Volume Backups**
   - Weekly full backups of Docker volumes
   - Incremental daily backups
   - Backup verification schedule

3. **Configuration Backups**
   - Version control for all config files
   - Encrypted secrets backup
   - Disaster recovery documentation

---

## 3. Infrastructure Requirements

### 3.1 Server Specifications

#### Production Server (Single Node)

```yaml
Server Type: Virtual Machine or Bare Metal
OS: Ubuntu 22.04 LTS (recommended) or RHEL 8+
CPU: 8 cores @ 3.0 GHz
RAM: 16 GB
Storage:
  - OS Disk: 50 GB SSD
  - Data Disk: 200 GB SSD (for Docker volumes)
  - Backup Disk: 500 GB (separate volume/location)
Network: 1 Gbps, static IP
Firewall: UFW or iptables configured
```

#### High Availability Setup (3+ Nodes)

```yaml
Load Balancer: HAProxy or AWS ELB
Database: PostgreSQL with streaming replication
Cache: Redis Sentinel (3 nodes)
Application: 3+ app containers behind load balancer
Storage: Shared NFS or S3-compatible object storage
```

### 3.2 Operating System Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    ufw \
    fail2ban \
    unattended-upgrades

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Enable automatic security updates
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 3.3 Docker Installation

```bash
# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group (logout/login required)
sudo usermod -aG docker $USER

# Verify installation
docker --version
docker compose version

# Enable Docker service
sudo systemctl enable docker
sudo systemctl start docker
```

### 3.4 Docker Configuration

Create `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "userland-proxy": false,
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
```

Apply configuration:

```bash
sudo systemctl restart docker
```

---

## 4. Docker Production Configuration

### 4.1 Environment Variables Setup

```bash
# Navigate to project directory
cd /opt/petroflow

# Copy environment template
cp .env.example .env

# Generate secure secret key
openssl rand -hex 32

# Edit .env file
nano .env
```

**Critical Environment Variables:**

```ini
# APPLICATION
APP_ENV=production
SECRET_KEY=<GENERATED_64_CHAR_HEX>

# DATABASE
DATABASE_URL=postgresql://petroflow:SECURE_PASSWORD@postgres:5432/petroflow

# REDIS
REDIS_URL=redis://redis:6379/0

# MQTT
MQTT_BROKER_HOST=mosquitto
MQTT_USERNAME=petroflow_mqtt
MQTT_PASSWORD=<SECURE_PASSWORD>
MQTT_USE_TLS=true

# SECURITY
CORS_ALLOWED_ORIGINS=https://app.petroflow.com
JWT_SECRET_KEY=<GENERATED_64_CHAR_HEX>
MFA_ENABLED=true

# MONITORING
SENTRY_DSN=<YOUR_SENTRY_DSN>
```

See `.env.example` for all 134 environment variables.

### 4.2 Production Deployment

```bash
# Build and start production stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Check service status
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Stop stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

### 4.3 Multi-Stage Docker Build

Build production image:

```bash
# Build with BuildKit
DOCKER_BUILDKIT=1 docker build \
  --target runtime \
  --tag petroflow:1.0.0 \
  --tag petroflow:latest \
  .

# Verify image size (should be < 500 MB)
docker images petroflow:latest
```

### 4.4 Health Checks

All services include health checks. Monitor with:

```bash
# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}"

# View health check logs
docker inspect --format='{{json .State.Health}}' petroflow_app | jq
```

---

## 5. Database Setup

### 5.1 PostgreSQL Configuration

**Production settings** (add to docker-compose.prod.yml):

```yaml
postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_DB: petroflow
    POSTGRES_USER: petroflow
    POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=en_US.UTF-8"
  command:
    - "postgres"
    - "-c" 
    - "max_connections=200"
    - "-c"
    - "shared_buffers=4GB"
    - "-c"
    - "effective_cache_size=12GB"
    - "-c"
    - "maintenance_work_mem=1GB"
    - "-c"
    - "checkpoint_completion_target=0.9"
    - "-c"
    - "wal_buffers=16MB"
    - "-c"
    - "default_statistics_target=100"
    - "-c"
    - "random_page_cost=1.1"
    - "-c"
    - "effective_io_concurrency=200"
    - "-c"
    - "work_mem=20MB"
    - "-c"
    - "min_wal_size=1GB"
    - "-c"
    - "max_wal_size=4GB"
```

### 5.2 Database Initialization

```bash
# Run migrations
docker compose exec backend alembic upgrade head

# Verify database
docker compose exec postgres psql -U petroflow -d petroflow -c "\dt"
```

### 5.3 Backup Procedures

**Automated backup script** (`scripts/backup-database.sh`):

```bash
#!/bin/bash
set -e

BACKUP_DIR="/backups/postgresql"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="petroflow_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Perform backup
docker compose exec -T postgres pg_dump -U petroflow petroflow | \
  gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

# Remove old backups
find "$BACKUP_DIR" -name "petroflow_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: ${BACKUP_FILE}"
```

**Setup cron job**:

```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /opt/petroflow/scripts/backup-database.sh >> /var/log/petroflow-backup.log 2>&1
```

**Restore procedure**:

```bash
# Restore from backup
gunzip -c /backups/postgresql/petroflow_20260519_020000.sql.gz | \
  docker compose exec -T postgres psql -U petroflow petroflow
```

---

## 6. Reverse Proxy & TLS Configuration

### 6.1 Traefik Setup

Traefik v3.0 handles TLS termination. Configuration in `docker-compose.prod.yml`:

```yaml
traefik:
  image: traefik:v3.0
  command:
    - --providers.docker=true
    - --entrypoints.web.address=:80
    - --entrypoints.websecure.address=:443
    - --certificatesresolvers.letsencrypt.acme.email=devops@petroflow.com
    - --certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json
    - --certificatesresolvers.letsencrypt.acme.tlschallenge=true
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - petroflow_letsencrypt:/letsencrypt
```

### 6.2 TLS 1.3 Configuration

**TLS options** (`traefik/tls-options.yml`):

```yaml
tls:
  options:
    tlsMinVersion13:
      minVersion: VersionTLS13
      sniStrict: true

http:
  middlewares:
    security-headers:
      headers:
        stsSeconds: 31536000
        stsIncludeSubdomains: true
        frameDeny: true
        contentTypeNosniff: true
        browserXssFilter: true
```

### 6.3 Verify TLS

```bash
# Test TLS 1.3
curl -v --tlsv1.3 https://app.petroflow.com

# Check certificate
openssl s_client -connect app.petroflow.com:443 -servername app.petroflow.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

---

## 7. Security Hardening

### 7.1 Secrets Management

**Use Docker Secrets**:

```bash
# Create secrets
echo "your_db_password" | docker secret create db_password -
echo "your_jwt_secret" | docker secret create jwt_secret -

# List secrets
docker secret ls
```

### 7.2 Zero-Trust Security

**Implemented features**:
- Network segmentation (internal network isolated)
- TLS 1.3 for all connections
- Non-root containers
- MFA required
- Audit logging for all actions
- Rate limiting on all endpoints

### 7.3 Security Headers

All responses include:
- `Strict-Transport-Security`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Content-Security-Policy`
- `Referrer-Policy`

---

## 8. Monitoring and Logging

### 8.1 Logging Architecture

**7 Audit Log Categories**:
1. system_audit.log
2. authentication.log
3. database.log
4. predictions.log
5. file_operations.log
6. errors.log
7. security.log

Configuration in `config/logging_config.json`.

### 8.2 Prometheus Metrics

Add to `docker-compose.prod.yml`:

```yaml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
  ports:
    - "9090:9090"
```

### 8.3 Grafana Dashboards

```yaml
grafana:
  image: grafana/grafana:latest
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
  ports:
    - "3000:3000"
```

### 8.4 Alert Configuration

Configure alerts in `prometheus/alerts.yml` for:
- High error rates
- Database down
- High memory usage
- Disk space low
- Certificate expiration

---

## 9. CI/CD Pipeline

### 9.1 GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          docker compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit
  
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: |
          docker build -t petroflow:${{ github.sha }} .
      - name: Push to registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker push petroflow:${{ github.sha }}
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /opt/petroflow
            docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
            docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 9.2 Deployment Steps

1. **Pre-deployment checks**
2. **Database backup**
3. **Pull latest images**
4. **Run migrations**
5. **Rolling update**
6. **Health check verification**
7. **Rollback on failure**

### 9.3 Rollback Procedure

```bash
# Rollback to previous version
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
docker tag petroflow:previous petroflow:latest
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 10. Scaling Considerations

### 10.1 Horizontal Scaling

**Load balancer configuration** (HAProxy):

```haproxy
frontend petroflow_frontend
    bind *:443 ssl crt /etc/ssl/certs/petroflow.pem
    default_backend petroflow_backend

backend petroflow_backend
    balance roundrobin
    option httpchk GET /health
    server app1 10.0.1.10:8501 check
    server app2 10.0.1.11:8501 check
    server app3 10.0.1.12:8501 check
```

### 10.2 Database Replication

**PostgreSQL streaming replication**:

```yaml
# Primary
postgres-primary:
  image: postgres:15
  environment:
    POSTGRES_REPLICATION_MODE: master
    POSTGRES_REPLICATION_USER: replicator
    POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}

# Replica
postgres-replica:
  image: postgres:15
  environment:
    POSTGRES_REPLICATION_MODE: slave
    POSTGRES_MASTER_HOST: postgres-primary
    POSTGRES_MASTER_PORT: 5432
```

### 10.3 Redis Clustering

```yaml
redis-sentinel:
  image: redis:7-alpine
  command: redis-sentinel /etc/redis/sentinel.conf
  volumes:
    - ./redis/sentinel.conf:/etc/redis/sentinel.conf
```

### 10.4 CDN Integration

Use CloudFlare or AWS CloudFront for:
- Static asset caching
- DDoS protection
- Global distribution
- SSL/TLS termination

---

## 11. Maintenance Procedures

### 11.1 Update Procedures

```bash
# 1. Backup database
./scripts/backup-database.sh

# 2. Pull latest images
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull

# 3. Update containers
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. Run migrations
docker compose exec backend alembic upgrade head

# 5. Verify health
docker compose ps
```

### 11.2 Certificate Renewal

Let's Encrypt certificates auto-renew. Manual renewal:

```bash
# Force renewal
docker compose exec traefik traefik cert renew
```

### 11.3 Log Rotation

Configure logrotate (`/etc/logrotate.d/petroflow`):

```
/opt/petroflow/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 petroflow petroflow
    sharedscripts
    postrotate
        docker compose -f /opt/petroflow/docker-compose.yml -f /opt/petroflow/docker-compose.prod.yml kill -s USR1 app
    endscript
}
```

### 11.4 Database Maintenance

```bash
# Vacuum database
docker compose exec postgres psql -U petroflow -d petroflow -c "VACUUM ANALYZE;"

# Reindex
docker compose exec postgres psql -U petroflow -d petroflow -c "REINDEX DATABASE petroflow;"

# Check database size
docker compose exec postgres psql -U petroflow -d petroflow -c "SELECT pg_size_pretty(pg_database_size('petroflow'));"
```

---

## 12. Troubleshooting Guide

### 12.1 Common Issues

#### Container Won't Start

```bash
# Check logs
docker compose logs app

# Check resource usage
docker stats

# Verify environment variables
docker compose config
```

#### Database Connection Failed

```bash
# Check PostgreSQL status
docker compose exec postgres pg_isready -U petroflow

# Test connection
docker compose exec backend python -c "from app.db import engine; print(engine.connect())"

# Check network
docker network inspect petroflow_net
```

#### High Memory Usage

```bash
# Check container memory
docker stats --no-stream

# Restart container
docker compose restart app

# Adjust memory limits in docker-compose.prod.yml
```

### 12.2 Performance Debugging

```bash
# Check slow queries
docker compose exec postgres psql -U petroflow -d petroflow -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Monitor Redis
docker compose exec redis redis-cli INFO stats

# Check MQTT broker
docker compose exec mosquitto mosquitto_sub -t '$SYS/#' -v
```

### 12.3 WebSocket Issues

```bash
# Test WebSocket connection
wscat -c wss://app.petroflow.com/ws/telemetry

# Check Traefik routing
docker compose logs traefik | grep websocket
```

### 12.4 Emergency Procedures

**Complete system restart**:

```bash
# Stop all services
docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# Start services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify health
docker compose ps
```

**Restore from backup**:

```bash
# 1. Stop application
docker compose stop app backend

# 2. Restore database
gunzip -c /backups/postgresql/latest.sql.gz | docker compose exec -T postgres psql -U petroflow petroflow

# 3. Restart application
docker compose start app backend
```

---

## Additional Resources

- **Integration Testing Guide**: See [`docs/INTEGRATION_TESTING_GUIDE.md`](INTEGRATION_TESTING_GUIDE.md)
- **Docker Deployment Guide**: See [`docs/DOCKER_DEPLOYMENT_GUIDE.md`](DOCKER_DEPLOYMENT_GUIDE.md)
- **Production Readiness Report**: See [`docs/PRODUCTION_READINESS_REPORT.md`](PRODUCTION_READINESS_REPORT.md)

---

## Support

For production support:
- **Email**: devops@petroflow.com
- **Emergency**: +1-XXX-XXX-XXXX
- **Documentation**: https://docs.petroflow.com

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-05-19  
**Next Review**: 2026-08-19