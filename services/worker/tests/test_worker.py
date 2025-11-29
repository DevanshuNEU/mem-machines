# =============================================================================
# Worker Service - Unit Tests
# =============================================================================
"""
Unit tests for the Worker service.

Tests cover:
- Pub/Sub message handling
- Data processing and transformation
- Firestore storage
- Error handling
"""

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.models.schemas import redact_sensitive_data


# =============================================================================
# Test Client Fixture
# =============================================================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def create_pubsub_message(data: dict) -> dict:
    """Helper to create a properly formatted Pub/Sub push message."""
    encoded_data = base64.b64encode(json.dumps(data).encode()).decode()
    return {
        "message": {
            "data": encoded_data,
            "messageId": "test_msg_123",
            "publishTime": "2024-01-15T10:00:00Z",
            "attributes": {
                "tenant_id": data.get("tenant_id", "test_tenant"),
                "source": data.get("source", "json_upload"),
            },
        },
        "subscription": "projects/test/subscriptions/test-sub",
    }


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthCheck:
    """Tests for the health check endpoint."""
    
    def test_health_check_returns_healthy(self, client):
        """Health check should return healthy status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "worker"
        assert "timestamp" in data


# =============================================================================
# Message Processing Tests
# =============================================================================

class TestMessageProcessing:
    """Tests for Pub/Sub message processing."""
    
    @patch("src.api.routes.get_firestore_service")
    @patch("src.api.routes.LogProcessor")
    def test_valid_message_returns_200(
        self,
        mock_processor_class,
        mock_get_firestore,
        client,
    ):
        """Valid Pub/Sub message should be processed and return 200."""
        # Setup mocks
        mock_processor = MagicMock()
        mock_processor.process = AsyncMock(return_value="Processed text")
        mock_processor_class.return_value = mock_processor
        
        mock_firestore = MagicMock()
        mock_firestore.save_processed_log = AsyncMock()
        mock_get_firestore.return_value = mock_firestore
        
        # Create message
        message_data = {
            "tenant_id": "acme_corp",
            "log_id": "log_12345",
            "text": "User 555-0199 accessed the system",
            "source": "json_upload",
            "ingested_at": "2024-01-15T10:00:00Z",
        }
        
        response = client.post(
            "/",
            json=create_pubsub_message(message_data),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["tenant_id"] == "acme_corp"
        assert data["log_id"] == "log_12345"
    
    def test_malformed_message_returns_200_with_error(self, client):
        """Malformed messages should return 200 to prevent infinite redelivery."""
        response = client.post(
            "/",
            json={
                "message": {
                    "data": "not_valid_base64!!!",
                    "messageId": "test_msg_123",
                },
                "subscription": "projects/test/subscriptions/test-sub",
            },
        )
        
        # Should still return 200 to ack the message
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"


# =============================================================================
# Data Transformation Tests
# =============================================================================

class TestRedaction:
    """Tests for sensitive data redaction."""
    
    def test_redacts_phone_numbers(self):
        """Phone numbers should be redacted."""
        text = "Call user at 555-0199 for support"
        result = redact_sensitive_data(text)
        
        assert "555-0199" not in result
        assert "[REDACTED]" in result
    
    def test_redacts_full_phone_numbers(self):
        """Full phone numbers with area code should be redacted."""
        text = "Contact: 123-456-7890"
        result = redact_sensitive_data(text)
        
        assert "123-456-7890" not in result
        assert "[REDACTED]" in result
    
    def test_redacts_phone_with_parens(self):
        """Phone numbers with parentheses should be redacted."""
        text = "Call (555) 123-4567"
        result = redact_sensitive_data(text)
        
        assert "(555) 123-4567" not in result
        assert "[REDACTED]" in result
    
    def test_redacts_email_addresses(self):
        """Email addresses should be redacted."""
        text = "Contact user at john.doe@example.com for help"
        result = redact_sensitive_data(text)
        
        assert "john.doe@example.com" not in result
        assert "[REDACTED]" in result
    
    def test_redacts_ssn(self):
        """Social Security Numbers should be redacted."""
        text = "User SSN is 123-45-6789"
        result = redact_sensitive_data(text)
        
        assert "123-45-6789" not in result
        assert "[REDACTED]" in result
    
    def test_preserves_non_sensitive_text(self):
        """Non-sensitive text should be preserved."""
        text = "User accessed the dashboard at 10:00 AM"
        result = redact_sensitive_data(text)
        
        assert result == text
    
    def test_multiple_redactions(self):
        """Multiple sensitive items should all be redacted."""
        text = "User john@test.com called 555-1234 with SSN 123-45-6789"
        result = redact_sensitive_data(text)
        
        assert "john@test.com" not in result
        assert "555-1234" not in result
        assert "123-45-6789" not in result
        assert result.count("[REDACTED]") == 3


# =============================================================================
# Firestore Path Tests
# =============================================================================

class TestMultiTenantPaths:
    """Tests for multi-tenant Firestore paths."""
    
    def test_firestore_service_uses_correct_path(self):
        """Firestore service should use correct tenant path."""
        from src.services.firestore import FirestoreService
        
        service = FirestoreService(project_id="test-project")
        
        # Verify collection names
        assert service.TENANTS_COLLECTION == "tenants"
        assert service.PROCESSED_LOGS_SUBCOLLECTION == "processed_logs"
