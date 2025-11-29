# =============================================================================
# Worker Service - Log Processor
# =============================================================================
"""
Log processing service.

Handles the simulated "heavy" processing by sleeping proportionally
to the text length, then applying data transformations.
"""

import asyncio

import structlog

from ..config import get_settings
from ..models.schemas import redact_sensitive_data


# Configure structured logger
logger = structlog.get_logger(__name__)


class LogProcessor:
    """
    Log processing service that simulates heavy computation.
    
    The processing time is proportional to the text length:
    - 100 characters = 5 seconds (at default 0.05s per char)
    - 1000 characters = 50 seconds
    
    This demonstrates handling of long-running async tasks.
    
    Attributes:
        delay_per_char: Seconds to sleep per character
    """
    
    def __init__(self, delay_per_char: float = None) -> None:
        """
        Initialize the log processor.
        
        Args:
            delay_per_char: Custom delay per character (uses settings if None)
        """
        settings = get_settings()
        self.delay_per_char = delay_per_char or settings.processing_delay_per_char
        
        logger.info(
            "processor_initialized",
            delay_per_char=self.delay_per_char,
        )
    
    async def process(
        self,
        text: str,
        log_id: str,
        tenant_id: str,
    ) -> str:
        """
        Process log text with simulated heavy computation.
        
        Steps:
        1. Calculate processing time based on text length
        2. Sleep to simulate CPU-bound work
        3. Apply data transformations (redaction)
        
        Args:
            text: The original log text
            log_id: Log identifier for tracing
            tenant_id: Tenant identifier for tracing
            
        Returns:
            str: The processed/transformed text
        """
        text_length = len(text)
        processing_time = text_length * self.delay_per_char
        
        logger.info(
            "processing_started",
            log_id=log_id,
            tenant_id=tenant_id,
            text_length=text_length,
            estimated_time_seconds=processing_time,
        )
        
        # Simulate heavy processing with async sleep
        # This doesn't block the event loop, allowing the service
        # to handle other requests during processing
        await asyncio.sleep(processing_time)
        
        # Apply data transformation (redact sensitive info)
        modified_text = redact_sensitive_data(text)
        
        logger.info(
            "processing_completed",
            log_id=log_id,
            tenant_id=tenant_id,
            text_length=text_length,
            actual_time_seconds=processing_time,
            redacted=modified_text != text,
        )
        
        return modified_text
