# PetroFlow API Documentation
## FastAPI Backend REST API Reference

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000`  
**API Prefix:** `/api`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Equipment Management](#equipment-management)
3. [Simulation](#simulation)
4. [Analysis](#analysis)
5. [IoT & Telemetry](#iot--telemetry)
6. [WebSocket Endpoints](#websocket-endpoints)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)

---

## Authentication

### Register User

**POST** `/api/auth/register`

Register a new user account.

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### Login

**POST** `/api/auth/login`

Authenticate user and receive access tokens.

**Request Body:** (Form Data)
```
username: john_doe
password: SecurePass123!
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### Refresh Token

**POST** `/api/auth/refresh`

Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### Get Current User

**GET** `/api/auth/me`

Get current authenticated user information.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## Equipment Management

### Get Equipment Types

**GET** `/api/equipment/types`

Get list of available equipment types.

**Response:** `200 OK`
```json
{
  "types": [
    {"id": "pump", "name": "Pump", "icon": "🔧"},
    {"id": "compressor", "name": "Compressor", "icon": "⚙️"},
    {"id": "separator", "name": "Separator", "icon": "🔄"},
    {"id": "heat_exchanger", "name": "Heat Exchanger", "icon": "🌡️"},
    {"id": "valve", "name": "Valve", "icon": "🚰"},
    {"id": "turbine", "name": "Turbine", "icon": "⚡"}
  ]
}
```

---

### Get Equipment Subtypes

**GET** `/api/equipment/subtypes/{equipment_type}`

Get subtypes for a specific equipment type.

**Path Parameters:**
- `equipment_type` (string): Equipment type ID

**Response:** `200 OK`
```json
{
  "subtypes": [
    {"id": "centrifugal", "name": "Centrifugal Pump"},
    {"id": "positive_displacement", "name": "Positive Displacement"},
    {"id": "submersible", "name": "Submersible Pump"}
  ]
}
```

---

### Create Equipment

**POST** `/api/equipment`

Create new equipment configuration.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "name": "Main Production Pump",
  "equipment_type": "pump",
  "equipment_subtype": "centrifugal",
  "description": "Primary pump for oil production",
  "parameters": {
    "flow_rate": 1000,
    "head": 50,
    "efficiency": 0.85,
    "power": 100
  }
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "name": "Main Production Pump",
  "equipment_type": "pump",
  "equipment_subtype": "centrifugal",
  "description": "Primary pump for oil production",
  "parameters": {
    "flow_rate": 1000,
    "head": 50,
    "efficiency": 0.85,
    "power": 100
  },
  "user_id": 1,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": null
}
```

---

### List Equipment

**GET** `/api/equipment`

List all equipment configurations for current user.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `skip` (integer, optional): Number of records to skip (default: 0)
- `limit` (integer, optional): Maximum records to return (default: 100)
- `equipment_type` (string, optional): Filter by equipment type

**Response:** `200 OK`
```json
{
  "equipment": [
    {
      "id": 1,
      "name": "Main Production Pump",
      "equipment_type": "pump",
      "equipment_subtype": "centrifugal",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

---

### Get Equipment

**GET** `/api/equipment/{equipment_id}`

Get specific equipment configuration.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Path Parameters:**
- `equipment_id` (integer): Equipment ID

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "Main Production Pump",
  "equipment_type": "pump",
  "equipment_subtype": "centrifugal",
  "description": "Primary pump for oil production",
  "parameters": {
    "flow_rate": 1000,
    "head": 50,
    "efficiency": 0.85,
    "power": 100
  },
  "user_id": 1,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": null
}
```

---

### Update Equipment

**PUT** `/api/equipment/{equipment_id}`

Update equipment configuration.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Path Parameters:**
- `equipment_id` (integer): Equipment ID

**Request Body:**
```json
{
  "name": "Updated Pump Name",
  "parameters": {
    "flow_rate": 1200,
    "head": 55
  }
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "Updated Pump Name",
  "equipment_type": "pump",
  "parameters": {
    "flow_rate": 1200,
    "head": 55,
    "efficiency": 0.85,
    "power": 100
  },
  "updated_at": "2024-01-01T01:00:00Z"
}
```

---

### Delete Equipment

**DELETE** `/api/equipment/{equipment_id}`

Delete equipment configuration.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Path Parameters:**
- `equipment_id` (integer): Equipment ID

**Response:** `204 No Content`

---

### Calculate Equipment Performance

**POST** `/api/equipment/{equipment_id}/calculate`

Perform equipment calculations.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Path Parameters:**
- `equipment_id` (integer): Equipment ID

**Request Body:**
```json
{
  "operating_conditions": {
    "flow_rate": 1000,
    "suction_pressure": 2.0,
    "discharge_pressure": 10.0,
    "temperature": 25.0,
    "fluid_properties": {
      "density": 850,
      "viscosity": 0.001
    }
  }
}
```

**Response:** `200 OK`
```json
{
  "results": {
    "efficiency": 0.82,
    "power_required": 105.5,
    "head": 48.2,
    "npsh_required": 3.5,
    "performance_curve": {
      "flow_rates": [800, 900, 1000, 1100, 1200],
      "heads": [52, 50, 48, 45, 42],
      "efficiencies": [0.78, 0.81, 0.82, 0.80, 0.76]
    }
  }
}
```

---

### Get Equipment Performance Metrics

**GET** `/api/equipment/{equipment_id}/performance`

Get equipment performance metrics and history.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Path Parameters:**
- `equipment_id` (integer): Equipment ID

**Response:** `200 OK`
```json
{
  "performance": {
    "efficiency": 0.85,
    "uptime": 0.95,
    "maintenance_score": 0.90,
    "last_calculation": "2024-01-01T00:00:00Z",
    "total_calculations": 150,
    "average_efficiency": 0.83
  }
}
```

---

## Simulation

### Run Simulation

**POST** `/api/simulation/run`

Execute dynamic simulation.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "equipment_ids": [1, 2, 3],
  "simulation_type": "steady_state",
  "parameters": {
    "time_step": 0.1,
    "duration": 3600,
    "convergence_tolerance": 1e-6
  },
  "initial_conditions": {
    "pressure": 5.0,
    "temperature": 25.0,
    "flow_rate": 1000
  }
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "simulation_id": 123,
  "results": {
    "converged": true,
    "iterations": 45,
    "execution_time": 2.5,
    "final_state": {
      "pressure": 4.98,
      "temperature": 26.2,
      "flow_rate": 998.5
    }
  }
}
```

---

### Get Simulation History

**GET** `/api/simulation/history`

Get simulation execution history.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `skip` (integer, optional): Number of records to skip
- `limit` (integer, optional): Maximum records to return

**Response:** `200 OK`
```json
{
  "simulations": [
    {
      "id": 123,
      "status": "completed",
      "created_at": "2024-01-01T00:00:00Z",
      "completed_at": "2024-01-01T00:02:30Z",
      "execution_time": 2.5
    }
  ],
  "total": 1
}
```

---

### Get Simulation Results

**GET** `/api/simulation/{simulation_id}`

Get specific simulation results.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Path Parameters:**
- `simulation_id` (integer): Simulation ID

**Response:** `200 OK`
```json
{
  "id": 123,
  "status": "completed",
  "results": {
    "converged": true,
    "iterations": 45,
    "time_series": {
      "time": [0, 0.1, 0.2, 0.3],
      "pressure": [5.0, 4.99, 4.98, 4.98],
      "temperature": [25.0, 25.5, 26.0, 26.2]
    }
  }
}
```

---

## Analysis

### Analyze Performance

**POST** `/api/analysis/performance`

Perform equipment performance analysis.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "equipment_id": 1,
  "analysis_type": "efficiency_trend",
  "time_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-31T23:59:59Z"
  }
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "analysis": {
    "trend": "declining",
    "efficiency_change": -0.05,
    "recommendations": [
      "Schedule maintenance check",
      "Inspect impeller for wear"
    ]
  }
}
```

---

### Predictive Maintenance

**POST** `/api/analysis/predictive-maintenance`

Run predictive maintenance analysis.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "equipment_id": 1
}
```

**Response:** `200 OK`
```json
{
  "predictions": [
    {
      "component": "impeller",
      "failure_probability": 0.15,
      "estimated_failure_date": "2024-06-15",
      "confidence": 0.85
    }
  ],
  "recommendations": [
    {
      "action": "replace_impeller",
      "priority": "medium",
      "estimated_cost": 5000,
      "estimated_downtime": 8
    }
  ]
}
```

---

## IoT & Telemetry

### List IoT Devices

**GET** `/api/iot/devices`

Get list of registered IoT devices.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "devices": [
    {
      "id": 1,
      "name": "Pump Sensor 01",
      "device_type": "pressure_sensor",
      "status": "online",
      "last_seen": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

---

### Register IoT Device

**POST** `/api/iot/devices`

Register new IoT device.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "name": "Temperature Sensor 01",
  "device_type": "temperature_sensor",
  "equipment_id": 1,
  "configuration": {
    "sampling_rate": 1,
    "units": "celsius"
  }
}
```

**Response:** `201 Created`
```json
{
  "device_id": 2,
  "status": "registered"
}
```

---

### Get Device Telemetry

**GET** `/api/iot/devices/{device_id}/telemetry`

Get telemetry data for specific device.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Path Parameters:**
- `device_id` (integer): Device ID

**Query Parameters:**
- `start_time` (string, optional): Start time (ISO format)
- `end_time` (string, optional): End time (ISO format)

**Response:** `200 OK`
```json
{
  "telemetry": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "value": 25.5,
      "unit": "celsius",
      "quality": "good"
    }
  ],
  "device_id": 1
}
```

---

## WebSocket Endpoints

### Telemetry WebSocket

**WebSocket** `/ws/telemetry`

Real-time telemetry data streaming.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/telemetry');
```

**Subscribe to Device:**
```json
{
  "type": "subscribe",
  "device_id": 1
}
```

**Telemetry Update:**
```json
{
  "type": "telemetry_update",
  "device_id": 1,
  "data": {
    "timestamp": "2024-01-01T00:00:00Z",
    "value": 25.5,
    "unit": "celsius"
  }
}
```

---

### Simulation WebSocket

**WebSocket** `/ws/simulation`

Real-time simulation updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/simulation');
```

**Start Simulation:**
```json
{
  "command": "start",
  "simulation_id": 123
}
```

**Simulation Update:**
```json
{
  "type": "simulation_update",
  "simulation_id": 123,
  "progress": 0.75,
  "current_iteration": 750
}
```

---

## Error Handling

### Error Response Format

All API errors follow this format:

```json
{
  "detail": "Error message",
  "status_code": 400,
  "timestamp": "2024-01-01T00:00:00Z",
  "path": "/api/equipment/1"
}
```

### Common HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `204 No Content` - Request successful, no content returned
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

### Validation Errors

```json
{
  "detail": "Validation error",
  "errors": [
    {
      "field": "email",
      "message": "Invalid email format"
    },
    {
      "field": "password",
      "message": "Password must be at least 8 characters"
    }
  ]
}
```

---

## Rate Limiting

### Default Limits

- **General API**: 60 requests per minute
- **Authentication**: 10 requests per minute
- **File Upload**: 5 requests per minute

### Rate Limit Headers

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640995200
```

### Rate Limit Exceeded

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 60
}
```

---

## Interactive API Documentation

- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`
- **OpenAPI JSON**: `http://localhost:8000/api/openapi.json`

---

**Last Updated:** 2026-05-19  
**API Version:** 1.0.0