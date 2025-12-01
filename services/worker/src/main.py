"""
Worker Service - Main Application

Processes messages from Pub/Sub, performs simulated heavy computation,
redacts PII, and stores results in Firestore.
"""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .config import get_settings


def configure_logging() -> None:
    """Configure structured logging for Cloud Logging compatibility."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging()
    
    app = FastAPI(
        title="Memory Machines Worker",
        description="Pub/Sub message processor with Firestore storage",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(router)
    
    logger = structlog.get_logger(__name__)
    logger.info(
        "application_startup",
        service=settings.service_name,
        project_id=settings.gcp_project_id,
    )
    
    return app


app = create_app()


@app.on_event("startup")
async def startup_event() -> None:
    """Log when application is ready."""
    logger = structlog.get_logger(__name__)
    logger.info("startup_complete")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Log when application is shutting down."""
    logger = structlog.get_logger(__name__)
    logger.info("shutdown_initiated")
