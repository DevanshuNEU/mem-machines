# =============================================================================
# Worker Service - Pydantic Schemas
# =============================================================================
"""
Request and response models for the Worker service.

Handles Pub/Sub push message format and Firestore document structure.
"""

import base64
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class PubSubMessage(BaseModel):
    """
    Pub/Sub message payload structure.
    
    The actual message content is base64-encoded in the 'data' field.
    
    Attributes:
        data: Base64-encoded message content
        message_id: Unique message identifier assigned by Pub/Sub
        publish_time: When the message was published
        attributes: Optional message attributes
    """
    
    data: str = Field(..., description="Base64-encoded message data")
    message_id: str = Field(
        alias="messageId",
        description="Pub/Sub message ID",
    )
    publish_time: Optional[str] = Field(
        default=None,
        alias="publishTime",
        description="Message publish timestamp",
    )
    attributes: Optional[Dict[str, str]] = Field(
        default=None,
        description="Message attributes",
    )
    
    def decode_data(self) -> Dict[str, Any]:
        """
        Decode the base64-encoded message data.
        
        Returns:
            Dict: Decoded JSON message content
            
        Raises:
            ValueError: If data cannot be decoded or parsed
        """
        try:
            decoded_bytes = base64.b64decode(self.data)
            decoded_str = decoded_bytes.decode("utf-8")
            return json.loads(decoded_str)
        except Exception as e:
            raise ValueError(f"Failed to decode message data: {e}")


class PubSubPushRequest(BaseModel):
    """
    Pub/Sub push subscription request format.
    
    This is the structure Pub/Sub sends to push endpoints.
    
    Attributes:
        message: The Pub/Sub message
        subscription: Full subscription resource name
    """
    
    message: PubSubMessage = Field(..., description="The Pub/Sub message")
    subscription: str = Field(..., description="Subscription resource name")


class InternalMessage(BaseModel):
    """
    Internal message format (decoded from Pub/Sub).
    
    This matches the format published by the Ingest API.
    """
    
    tenant_id: str
    log_id: str
    text: str
    source: str
    ingested_at: str


class ProcessedLog(BaseModel):
    """
    Firestore document structure for processed logs.
    
    Stored at: tenants/{tenant_id}/processed_logs/{log_id}
    
    Attributes:
        source: How the data was originally ingested
        original_text: The unmodified input text
        modified_data: The processed/transformed text
        processed_at: When processing completed
        ingested_at: When data was originally received
        message_id: Pub/Sub message ID for tracing
    """
    
    source: str = Field(..., description="Data source type")
    original_text: str = Field(..., description="Original input text")
    modified_data: str = Field(..., description="Processed text")
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Processing completion timestamp",
    )
    ingested_at: str = Field(..., description="Original ingestion timestamp")
    message_id: str = Field(..., description="Pub/Sub message ID")
    
    def to_firestore_dict(self) -> Dict[str, Any]:
        """
        Convert to Firestore-compatible dictionary.
        
        Returns:
            Dict: Document data for Firestore
        """
        return {
            "source": self.source,
            "original_text": self.original_text,
            "modified_data": self.modified_data,
            "processed_at": self.processed_at.isoformat(),
            "ingested_at": self.ingested_at,
            "message_id": self.message_id,
        }


class HealthResponse(BaseModel):
    """
    Response model for health check endpoint.
    
    Attributes:
        status: Service health status
        service: Service name
        version: Service version
        timestamp: Current server time
    """
    
    status: str = Field(default="healthy", description="Health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Current timestamp",
    )


def redact_sensitive_data(text: str) -> str:
    """
    Redact sensitive information from text.
    
    Currently redacts:
    - Phone numbers (various formats including 7-digit and 10-digit)
    - Email addresses
    - Social Security Numbers
    
    Args:
        text: The original text
        
    Returns:
        str: Text with sensitive data redacted
    """
    # 10-digit phone numbers (e.g., 555-555-0199, 555.555.0199, 5555550199)
    phone_10_pattern = r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'
    text = re.sub(phone_10_pattern, '[REDACTED]', text)
    
    # 7-digit phone numbers (e.g., 555-0199, 555.0199)
    phone_7_pattern = r'\b\d{3}[-.\s]?\d{4}\b'
    text = re.sub(phone_7_pattern, '[REDACTED]', text)
    
    # Phone with area code in parens (e.g., (555) 555-0199)
    phone_parens_pattern = r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}'
    text = re.sub(phone_parens_pattern, '[REDACTED]', text)
    
    # Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    text = re.sub(email_pattern, '[REDACTED]', text)
    
    # SSN (e.g., 123-45-6789)
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    text = re.sub(ssn_pattern, '[REDACTED]', text)
    
    return text
