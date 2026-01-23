import pytest
import json
from datetime import datetime, timedelta

from src.models import InventoryItem, Reservation, StockMovementType, ReservationStatus
from tests.conftest import create_test_inventory_item, create_test_reservation


class TestInventoryEndpoints:
    """Test inventory REST endpoints."""
    
    def test_get_inventory_by_sku(self, client, db_session):
        """Test getting inventory by SKU."""
        item = create_test_inventory_item(db_session, sku='GET001')
        
        response = client.get('/api/inventory/GET001')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['sku'] == 'GET001'
    
    def test_get_inventory_not_found(self, client, db_session):
        """Test getting non-existent inventory."""
        response = client.get('/api/inventory/NONEXISTENT')
        
        assert response.status_code == 404


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check_basic(self, client, db_session):
        """Test basic health check."""
        response = client.get('/health')
        
        # Should return some response (may be 200 or 503 depending on services)
        assert response.status_code in [200, 503]
        json_data = response.get_json()
        assert 'status' in json_data
    
    def test_liveness_check(self, client, db_session):
        """Test liveness probe."""
        response = client.get('/liveness')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert 'status' in json_data
        assert json_data['status'] == 'alive'
