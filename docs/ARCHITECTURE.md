# PetroFlow System Architecture
## FastAPI + React Migration Architecture

**Version:** 1.0.0  
**Date:** 2026-05-19

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Technology Stack](#technology-stack)
4. [Backend Architecture](#backend-architecture)
5. [Frontend Architecture](#frontend-architecture)
6. [Data Flow](#data-flow)
7. [Security Architecture](#security-architecture)
8. [Scalability & Performance](#scalability--performance)
9. [Deployment Architecture](#deployment-architecture)

---

## System Overview

PetroFlow is a comprehensive oil & gas production optimization platform that provides:

- **Equipment Management**: Configuration and monitoring of production equipment
- **Dynamic Simulation**: Real-time process simulation and optimization
- **Predictive Analytics**: AI-powered diagnostics and maintenance prediction
- **IoT Integration**: Real-time telemetry data collection and processing
- **3D Visualization**: Interactive 3D equipment and process visualization

### Architecture Principles

1. **Microservices**: Loosely coupled services for better scalability
2. **API-First**: RESTful API design with comprehensive documentation
3. **Real-time**: WebSocket support for live data streaming
4. **Scalable**: Horizontal scaling capability
5. **Secure**: JWT authentication, HTTPS, and data encryption
6. **Observable**: Comprehensive logging and monitoring

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Load Balancer (Nginx)                    │
│                    SSL Termination & Routing                     │
└────────────────┬────────────────────────────┬────────────────────┘
                 │                            │
        ┌────────▼────────┐          ┌────────▼────────────────┐
        │                 │          │                         │
        │  React Frontend │          │   FastAPI Backend       │
        │   (Port 3000)   │          │    (Port 8000)          │
        │                 │          │                         │
        │  - Components   │          │  - REST API             │
        │  - Redux Store  │◄────────►│  - WebSocket Server     │
        │  - 3D Viewer    │  HTTP/WS │  - Background Tasks     │
        │  - Charts       │          │  - Core Engines         │
        │                 │          │                         │
        └─────────────────┘          └────────┬────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────┐
                    │                         │                     │
           ┌────────▼────────┐    ┌──────────▼──────────┐  ┌──────▼──────┐
           │                 │    │                     │  │             │
           │   PostgreSQL    │    │       Redis         │  │    MQTT     │
           │   (Port 5432)   │    │    (Port 6379)      │  │ (Port 1883) │
           │                 │    │                     │  │             │
           │  - User Data    │    │  - Session Cache    │  │ - Telemetry │
           │  - Equipment    │    │  - API Cache        │  │ - Commands  │
           │  - Simulations  │    │  - Task Queue       │  │ - Events    │
           │  - Analytics    │    │                     │  │             │
           │                 │    │                     │  │             │
           └─────────────────┘    └─────────────────────┘  └─────────────┘
                    │                         │                     │
                    └─────────────────────────┴─────────────────────┘
                                          │
                              ┌───────────▼───────────┐
                              │                       │
                              │  Monitoring Stack     │
                              │  - Prometheus         │
                              │  - Grafana            │
                              │  - Sentry             │
                              │                       │
                              └───────────────────────┘
```

---

## Technology Stack

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.2+ | UI Framework |
| Redux Toolkit | 2.0+ | State Management |
| React Router | 6.21+ | Routing |
| Axios | 1.6+ | HTTP Client |
| Chart.js | 4.4+ | Data Visualization |
| Three.js | 0.160+ | 3D Graphics |
| Plotly.js | 2.27+ | Scientific Plots |
| Formik | 2.4+ | Form Management |
| Styled Components | 6.1+ | CSS-in-JS |

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Programming Language |
| FastAPI | 0.109+ | Web Framework |
| Uvicorn | 0.27+ | ASGI Server |
| SQLAlchemy | 2.0+ | ORM |
| Pydantic | 2.5+ | Data Validation |
| Celery | 5.3+ | Task Queue |
| Redis | 7.0+ | Cache & Queue |
| PostgreSQL | 15+ | Database |
| Paho-MQTT | 1.6+ | MQTT Client |

### Infrastructure

| Technology | Version | Purpose |
|------------|---------|---------|
| Docker | 24+ | Containerization |
| Docker Compose | 2.0+ | Orchestration |
| Nginx | 1.25+ | Reverse Proxy |
| Mosquitto | 2.0+ | MQTT Broker |
| Prometheus | 2.45+ | Metrics |
| Grafana | 10.0+ | Dashboards |

---

## Backend Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer                            │
│  - REST Endpoints (FastAPI)                             │
│  - WebSocket Handlers                                   │
│  - Request Validation (Pydantic)                        │
│  - Authentication & Authorization                       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  Service Layer                          │
│  - Business Logic                                       │
│  - Equipment Engine                                     │
│  - Simulation Engine                                    │
│  - Analysis Engine                                      │
│  - MQTT Service                                         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   Data Layer                            │
│  - SQLAlchemy Models                                    │
│  - Database Operations                                  │
│  - Cache Management (Redis)                             │
│  - File Storage                                         │
└─────────────────────────────────────────────────────────┘
```

### Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration
│   ├── database.py             # Database setup
│   │
│   ├── api/                    # API Layer
│   │   ├── deps.py             # Dependencies
│   │   ├── endpoints/          # REST endpoints
│   │   │   ├── auth.py
│   │   │   ├── equipment.py
│   │   │   ├── simulation.py
│   │   │   ├── analysis.py
│   │   │   └── iot.py
│   │   └── websockets/         # WebSocket handlers
│   │       └── telemetry.py
│   │
│   ├── core/                   # Core Business Logic
│   │   ├── security.py         # Authentication
│   │   ├── equipment_engine.py # Equipment calculations
│   │   ├── simulation_engine.py# Simulation logic
│   │   └── analysis_engine.py  # Analysis algorithms
│   │
│   ├── models/                 # Database Models
│   │   ├── user.py
│   │   ├── equipment.py
│   │   ├── simulation.py
│   │   └── telemetry.py
│   │
│   ├── schemas/                # Pydantic Schemas
│   │   ├── auth.py
│   │   ├── equipment.py
│   │   └── simulation.py
│   │
│   └── services/               # External Services
│       ├── mqtt_service.py     # MQTT integration
│       ├── calculation_service.py
│       └── report_service.py
│
├── tests/                      # Test Suite
├── requirements.txt
└── Dockerfile
```

### API Design Patterns

1. **RESTful Resources**: Standard CRUD operations
2. **Dependency Injection**: FastAPI's Depends system
3. **Repository Pattern**: Data access abstraction
4. **Service Layer**: Business logic separation
5. **DTO Pattern**: Pydantic schemas for data transfer

---

## Frontend Architecture

### Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    App Component                        │
│  - Routing                                              │
│  - Global State Provider                                │
│  - Theme Provider                                       │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──────┐ ┌──▼──────┐ ┌──▼──────────┐
│   Pages      │ │ Layout  │ │  Features   │
│              │ │         │ │             │
│ - Dashboard  │ │ - Header│ │ - Equipment │
│ - Equipment  │ │ - Sidebar│ │ - Simulation│
│ - Simulation │ │ - Footer│ │ - Analysis  │
│ - Analysis   │ │         │ │ - IoT       │
└──────┬───────┘ └─────────┘ └──────┬──────┘
       │                            │
       └────────────┬───────────────┘
                    │
        ┌───────────▼───────────┐
        │   Shared Components   │
        │                       │
        │ - Button              │
        │ - Input               │
        │ - Chart               │
        │ - Table               │
        │ - Modal               │
        └───────────────────────┘
```

### Directory Structure

```
frontend/
├── public/
│   ├── index.html
│   └── assets/
│
├── src/
│   ├── App.js                  # Root component
│   ├── index.js                # Entry point
│   │
│   ├── components/             # Reusable components
│   │   ├── Dashboard/
│   │   ├── Equipment/
│   │   ├── Simulation/
│   │   ├── Analysis/
│   │   └── Viewer3D/
│   │
│   ├── pages/                  # Page components
│   │   ├── Home.jsx
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   └── Equipment.jsx
│   │
│   ├── services/               # API services
│   │   └── api.js              # Axios configuration
│   │
│   ├── store/                  # Redux store
│   │   ├── index.js
│   │   ├── authSlice.js
│   │   ├── equipmentSlice.js
│   │   └── simulationSlice.js
│   │
│   ├── hooks/                  # Custom hooks
│   │   ├── useAuth.js
│   │   ├── useTelemetry.js
│   │   └── useWebSocket.js
│   │
│   ├── utils/                  # Utility functions
│   │   ├── formatters.js
│   │   ├── validators.js
│   │   └── constants.js
│   │
│   └── styles/                 # Global styles
│       └── theme.js
│
├── package.json
└── Dockerfile
```

### State Management

```javascript
// Redux Store Structure
{
  auth: {
    user: {...},
    token: "...",
    isAuthenticated: true
  },
  equipment: {
    items: [...],
    selected: {...},
    loading: false
  },
  simulation: {
    active: {...},
    history: [...],
    results: {...}
  },
  telemetry: {
    devices: [...],
    data: {...},
    connected: true
  }
}
```

---

## Data Flow

### Request Flow

```
User Action
    │
    ▼
React Component
    │
    ▼
Redux Action
    │
    ▼
API Service (Axios)
    │
    ▼
FastAPI Endpoint
    │
    ▼
Service Layer
    │
    ▼
Database/Cache
    │
    ▼
Response
    │
    ▼
Redux Store Update
    │
    ▼
Component Re-render
```

### Real-time Data Flow

```
IoT Device
    │
    ▼
MQTT Broker
    │
    ▼
FastAPI MQTT Handler
    │
    ▼
WebSocket Broadcast
    │
    ▼
React WebSocket Client
    │
    ▼
Redux Store Update
    │
    ▼
Component Re-render
```

---

## Security Architecture

### Authentication Flow

```
1. User Login
   ├─► POST /api/auth/login
   ├─► Verify credentials
   ├─► Generate JWT tokens
   └─► Return access_token + refresh_token

2. API Request
   ├─► Include Authorization header
   ├─► Verify JWT token
   ├─► Extract user info
   └─► Process request

3. Token Refresh
   ├─► POST /api/auth/refresh
   ├─► Verify refresh_token
   ├─► Generate new access_token
   └─► Return new tokens
```

### Security Layers

1. **Transport Security**: HTTPS/TLS encryption
2. **Authentication**: JWT tokens with expiration
3. **Authorization**: Role-based access control (RBAC)
4. **Input Validation**: Pydantic schemas
5. **SQL Injection Prevention**: SQLAlchemy ORM
6. **XSS Prevention**: React's built-in escaping
7. **CSRF Protection**: Token-based authentication
8. **Rate Limiting**: Per-user and per-endpoint limits

---

## Scalability & Performance

### Horizontal Scaling

```
┌─────────────────────────────────────────┐
│         Load Balancer                   │
└────┬────────┬────────┬────────┬─────────┘
     │        │        │        │
┌────▼───┐ ┌─▼────┐ ┌─▼────┐ ┌─▼────┐
│Backend │ │Backend│ │Backend│ │Backend│
│   1    │ │   2   │ │   3   │ │   N   │
└────┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
     │        │        │        │
     └────────┴────────┴────────┘
              │
     ┌────────▼────────┐
     │  Shared State   │
     │  - PostgreSQL   │
     │  - Redis        │
     └─────────────────┘
```

### Performance Optimizations

1. **Caching Strategy**:
   - Redis for API responses
   - Browser caching for static assets
   - CDN for global distribution

2. **Database Optimization**:
   - Connection pooling
   - Query optimization
   - Indexing strategy
   - Read replicas

3. **Async Operations**:
   - FastAPI async endpoints
   - Background tasks with Celery
   - Non-blocking I/O

4. **Frontend Optimization**:
   - Code splitting
   - Lazy loading
   - Memoization
   - Virtual scrolling

---

## Deployment Architecture

### Development Environment

```
docker-compose.yml
├── postgres (development)
├── redis (development)
├── mqtt (development)
├── backend (hot-reload)
└── frontend (hot-reload)
```

### Production Environment

```
docker-compose.prod.yml
├── nginx (load balancer)
├── backend (3 replicas)
├── frontend (static files)
├── postgres (primary + replica)
├── redis (cluster)
├── mqtt (cluster)
├── celery-worker (3 replicas)
├── celery-beat
└── monitoring (Prometheus + Grafana)
```

### CI/CD Pipeline

```
Git Push
    │
    ▼
GitHub Actions
    │
    ├─► Run Tests
    ├─► Build Docker Images
    ├─► Security Scan
    ├─► Push to Registry
    │
    ▼
Deployment
    │
    ├─► Staging Environment
    ├─► Integration Tests
    ├─► Manual Approval
    │
    ▼
Production Deployment
    │
    ├─► Blue-Green Deployment
    ├─► Health Checks
    └─► Rollback if needed
```

---

## Monitoring & Observability

### Metrics Collection

- **Application Metrics**: Request rate, latency, errors
- **System Metrics**: CPU, memory, disk, network
- **Business Metrics**: Active users, calculations, simulations

### Logging Strategy

```
Application Logs
    │
    ▼
Structured JSON Logs
    │
    ▼
Log Aggregation (ELK Stack)
    │
    ▼
Dashboards & Alerts
```

### Health Checks

- `/health` - Basic health check
- `/health/db` - Database connectivity
- `/health/redis` - Cache connectivity
- `/health/mqtt` - MQTT broker connectivity

---

**Last Updated:** 2026-05-19  
**Architecture Version:** 1.0.0