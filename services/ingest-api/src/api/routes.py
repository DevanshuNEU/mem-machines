"""
Ingest API - Route Handlers

Handles /ingest endpoint for both JSON and raw text payloads.
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


logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check for load balancers."""
    settings = get_settings()
    return HealthResponse(service=settings.service_name, version="1.0.0")


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Ingestion"])
async def ingest(
    request: Request,
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-ID"),
) -> IngestResponse:
    """
    Ingest log data (JSON or text format).
    
    JSON: Include tenant_id and text in body
    Text: Include X-Tenant-ID header, text in body
    """
    content_type = request.headers.get("content-type", "").lower()
    
    if "application/json" in content_type:
        return await _handle_json_payload(request)
    elif "text/plain" in content_type:
        return await _handle_text_payload(request, x_tenant_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported Content-Type: {content_type}. Use 'application/json' or 'text/plain'.",
        )


async def _handle_json_payload(request: Request) -> IngestResponse:
    """Process JSON payload."""
    try:
        body = await request.json()
    except Exception as e:
        logger.warning("invalid_json_body", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")
    
    try:
        payload = IngestRequest(**body)
    except Exception as e:
        logger.warning("json_validation_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    
    log_id = payload.log_id or generate_log_id()
    
    message = InternalMessage(
        tenant_id=payload.tenant_id,
        log_id=log_id,
        text=payload.text,
        source=SourceType.JSON_UPLOAD,
    )
    
    await _publish_message(message)
    return IngestResponse(log_id=log_id)


async def _handle_text_payload(request: Request, tenant_id: Optional[str]) -> IngestResponse:
    """Process text payload."""
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required for text/plain requests",
        )
    
    tenant_id = tenant_id.lower()
    if not all(c.isalnum() or c in "_-" for c in tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID must contain only alphanumeric characters, underscores, or hyphens",
        )
    
    try:
        text = (await request.body()).decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request body must be valid UTF-8")
    
    if not text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request body cannot be empty")
    
    log_id = generate_log_id()
    
    message = InternalMessage(
        tenant_id=tenant_id,
        log_id=log_id,
        text=text,
        source=SourceType.TEXT_UPLOAD,
    )
    
    await _publish_message(message)
    return IngestResponse(log_id=log_id)


async def _publish_message(message: InternalMessage) -> None:
    """Publish message to Pub/Sub."""
    publisher = get_publisher()
    
    try:
        await publisher.publish(message)
        logger.info(
            "ingest_successful",
            tenant_id=message.tenant_id,
            log_id=message.log_id,
            source=message.source.value,
        )
    except PubSubPublishError as e:
        logger.error("ingest_publish_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue data for processing",
        )
