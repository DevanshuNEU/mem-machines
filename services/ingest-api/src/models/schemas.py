# =============================================================================
# Ingest API - Pydantic Schemas
# =============================================================================
"""
Request and response models for the Ingest API.

These models handle validation, serialization, and documentation
for all API endpoints.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    """Enumeration of supported data source types."""
    JSON_UPLOAD = "json_upload"
    TEXT_UPLOAD = "text_upload"


class IngestRequest(BaseModel):
    """
    Request model for JSON payload ingestion.
    
    Used when Content-Type is application/json.
    
    Attributes:
        tenant_id: Unique identifier for the tenant/organization
        log_id: Optional unique identifier for the log entry
        text: The log content to be processed
    
    Example:
        {
            "tenant_id": "acme_corp",
            "log_id": "log_12345",
            "text": "User 555-0199 accessed the system"
        }
    """
    
    tenant_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique identifier for the tenant",
        examples=["acme_corp", "beta_inc"],
    )
    log_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Optional unique identifier for the log entry",
        examples=["log_12345"],
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=1_000_000,  # 1MB text limit
        description="The log content to be processed",
        examples=["User 555-0199 accessed the system at 2024-01-15"],
    )
    
    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        """Validate tenant_id contains only safe characters."""
        # Allow alphanumeric, underscore, and hyphen
        if not all(c.isalnum() or c in "_-" for c in v):
            raise ValueError(
                "tenant_id must contain only alphanumeric characters, "
                "underscores, or hyphens"
            )
        return v.lower()  # Normalize to lowercase


class InternalMessage(BaseModel):
    """
    Internal message format for Pub/Sub publishing.
    
    This normalized format is used regardless of whether the
    original input was JSON or raw text.
    
    Attributes:
        tenant_id: Unique identifier for the tenant
        log_id: Unique identifier for the log entry
        text: The log content
        source: How the data was ingested
        ingested_at: Timestamp when data was received
    """
    
    tenant_id: str = Field(..., description="Tenant identifier")
    log_id: str = Field(..., description="Unique log identifier")
    text: str = Field(..., description="Log content")
    source: SourceType = Field(..., description="Data source type")
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Ingestion timestamp (UTC)",
    )
    
    def to_pubsub_data(self) -> bytes:
        """
        Serialize message for Pub/Sub publishing.
        
        Returns:
            bytes: UTF-8 encoded JSON representation
        """
        return self.model_dump_json().encode("utf-8")


class IngestResponse(BaseModel):
    """
    Response model for successful ingestion.
    
    Attributes:
        status: Always "accepted" for successful requests
        log_id: The assigned log identifier
        message: Human-readable status message
    """
    
    status: str = Field(
        default="accepted",
        description="Request status",
    )
    log_id: str = Field(
        ...,
        description="Assigned log identifier",
    )
    message: str = Field(
        default="Data queued for processing",
        description="Human-readable status message",
    )


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


def generate_log_id() -> str:
    """
    Generate a unique log identifier.
    
    Format: log_{uuid4_hex_prefix}
    
    Returns:
        str: Unique log identifier
    """
    return f"log_{uuid4().hex[:16]}"
