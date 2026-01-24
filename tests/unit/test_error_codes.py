"""
Unit tests for error codes module
Tests standardized error response creation
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from flask import Flask, g

from src.utils.error_codes import (
    ErrorCode,
    create_error_response,
    sku_not_found_error,
    insufficient_stock_error,
    sku_already_exists_error,
    reservation_not_found_error,
    validation_error
)


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    return app


class TestErrorCode:
    """Test ErrorCode constants."""
    
    def test_error_codes_exist(self):
        """Test that all required error codes are defined."""
        assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCode.INVALID_SKU == "INVALID_SKU"
        assert ErrorCode.INVALID_QUANTITY == "INVALID_QUANTITY"
        assert ErrorCode.UNAUTHORIZED == "UNAUTHORIZED"
        assert ErrorCode.FORBIDDEN == "FORBIDDEN"
        assert ErrorCode.SKU_NOT_FOUND == "SKU_NOT_FOUND"
        assert ErrorCode.RESERVATION_NOT_FOUND == "RESERVATION_NOT_FOUND"
        assert ErrorCode.INSUFFICIENT_STOCK == "INSUFFICIENT_STOCK"
        assert ErrorCode.RESERVATION_CONFLICT == "RESERVATION_CONFLICT"
        assert ErrorCode.SKU_ALREADY_EXISTS == "SKU_ALREADY_EXISTS"
        assert ErrorCode.RESERVATION_EXPIRED == "RESERVATION_EXPIRED"
        assert ErrorCode.INTERNAL_ERROR == "INTERNAL_ERROR"


class TestCreateErrorResponse:
    """Test create_error_response function."""
    
    def test_create_basic_error(self, app):
        """Test creating basic error response."""
        with app.app_context():
            response, status_code = create_error_response(
                code="TEST_ERROR",
                message="Test error message",
                status_code=400
            )
            
            assert status_code == 400
            assert response["error"]["code"] == "TEST_ERROR"
            assert response["error"]["message"] == "Test error message"
            assert "timestamp" in response["error"]
    
    def test_create_error_with_details(self, app):
        """Test creating error response with details."""
        with app.app_context():
            details = {"field": "value", "count": 42}
            response, status_code = create_error_response(
                code="TEST_ERROR",
                message="Test message",
                details=details,
                status_code=422
            )
            
            assert status_code == 422
            assert response["error"]["details"] == details
    
    def test_create_error_with_correlation_id(self, app):
        """Test error response includes correlation ID from context."""
        with app.app_context():
            g.correlation_id = "test-corr-123"
            
            response, status_code = create_error_response(
                code="TEST_ERROR",
                message="Test message"
            )
            
            assert response["error"]["correlation_id"] == "test-corr-123"
    
    def test_create_error_without_correlation_id(self, app):
        """Test error response when no correlation ID in context."""
        with app.app_context():
            response, status_code = create_error_response(
                code="TEST_ERROR",
                message="Test message"
            )
            
            # Should not have correlation_id if not set in g
            assert "correlation_id" not in response["error"]
    
    def test_error_timestamp_format(self, app):
        """Test that timestamp is in ISO 8601 format."""
        with app.app_context():
            response, _ = create_error_response(
                code="TEST_ERROR",
                message="Test message"
            )
            
            timestamp = response["error"]["timestamp"]
            assert timestamp.endswith("Z")
            # Verify it's valid ISO format
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


class TestErrorHelperFunctions:
    """Test error helper functions."""
    
    def test_sku_not_found_error(self, app):
        """Test SKU not found error helper."""
        with app.app_context():
            response, status_code = sku_not_found_error("TEST-SKU-001")
            
            assert status_code == 404
            assert response["error"]["code"] == ErrorCode.SKU_NOT_FOUND
            assert response["error"]["message"] == "SKU not found"
            assert response["error"]["details"]["sku"] == "TEST-SKU-001"
    
    def test_insufficient_stock_error(self, app):
        """Test insufficient stock error helper."""
        with app.app_context():
            response, status_code = insufficient_stock_error(
                sku="TEST-SKU-001",
                requested=10,
                available=5
            )
            
            assert status_code == 409
            assert response["error"]["code"] == ErrorCode.INSUFFICIENT_STOCK
            assert "Not enough stock available" in response["error"]["message"]
            assert response["error"]["details"]["sku"] == "TEST-SKU-001"
            assert response["error"]["details"]["requested"] == 10
            assert response["error"]["details"]["available"] == 5
    
    def test_sku_already_exists_error(self, app):
        """Test SKU already exists error helper."""
        with app.app_context():
            response, status_code = sku_already_exists_error("DUP-SKU-001")
            
            assert status_code == 409
            assert response["error"]["code"] == ErrorCode.SKU_ALREADY_EXISTS
            assert response["error"]["message"] == "SKU already exists"
            assert response["error"]["details"]["sku"] == "DUP-SKU-001"
    
    def test_reservation_not_found_error(self, app):
        """Test reservation not found error helper."""
        with app.app_context():
            response, status_code = reservation_not_found_error("res-123")
            
            assert status_code == 404
            assert response["error"]["code"] == ErrorCode.RESERVATION_NOT_FOUND
            assert response["error"]["message"] == "Reservation not found"
            assert response["error"]["details"]["reservation_id"] == "res-123"
    
    def test_validation_error_basic(self, app):
        """Test basic validation error helper."""
        with app.app_context():
            response, status_code = validation_error("Invalid input")
            
            assert status_code == 400
            assert response["error"]["code"] == ErrorCode.VALIDATION_ERROR
            assert response["error"]["message"] == "Invalid input"
    
    def test_validation_error_with_details(self, app):
        """Test validation error with details."""
        with app.app_context():
            details = {"field": "quantity", "error": "must be positive"}
            response, status_code = validation_error(
                "Validation failed",
                details
            )
            
            assert status_code == 400
            assert response["error"]["details"] == details
