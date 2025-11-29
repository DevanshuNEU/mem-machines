# =============================================================================
# Ingest API - Unit Tests
# =============================================================================
"""
Unit tests for the Ingest API service.

Tests cover:
- JSON payload ingestion
- Text payload ingestion
- Input validation
- Error handling
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.models import InternalMessage, SourceType


# =============================================================================
# Test Client Fixture
# =============================================================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


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
        assert data["service"] == "ingest-api"
        assert "timestamp" in data


# =============================================================================
# JSON Ingestion Tests
# =============================================================================

class TestJsonIngestion:
    """Tests for JSON payload ingestion."""
    
    @patch("src.api.routes.get_publisher")
    def test_valid_json_payload_returns_202(self, mock_get_publisher, client):
        """Valid JSON payload should return 202 Accepted."""
        # Setup mock
        mock_publisher = AsyncMock()
        mock_publisher.publish = AsyncMock(return_value="msg_123")
        mock_get_publisher.return_value = mock_publisher
        
        response = client.post(
            "/ingest",
            json={
                "tenant_id": "acme_corp",
                "log_id": "log_12345",
                "text": "User 555-0199 accessed the system",
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["log_id"] == "log_12345"
    
    @patch("src.api.routes.get_publisher")
    def test_json_without_log_id_generates_one(self, mock_get_publisher, client):
        """JSON payload without log_id should auto-generate one."""
        mock_publisher = AsyncMock()
        mock_publisher.publish = AsyncMock(return_value="msg_123")
        mock_get_publisher.return_value = mock_publisher
        
        response = client.post(
            "/ingest",
            json={
                "tenant_id": "acme_corp",
                "text": "Some log content",
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["log_id"].startswith("log_")
    
    def test_json_missing_tenant_id_returns_422(self, client):
        """JSON payload without tenant_id should return 422."""
        response = client.post(
            "/ingest",
            json={
                "text": "Some log content",
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 422
    
    def test_json_missing_text_returns_422(self, client):
        """JSON payload without text should return 422."""
        response = client.post(
            "/ingest",
            json={
                "tenant_id": "acme_corp",
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 422
    
    def test_json_invalid_tenant_id_format_returns_422(self, client):
        """JSON with invalid tenant_id format should return 422."""
        response = client.post(
            "/ingest",
            json={
                "tenant_id": "acme/corp",  # Invalid character
                "text": "Some content",
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 422


# =============================================================================
# Text Ingestion Tests
# =============================================================================

class TestTextIngestion:
    """Tests for raw text payload ingestion."""
    
    @patch("src.api.routes.get_publisher")
    def test_valid_text_payload_returns_202(self, mock_get_publisher, client):
        """Valid text payload with X-Tenant-ID should return 202."""
        mock_publisher = AsyncMock()
        mock_publisher.publish = AsyncMock(return_value="msg_123")
        mock_get_publisher.return_value = mock_publisher
        
        response = client.post(
            "/ingest",
            content="User 555-0199 accessed the system",
            headers={
                "Content-Type": "text/plain",
                "X-Tenant-ID": "acme_corp",
            },
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["log_id"].startswith("log_")
    
    def test_text_without_tenant_id_header_returns_400(self, client):
        """Text payload without X-Tenant-ID header should return 400."""
        response = client.post(
            "/ingest",
            content="Some log content",
            headers={"Content-Type": "text/plain"},
        )
        
        assert response.status_code == 400
        assert "X-Tenant-ID" in response.json()["detail"]
    
    def test_text_empty_body_returns_400(self, client):
        """Empty text body should return 400."""
        response = client.post(
            "/ingest",
            content="",
            headers={
                "Content-Type": "text/plain",
                "X-Tenant-ID": "acme_corp",
            },
        )
        
        assert response.status_code == 400
    
    def test_text_invalid_tenant_id_returns_400(self, client):
        """Text with invalid X-Tenant-ID should return 400."""
        response = client.post(
            "/ingest",
            content="Some content",
            headers={
                "Content-Type": "text/plain",
                "X-Tenant-ID": "acme/corp",  # Invalid character
            },
        )
        
        assert response.status_code == 400


# =============================================================================
# Content-Type Tests
# =============================================================================

class TestContentType:
    """Tests for Content-Type handling."""
    
    def test_unsupported_content_type_returns_400(self, client):
        """Unsupported Content-Type should return 400."""
        response = client.post(
            "/ingest",
            content="some data",
            headers={"Content-Type": "application/xml"},
        )
        
        assert response.status_code == 400
        assert "Unsupported Content-Type" in response.json()["detail"]


# =============================================================================
# Model Tests
# =============================================================================

class TestInternalMessage:
    """Tests for the InternalMessage model."""
    
    def test_to_pubsub_data_returns_bytes(self):
        """to_pubsub_data should return UTF-8 encoded JSON."""
        message = InternalMessage(
            tenant_id="acme_corp",
            log_id="log_123",
            text="Test content",
            source=SourceType.JSON_UPLOAD,
        )
        
        data = message.to_pubsub_data()
        
        assert isinstance(data, bytes)
        assert b"acme_corp" in data
        assert b"log_123" in data
