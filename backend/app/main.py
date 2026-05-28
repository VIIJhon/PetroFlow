"""
PetroFlow FastAPI Main Application
Entry point for the FastAPI backend server
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import logging
import time
from pathlib import Path

from app.config import settings
from app.api.endpoints import (
    equipment,
    simulation,
    analysis,
    iot,
    auth,
    statistics,
    motor_config,
    ai_analysis,
    compat
)
# Phase 5: Import refactored endpoints
from app.api.endpoints import (
    simulation_refactored,
    equipment_refactored,
    iot_refactored
)
from app.api.endpoints import workers, maintenance, manuals, google_auth, users, reliability, engineering, reports
from app.api.websockets import telemetry
from app.database import engine, Base, check_db_connection
from app.db.init_db import check_db_health
from app.database import SessionLocal
from app.api.deps import reset_service_instances

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PetroFlow API",
    description="Advanced Oil & Gas Production Optimization Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    return response

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred"
        }
    )

# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.get("/api/v2/health")
async def health_check_v2():
    """V2 health check endpoint for demo dashboard"""
    return {
        "status": "online",
        "version": "1.0.0",
        "api_version": "v2",
        "environment": settings.ENVIRONMENT,
        "services": {
            "database": "operational",
            "safety_validator": "operational",
            "optimizer": "operational",
            "telemetry": "operational",
            "simulation": "operational"
        }
    }


# Database health check endpoint
@app.get("/api/v1/health/db")
async def database_health_check():
    """Database health check endpoint"""
    db = SessionLocal()
    try:
        health = check_db_health(db)
        status_code = 200 if health["status"] == "healthy" else 503
        return JSONResponse(content=health, status_code=status_code)
    finally:
        db.close()

# Include routers - Original endpoints (backward compatibility)
app.include_router(compat.router)
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(google_auth.router, prefix="/api/auth/google", tags=["Google OAuth"])
app.include_router(equipment.router, prefix="/api/equipment", tags=["Equipment"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["Simulation"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(statistics.router)
app.include_router(motor_config.router)
app.include_router(iot.router, prefix="/api/iot", tags=["IoT & Telemetry"])
app.include_router(telemetry.router, prefix="/ws", tags=["WebSockets"])

# Phase 5: Include refactored endpoints with new routes
app.include_router(
    simulation_refactored.router,
    prefix="/api/v2/simulation",
    tags=["Simulation V2 (Refactored)"]
)
app.include_router(
    equipment_refactored.router,
    prefix="/api/v2/equipment",
    tags=["Equipment V2 (Refactored)"]
)
app.include_router(
    iot_refactored.router,
    prefix="/api/v2/iot",
    tags=["IoT V2 (Refactored)"]
)

# Gemini AI Analysis endpoints
app.include_router(
    ai_analysis.router,
    prefix="/api/v2/ai",
    tags=["AI Analysis (Gemini)"]
)

# Workers, Maintenance and Technical Manuals RAG endpoints
app.include_router(
    workers.router,
    prefix="/api/v2/workers",
    tags=["Workers V2"]
)
app.include_router(
    users.router,
    prefix="/api/v2/users",
    tags=["Users V2"]
)
app.include_router(
    maintenance.router,
    prefix="/api/v2/maintenance",
    tags=["Maintenance V2"]
)
app.include_router(
    manuals.router,
    prefix="/api/v2/manuals",
    tags=["Manuals RAG V2"]
)
app.include_router(
    reliability.router,
    prefix="/api/v2/reliability",
    tags=["Reliability V2"]
)
app.include_router(
    engineering.router,
    prefix="/api/v2/engineering",
    tags=["Engineering V2"]
)
app.include_router(
    reports.router,
    prefix="/api/v2/reports",
    tags=["Reports V2"]
)

# Mount static files for React SPA
frontend_build_path = Path(__file__).parent.parent.parent / "frontend" / "build"

# We define the catch-all SPA route AFTER all API routes have been registered
@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
    """
    Catch-all route to serve the React SPA and its static assets.
    """
    # Prevent catching API/WS routes that 404'd
    if full_path.startswith("api/") or full_path.startswith("ws/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
        
    # If the build folder doesn't exist, provide a helpful message
    if not frontend_build_path.exists():
        return JSONResponse(
            status_code=503, 
            content={
                "detail": "Frontend build not found. Please run 'npm run build' in the frontend directory."
            }
        )

    # If the user is requesting a specific file that exists (like static/js/..., favicon.ico, etc.)
    file_path = frontend_build_path / full_path
    if file_path.is_file():
        return FileResponse(file_path)

    # For any other route, serve index.html so React Router can handle it
    index_path = frontend_build_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    
    return JSONResponse(status_code=404, content={"detail": "Index.html not found"})

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event handler"""
    logger.info("=" * 60)
    logger.info("Starting PetroFlow API (Unified Backend/Frontend Mode)...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Version: 1.0.0 (Phase 5 - Refactored)")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    
    # Check database connection
    logger.info("Checking database connection...")
    if check_db_connection():
        logger.info("✓ Database connection successful")
        # Ensure tables exist (create if missing) and initialize minimal data in development
        try:
            # Create tables directly from the current process' Base/engine to avoid import-name duplication
            from app.database import Base, engine
            Base.metadata.create_all(bind=engine)

            # Create an initial admin user if none exists using local model imports
            from app.models.user import User, UserRole
            from app.core.security import get_password_hash

            db = SessionLocal()
            try:
                user_count = db.query(User).count()
                if user_count == 0:
                    logger.info("No users found, creating initial admin user")
                    admin_user = User(
                        email="admin@petroflow.com",
                        username="admin",
                        hashed_password=get_password_hash("admin123"),
                        full_name="System Administrator",
                        role=UserRole.ADMIN,
                        is_active=True,
                        is_verified=True,
                        company="PetroFlow",
                        department="IT"
                    )
                    db.add(admin_user)
                    db.commit()
                    db.refresh(admin_user)
                    logger.info(f"Created admin user: {admin_user.email}")
                else:
                    logger.info(f"Database already initialized with {user_count} users")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Could not create or initialize database tables: {e}")
        
        # Get database health status
        db = SessionLocal()
        try:
            health = check_db_health(db)
            logger.info(f"✓ Database health: {health['status']}")
            logger.info(f"  - Users: {health.get('users', 0)}")
            logger.info(f"  - Equipment: {health.get('equipment', 0)}")
        except Exception as e:
            logger.warning(f"Could not get database health: {e}")
        finally:
            db.close()
    else:
        logger.error("✗ Database connection failed!")
        logger.error("Please check your database configuration and ensure PostgreSQL is running")
    
    # Phase 5: Initialize services (singleton pattern via dependency injection)
    logger.info("Initializing Phase 5 modular services...")
    try:
        from app.api.deps import (
            get_safety_validator,
            get_optimizer,
            get_telemetry_processor,
            get_simulation_orchestrator,
            get_report_generator
        )
        
        # Trigger singleton initialization
        _ = get_safety_validator()
        logger.info("✓ SafetyEnvelopeValidator initialized")
        
        _ = get_optimizer()
        logger.info("✓ OperationalOptimizer initialized")
        
        _ = get_telemetry_processor()
        logger.info("✓ TelemetryProcessor initialized")
        
        _ = get_simulation_orchestrator()
        logger.info("✓ SimulationOrchestrator initialized")
        
        _ = get_report_generator()
        logger.info("✓ ReportGenerator initialized")
        
        logger.info("✓ All Phase 5 services initialized successfully")
    except Exception as e:
        logger.error(f"✗ Service initialization failed: {e}")
        logger.warning("Application will continue but some features may not work")
    
    logger.info(f"API Documentation: http://localhost:8000/api/docs")
    if frontend_build_path.exists():
        logger.info(f"Unified React SPA is READY at: http://localhost:8000/")
    else:
        logger.warning(f"Frontend build folder not found at {frontend_build_path}. Please run 'npm run build'")
    logger.info("=" * 60)

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event handler"""
    logger.info("=" * 60)
    logger.info("Shutting down PetroFlow API...")
    
    # Phase 5: Reset service instances
    try:
        reset_service_instances()
        logger.info("✓ Service instances reset")
    except Exception as e:
        logger.error(f"Error resetting service instances: {e}")
    
    # Close database connections
    try:
        engine.dispose()
        logger.info("✓ Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
    
    logger.info("Shutdown complete")
    logger.info("=" * 60)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )