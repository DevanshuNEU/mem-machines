# =============================================================================
# Worker Service - Main Application
# =============================================================================
"""
Memory Machines Worker Service

Processes messages from Pub/Sub, performs simulated heavy computation,
and stores results in Firestore with multi-tenant isolation.

Key Features:
- Pub/Sub push handler for event-driven processing
- Simulated heavy processing (0.05s per character)
- Multi-tenant Firestore storage with subcollections
- Idempotent writes for crash recovery

Author: Devanshu Chicholikar
"""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .config import get_settings


# =============================================================================
# Logging Configuration
# =============================================================================

def configure_logging() -> None:
    """
    Configure structured logging with structlog.
    
    Sets up JSON-formatted logs suitable for Cloud Logging
    and local development.
    """
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


# =============================================================================
# Application Factory
# =============================================================================

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()
    
    # Configure logging first
    configure_logging()
    
    # Create FastAPI app
    app = FastAPI(
        title="Memory Machines Worker Service",
        description="""
## Overview

Worker service for processing log data from the Memory Machines platform.

## Features

- **Pub/Sub Push Handler**: Receives messages via HTTP push
- **Heavy Processing Simulation**: 0.05s delay per character
- **Data Transformation**: Redacts sensitive information
- **Multi-tenant Storage**: Firestore with subcollection isolation

## Pub/Sub Integration

This service is triggered by Pub/Sub push subscriptions.
The endpoint expects the standard Pub/Sub push format.
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(router)
    
    # Log startup
    logger = structlog.get_logger(__name__)
    logger.info(
        "application_startup",
        service=settings.service_name,
        environment=settings.environment,
        project_id=settings.gcp_project_id,
        processing_delay=settings.processing_delay_per_char,
    )
    
    return app


# =============================================================================
# Application Instance
# =============================================================================

app = create_app()


# =============================================================================
# Startup & Shutdown Events
# =============================================================================

@app.on_event("startup")
async def startup_event() -> None:
    """
    Application startup handler.
    
    Performs initialization tasks.
    """
    logger = structlog.get_logger(__name__)
    logger.info("startup_complete", message="Worker ready to process messages")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Application shutdown handler.
    
    Performs cleanup tasks.
    """
    logger = structlog.get_logger(__name__)
    logger.info("shutdown_initiated", message="Worker shutting down")
