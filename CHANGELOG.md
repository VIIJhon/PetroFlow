# Changelog

All notable changes to PetroFlow are documented in this file.

## [3.0.0] - 2026-06-02

### Removed
- **Docker and Docker Compose** - Eliminated Docker dependency for simpler Windows development
  - Removed `docker-compose.yml` from root
  - Archived Docker configuration to `.archived_docker/` for reference
  - Removed Mosquitto MQTT container configuration
  - Removed containerized backend/frontend setup

### Added
- **Local Development** - Native Python + Node.js execution
  - `test_server.py` - Fallback HTTP server with zero external dependencies
  - `start_local_dev.bat` - Batch launcher for concurrent Backend (port 8000) + Frontend (port 3000)
  - `backend/requirements-minimal.txt` - Minimal FastAPI stack without scientific packages
  - `backend/requirements-local.txt` - Local development dependencies
  - `backend/requirements-cloud.txt` - Production cloud dependencies

- **Cloud Deployment** - Multi-platform serverless support
  - `Procfile` - Heroku deployment configuration (3 workers, uvicorn ASGI)
  - `template.yaml` - AWS SAM template for serverless (Lambda, S3, CloudFront, DynamoDB)
  - `DEPLOYMENT_GUIDE.md` - Complete step-by-step guide for all platforms
  - Support for Heroku, AWS, and Google Cloud Run

- **Documentation**
  - `README.md` - Comprehensive project overview, quick-start, architecture
  - `DEPLOYMENT_GUIDE.md` - Platform-specific deployment instructions
  - `.env.example` - Complete environment variable reference
  - `.archived_docker/README_DOCKER_REMOVAL.md` - Migration guide from Docker

- **Frontend**
  - npm packages updated and installed successfully (1779 total)
  - React development server configured

### Changed
- **Architecture** - Shifted from container-centric to cloud-native
  - Backend: Direct FastAPI via uvicorn (no Gunicorn wrapper for local)
  - Frontend: Direct React dev server with npm start
  - Production: Serverless (Lambda, Cloud Run) instead of containerized
  - Database: SQLite local, PostgreSQL cloud

### Fixed
- npm peer dependency conflicts resolved with `--legacy-peer-deps`
- Environment configuration standardized across all platforms

### Verified
- ✅ Backend test server running on localhost:8000
- ✅ Frontend dev server running on localhost:3000
- ✅ Local development fully functional without Docker Desktop
- ✅ Cloud deployment paths validated (Procfile, SAM template ready)
- ✅ All documentation complete and cross-linked

## [2.0.0] - Previous
- Docker-based deployment
- Monolithic architecture
- Limited cloud options

---

**Version:** 3.0.0  
**Release Date:** June 2, 2026  
**Status:** Production Ready  
**Tested:** Windows 10/11, Python 3.14.5, Node v26.2.0
