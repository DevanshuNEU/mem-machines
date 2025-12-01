"""
Worker Service - Route Handlers

Pub/Sub push handler that processes messages and stores results in Firestore.
"""

import structlog
from fastapi import APIRouter, HTTPException, status

from ..config import get_settings
from ..models import HealthResponse, ProcessedLog, PubSubPushRequest
from ..models.schemas import InternalMessage
from ..services import LogProcessor, get_firestore_service


logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check for load balancers."""
    settings = get_settings()
    return HealthResponse(service=settings.service_name, version="1.0.0")


@router.post("/", status_code=status.HTTP_200_OK, tags=["Processing"])
async def process_message(request: PubSubPushRequest) -> dict:
    """
    Process a Pub/Sub push message.
    
    Steps:
    1. Decode the base64 message
    2. Simulate heavy processing (delay based on text length)
    3. Redact PII (phone, email, SSN)
    4. Store in Firestore with tenant isolation
    
    Returns 200 to acknowledge message. Non-2xx triggers redelivery.
    """
    message_id = request.message.message_id
    
    logger.info("message_received", message_id=message_id)
    
    # Decode message
    try:
        data = request.message.decode_data()
        internal_message = InternalMessage(**data)
    except Exception as e:
        logger.error("message_decode_failed", message_id=message_id, error=str(e))
        # Return 200 to avoid infinite redelivery of malformed messages
        return {"status": "error", "message_id": message_id, "error": "Failed to decode message"}
    
    tenant_id = internal_message.tenant_id
    log_id = internal_message.log_id
    
    logger.info(
        "processing_message",
        message_id=message_id,
        tenant_id=tenant_id,
        log_id=log_id,
        text_length=len(internal_message.text),
    )
    
    # Process (simulated heavy work + PII redaction)
    try:
        processor = LogProcessor()
        modified_text = await processor.process(
            text=internal_message.text,
            log_id=log_id,
            tenant_id=tenant_id,
        )
    except Exception as e:
        logger.error("processing_failed", log_id=log_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Processing failed")
    
    # Create processed log document
    processed_log = ProcessedLog(
        source=internal_message.source,
        original_text=internal_message.text,
        modified_data=modified_text,
        ingested_at=internal_message.ingested_at,
        message_id=message_id,
    )
    
    # Store in Firestore (tenant isolation via subcollections)
    try:
        firestore_service = get_firestore_service()
        await firestore_service.save_processed_log(
            tenant_id=tenant_id,
            log_id=log_id,
            processed_log=processed_log,
        )
    except Exception as e:
        logger.error("storage_failed", log_id=log_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage failed")
    
    logger.info("message_processed_successfully", tenant_id=tenant_id, log_id=log_id)
    
    return {"status": "success", "message_id": message_id, "tenant_id": tenant_id, "log_id": log_id}
