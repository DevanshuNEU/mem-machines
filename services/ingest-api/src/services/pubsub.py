# =============================================================================
# Ingest API - Pub/Sub Publisher Service
# =============================================================================
"""
Google Cloud Pub/Sub publisher service.

Handles publishing messages to Pub/Sub with proper error handling,
retries, and structured logging.
"""

import asyncio
from functools import lru_cache
from typing import Optional

import structlog
from google.cloud import pubsub_v1
from google.api_core import exceptions as gcp_exceptions

from ..config import get_settings
from ..models import InternalMessage


# Configure structured logger
logger = structlog.get_logger(__name__)


class PubSubPublisher:
    """
    Async-compatible Pub/Sub publisher.
    
    Wraps the synchronous Google Cloud Pub/Sub client in an
    async-friendly interface suitable for FastAPI.
    
    Attributes:
        project_id: GCP project identifier
        topic_id: Pub/Sub topic name
        _publisher: Underlying synchronous publisher client
        _topic_path: Full topic resource path
    """
    
    def __init__(
        self,
        project_id: str,
        topic_id: str,
    ) -> None:
        """
        Initialize the Pub/Sub publisher.
        
        Args:
            project_id: GCP project identifier
            topic_id: Pub/Sub topic name
        """
        self.project_id = project_id
        self.topic_id = topic_id
        self._publisher: Optional[pubsub_v1.PublisherClient] = None
        self._topic_path: Optional[str] = None
        
        logger.info(
            "pubsub_publisher_initialized",
            project_id=project_id,
            topic_id=topic_id,
        )
    
    def _get_publisher(self) -> pubsub_v1.PublisherClient:
        """
        Lazily initialize the publisher client.
        
        Returns:
            PublisherClient: Initialized Pub/Sub publisher
        """
        if self._publisher is None:
            self._publisher = pubsub_v1.PublisherClient()
            self._topic_path = self._publisher.topic_path(
                self.project_id,
                self.topic_id,
            )
        return self._publisher
    
    async def publish(self, message: InternalMessage) -> str:
        """
        Publish a message to Pub/Sub asynchronously.
        
        Runs the synchronous publish operation in a thread pool
        to avoid blocking the event loop.
        
        Args:
            message: The normalized message to publish
            
        Returns:
            str: The message ID assigned by Pub/Sub
            
        Raises:
            PubSubPublishError: If publishing fails after retries
        """
        publisher = self._get_publisher()
        data = message.to_pubsub_data()
        
        # Add message attributes for filtering/routing
        attributes = {
            "tenant_id": message.tenant_id,
            "source": message.source.value,
        }
        
        try:
            # Run synchronous publish in thread pool
            loop = asyncio.get_event_loop()
            future = await loop.run_in_executor(
                None,
                lambda: publisher.publish(
                    self._topic_path,
                    data=data,
                    **attributes,
                ),
            )
            
            # Wait for publish confirmation
            message_id = await loop.run_in_executor(
                None,
                future.result,
            )
            
            logger.info(
                "message_published",
                message_id=message_id,
                tenant_id=message.tenant_id,
                log_id=message.log_id,
                text_length=len(message.text),
                source=message.source.value,
            )
            
            return message_id
            
        except gcp_exceptions.NotFound as e:
            logger.error(
                "pubsub_topic_not_found",
                topic_path=self._topic_path,
                error=str(e),
            )
            raise PubSubPublishError(
                f"Topic not found: {self._topic_path}"
            ) from e
            
        except gcp_exceptions.PermissionDenied as e:
            logger.error(
                "pubsub_permission_denied",
                topic_path=self._topic_path,
                error=str(e),
            )
            raise PubSubPublishError(
                "Permission denied for Pub/Sub publish"
            ) from e
            
        except Exception as e:
            logger.error(
                "pubsub_publish_failed",
                topic_path=self._topic_path,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PubSubPublishError(
                f"Failed to publish message: {str(e)}"
            ) from e


class PubSubPublishError(Exception):
    """Custom exception for Pub/Sub publishing failures."""
    pass


@lru_cache
def get_publisher() -> PubSubPublisher:
    """
    Get cached Pub/Sub publisher instance.
    
    Uses LRU cache to maintain a single publisher instance
    across all requests.
    
    Returns:
        PubSubPublisher: Configured publisher instance
    """
    settings = get_settings()
    return PubSubPublisher(
        project_id=settings.gcp_project_id,
        topic_id=settings.pubsub_topic,
    )
