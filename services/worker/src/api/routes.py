# =============================================================================
# Worker Service - Route Handlers
# =============================================================================
"""
API route handlers for the Worker service.

Implements the Pub/Sub push handler that receives messages,
processes them, and stores results in Firestore.
"""

import structlog
from fastapi import APIRouter, HTTPException, status

from ..config import get_settings
from ..models import (
    HealthResponse,
    ProcessedLog,
    PubSubPushRequest,
)
from ..models.schemas import InternalMessage
from ..services import FirestoreService, LogProcessor, get_firestore_service


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
# Pub/Sub Push Handler
# =============================================================================

@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    tags=["Processing"],
    summary="Process Pub/Sub message",
    description="""
    Receives and processes messages pushed from Pub/Sub.
    
    This endpoint:
    1. Decodes the base64-encoded message
    2. Simulates heavy processing (sleep proportional to text length)
    3. Transforms data (redacts sensitive information)
    4. Stores result in Firestore with tenant isolation
    
    **Important**: Returns 200 OK to acknowledge the message.
    Returning non-2xx will cause Pub/Sub to redeliver the message.
    """,
    responses={
        200: {"description": "Message processed successfully"},
        400: {"description": "Invalid message format"},
        500: {"description": "Processing or storage error"},
    },
)
async def process_message(request: PubSubPushRequest) -> dict:
    """
    Process a Pub/Sub push message.
    
    This is the main worker endpoint that:
    1. Decodes the incoming message
    2. Performs simulated heavy processing
    3. Stores results in Firestore
    
    Args:
        request: The Pub/Sub push request containing the message
        
    Returns:
        dict: Processing result confirmation
        
    Note:
        Returning 200 acknowledges the message to Pub/Sub.
        Any non-2xx response will cause redelivery.
    """
    message_id = request.message.message_id
    
    logger.info(
        "message_received",
        message_id=message_id,
        subscription=request.subscription,
    )
    
    # Decode the message data
    try:
        data = request.message.decode_data()
        internal_message = InternalMessage(**data)
    except Exception as e:
        logger.error(
            "message_decode_failed",
            message_id=message_id,
            error=str(e),
        )
        # Return 200 to avoid infinite redelivery of malformed messages
        # In production, you might want to dead-letter these instead
        return {
            "status": "error",
            "message_id": message_id,
            "error": "Failed to decode message",
        }
    
    tenant_id = internal_message.tenant_id
    log_id = internal_message.log_id
    
    logger.info(
        "processing_message",
        message_id=message_id,
        tenant_id=tenant_id,
        log_id=log_id,
        text_length=len(internal_message.text),
        source=internal_message.source,
    )
    
    # Process the log (simulated heavy work + transformation)
    try:
        processor = LogProcessor()
        modified_text = await processor.process(
            text=internal_message.text,
            log_id=log_id,
            tenant_id=tenant_id,
        )
    except Exception as e:
        logger.error(
            "processing_failed",
            message_id=message_id,
            tenant_id=tenant_id,
            log_id=log_id,
            error=str(e),
        )
        # Raise exception to trigger Pub/Sub redelivery
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Processing failed",
        )
    
    # Create the processed log document
    processed_log = ProcessedLog(
        source=internal_message.source,
        original_text=internal_message.text,
        modified_data=modified_text,
        ingested_at=internal_message.ingested_at,
        message_id=message_id,
    )
    
    # Store in Firestore with tenant isolation
    try:
        firestore_service = get_firestore_service()
        await firestore_service.save_processed_log(
            tenant_id=tenant_id,
            log_id=log_id,
            processed_log=processed_log,
        )
    except Exception as e:
        logger.error(
            "storage_failed",
            message_id=message_id,
            tenant_id=tenant_id,
            log_id=log_id,
            error=str(e),
        )
        # Raise exception to trigger Pub/Sub redelivery
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage failed",
        )
    
    logger.info(
        "message_processed_successfully",
        message_id=message_id,
        tenant_id=tenant_id,
        log_id=log_id,
    )
    
    return {
        "status": "success",
        "message_id": message_id,
        "tenant_id": tenant_id,
        "log_id": log_id,
    }
