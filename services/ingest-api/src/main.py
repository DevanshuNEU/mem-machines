# =============================================================================
# Ingest API - Main Application
# =============================================================================
"""
Memory Machines Ingest API

A high-throughput data ingestion gateway that accepts JSON and text payloads,
normalizes them to a consistent internal format, and publishes them to
Google Cloud Pub/Sub for asynchronous processing.

Key Features:
- Non-blocking: Returns 202 Accepted immediately
- Multi-format: Supports both JSON and raw text inputs
- Validated: Strict input validation with Pydantic
- Observable: Structured logging for debugging and monitoring

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
    settings = get_settings()
    
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
        title="Memory Machines Ingest API",
        description="""
## Overview

High-throughput data ingestion gateway for the Memory Machines platform.

## Features

- **Multi-format Input**: Accepts both JSON and raw text payloads
- **Non-blocking**: Returns 202 Accepted immediately after queuing
- **Multi-tenant**: Strict tenant isolation via tenant_id
- **Fault-tolerant**: Pub/Sub ensures at-least-once delivery

## Authentication

This API is currently public for assessment purposes.
In production, implement proper authentication.
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
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
        topic=settings.pubsub_topic,
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
    
    Performs initialization tasks like warming up connections.
    """
    logger = structlog.get_logger(__name__)
    logger.info("startup_complete", message="Ingest API ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Application shutdown handler.
    
    Performs cleanup tasks like closing connections.
    """
    logger = structlog.get_logger(__name__)
    logger.info("shutdown_initiated", message="Ingest API shutting down")
