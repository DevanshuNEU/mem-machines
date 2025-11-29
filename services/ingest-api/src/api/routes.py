# =============================================================================
# Ingest API - Route Handlers
# =============================================================================
"""
API route handlers for the Ingest API.

Implements the /ingest endpoint that handles both JSON and raw text
payloads, normalizing them and publishing to Pub/Sub.
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Header, HTTPException, Request, status

from ..config import get_settings
from ..models import (
    HealthResponse,
    IngestRequest,
    IngestResponse,
    InternalMessage,
    SourceType,
)
from ..models.schemas import generate_log_id
from ..services import PubSubPublishError, get_publisher


# Configure structured logger
logger = structlog.get_logger(__name__)

# Create router
router = APIRouter()


# =============================================================================
# Health Check Endpoint
# =============================================================================

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint",
    description="Returns the service health status.",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint for load balancers and orchestrators.
    
    Returns:
        HealthResponse: Service health status
    """
    settings = get_settings()
    return HealthResponse(
        service=settings.service_name,
        version="1.0.0",
    )


# =============================================================================
# Ingest Endpoint
# =============================================================================

@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Ingestion"],
    summary="Ingest log data",
    description="""
    Ingest log data in either JSON or raw text format.
    
    **JSON Format:**
    - Content-Type: application/json
    - Body: {"tenant_id": "...", "log_id": "...", "text": "..."}
    
    **Text Format:**
    - Content-Type: text/plain
    - Header: X-Tenant-ID: <tenant_id>
    - Body: Raw text content
    
    Returns 202 Accepted immediately after queuing the data for processing.
    """,
    responses={
        202: {
            "description": "Data accepted and queued for processing",
            "content": {
                "application/json": {
                    "example": {
                        "status": "accepted",
                        "log_id": "log_abc123def456",
                        "message": "Data queued for processing",
                    }
                }
            },
        },
        400: {"description": "Invalid request format or missing required fields"},
        422: {"description": "Validation error in request body"},
        500: {"description": "Internal server error during processing"},
    },
)
async def ingest(
    request: Request,
    x_tenant_id: Optional[str] = Header(
        default=None,
        alias="X-Tenant-ID",
        description="Tenant ID for text/plain requests",
    ),
) -> IngestResponse:
    """
    Unified ingestion endpoint for JSON and text payloads.
    
    Handles two scenarios:
    1. JSON payload (Content-Type: application/json)
       - tenant_id and text from body
       - log_id optional in body
       
    2. Raw text payload (Content-Type: text/plain)
       - tenant_id from X-Tenant-ID header
       - text from body
       - log_id auto-generated
    
    Args:
        request: The incoming HTTP request
        x_tenant_id: Tenant ID header for text payloads
        
    Returns:
        IngestResponse: Confirmation of data acceptance
        
    Raises:
        HTTPException: If request validation fails or publishing errors
    """
    content_type = request.headers.get("content-type", "").lower()
    
    # Route based on Content-Type
    if "application/json" in content_type:
        return await _handle_json_payload(request)
    elif "text/plain" in content_type:
        return await _handle_text_payload(request, x_tenant_id)
    else:
        logger.warning(
            "unsupported_content_type",
            content_type=content_type,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported Content-Type: {content_type}. "
                   f"Use 'application/json' or 'text/plain'.",
        )


async def _handle_json_payload(request: Request) -> IngestResponse:
    """
    Handle JSON payload ingestion.
    
    Args:
        request: The incoming HTTP request with JSON body
        
    Returns:
        IngestResponse: Confirmation response
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.warning("invalid_json_body", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        )
    
    # Validate with Pydantic model
    try:
        payload = IngestRequest(**body)
    except Exception as e:
        logger.warning("json_validation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    
    # Generate log_id if not provided
    log_id = payload.log_id or generate_log_id()
    
    # Create internal message
    message = InternalMessage(
        tenant_id=payload.tenant_id,
        log_id=log_id,
        text=payload.text,
        source=SourceType.JSON_UPLOAD,
    )
    
    # Publish to Pub/Sub
    await _publish_message(message)
    
    return IngestResponse(log_id=log_id)


async def _handle_text_payload(
    request: Request,
    tenant_id: Optional[str],
) -> IngestResponse:
    """
    Handle raw text payload ingestion.
    
    Args:
        request: The incoming HTTP request with text body
        tenant_id: Tenant ID from X-Tenant-ID header
        
    Returns:
        IngestResponse: Confirmation response
    """
    # Validate tenant_id header
    if not tenant_id:
        logger.warning("missing_tenant_id_header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required for text/plain requests",
        )
    
    # Validate tenant_id format
    tenant_id = tenant_id.lower()
    if not all(c.isalnum() or c in "_-" for c in tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID must contain only alphanumeric characters, "
                   "underscores, or hyphens",
        )
    
    # Read text body
    try:
        text = (await request.body()).decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be valid UTF-8 text",
        )
    
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body cannot be empty",
        )
    
    # Generate log_id for text uploads
    log_id = generate_log_id()
    
    # Create internal message
    message = InternalMessage(
        tenant_id=tenant_id,
        log_id=log_id,
        text=text,
        source=SourceType.TEXT_UPLOAD,
    )
    
    # Publish to Pub/Sub
    await _publish_message(message)
    
    return IngestResponse(log_id=log_id)


async def _publish_message(message: InternalMessage) -> None:
    """
    Publish message to Pub/Sub.
    
    Args:
        message: The normalized message to publish
        
    Raises:
        HTTPException: If publishing fails
    """
    publisher = get_publisher()
    
    try:
        await publisher.publish(message)
        
        logger.info(
            "ingest_successful",
            tenant_id=message.tenant_id,
            log_id=message.log_id,
            source=message.source.value,
            text_length=len(message.text),
        )
        
    except PubSubPublishError as e:
        logger.error(
            "ingest_publish_failed",
            tenant_id=message.tenant_id,
            log_id=message.log_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue data for processing",
        )
