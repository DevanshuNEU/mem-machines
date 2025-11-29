# =============================================================================
# Worker Service - Firestore Service
# =============================================================================
"""
Google Cloud Firestore service for multi-tenant data storage.

Handles storage of processed logs with strict tenant isolation
using the subcollection pattern:

    tenants/{tenant_id}/processed_logs/{log_id}
"""

from functools import lru_cache
from typing import Optional

import structlog
from google.cloud import firestore

from ..config import get_settings
from ..models import ProcessedLog


# Configure structured logger
logger = structlog.get_logger(__name__)


class FirestoreService:
    """
    Firestore service for multi-tenant document storage.
    
    Uses the subcollection pattern for tenant isolation:
    - Each tenant has their own document under 'tenants' collection
    - Processed logs are stored in a subcollection under each tenant
    
    This ensures physical separation of tenant data and enables
    efficient queries within a single tenant's data.
    
    Attributes:
        project_id: GCP project identifier
        _client: Firestore client instance
    """
    
    # Collection names
    TENANTS_COLLECTION = "tenants"
    PROCESSED_LOGS_SUBCOLLECTION = "processed_logs"
    
    def __init__(self, project_id: str) -> None:
        """
        Initialize the Firestore service.
        
        Args:
            project_id: GCP project identifier
        """
        self.project_id = project_id
        self._client: Optional[firestore.Client] = None
        
        logger.info(
            "firestore_service_initialized",
            project_id=project_id,
        )
    
    def _get_client(self) -> firestore.Client:
        """
        Lazily initialize the Firestore client.
        
        Returns:
            firestore.Client: Initialized Firestore client
        """
        if self._client is None:
            self._client = firestore.Client(project=self.project_id)
        return self._client
    
    async def save_processed_log(
        self,
        tenant_id: str,
        log_id: str,
        processed_log: ProcessedLog,
    ) -> None:
        """
        Save a processed log to Firestore.
        
        The document is stored at:
            tenants/{tenant_id}/processed_logs/{log_id}
        
        Using log_id as the document ID ensures idempotent writes:
        - If a message is redelivered and reprocessed, the same
          document will be overwritten with the same data
        - This handles crash recovery without creating duplicates
        
        Args:
            tenant_id: Tenant identifier (determines subcollection path)
            log_id: Log identifier (used as document ID)
            processed_log: The processed log data to store
        """
        client = self._get_client()
        
        # Build the document reference with multi-tenant path
        doc_ref = (
            client.collection(self.TENANTS_COLLECTION)
            .document(tenant_id)
            .collection(self.PROCESSED_LOGS_SUBCOLLECTION)
            .document(log_id)
        )
        
        # Convert to Firestore-compatible dict
        data = processed_log.to_firestore_dict()
        
        try:
            # Use set() for idempotent writes
            # This creates or overwrites the document
            doc_ref.set(data)
            
            logger.info(
                "document_saved",
                tenant_id=tenant_id,
                log_id=log_id,
                path=f"{self.TENANTS_COLLECTION}/{tenant_id}/{self.PROCESSED_LOGS_SUBCOLLECTION}/{log_id}",
            )
            
        except Exception as e:
            logger.error(
                "document_save_failed",
                tenant_id=tenant_id,
                log_id=log_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise FirestoreError(
                f"Failed to save document for tenant {tenant_id}, log {log_id}: {e}"
            ) from e
    
    async def get_processed_log(
        self,
        tenant_id: str,
        log_id: str,
    ) -> Optional[dict]:
        """
        Retrieve a processed log from Firestore.
        
        Args:
            tenant_id: Tenant identifier
            log_id: Log identifier
            
        Returns:
            Optional[dict]: Document data if exists, None otherwise
        """
        client = self._get_client()
        
        doc_ref = (
            client.collection(self.TENANTS_COLLECTION)
            .document(tenant_id)
            .collection(self.PROCESSED_LOGS_SUBCOLLECTION)
            .document(log_id)
        )
        
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        return None


class FirestoreError(Exception):
    """Custom exception for Firestore operations."""
    pass


@lru_cache
def get_firestore_service() -> FirestoreService:
    """
    Get cached Firestore service instance.
    
    Uses LRU cache to maintain a single service instance
    across all requests.
    
    Returns:
        FirestoreService: Configured Firestore service
    """
    settings = get_settings()
    return FirestoreService(project_id=settings.gcp_project_id)
