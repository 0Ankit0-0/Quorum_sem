"""
FastAPI Application
Main API application setup
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routes import (
    logs,
    analysis,
    queries,
    reports,
    updates,
    system,
    devices,
    hub,
    stream,
    cli,
)
from config.settings import settings
from config.logging_config import setup_logging, get_logger

# Setup logging
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_format=settings.LOG_FORMAT,
    log_file=settings.LOG_FILE,
    log_dir=settings.LOGS_DIR
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} API v{settings.APP_VERSION}")
    
    # Initialize MITRE data if needed
    try:
        from services.mitre_service import mitre_service
        from core.database import db
        
        technique_count = db.get_table_count('mitre_techniques')
        if technique_count == 0:
            logger.info("Loading MITRE ATT&CK data...")
            mitre_service.load_mitre_data()
    except Exception as e:
        logger.warning(f"MITRE data initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API")
    from core.database import db
    db.close()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Log Analysis for Secure Offline Environments",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(system.router)
app.include_router(logs.router)
app.include_router(analysis.router)
app.include_router(queries.router)
app.include_router(reports.router)
app.include_router(updates.router)
app.include_router(devices.router)
app.include_router(hub.router)
app.include_router(stream.router)
app.include_router(cli.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        workers=settings.API_WORKERS
    )
