"""
Integration tests for authentication and updated inventory endpoints
Tests admin authentication and new API features
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.models import InventoryItem, Reservation, ReservationStatus


class TestInventoryAuthenticationIntegration:
    """Test authentication on inventory endpoints."""
    
    @patch('src.middlewares.auth.decode_jwt')
    def test_create_inventory_requires_admin(self, mock_decode, client, db_session):
        """Test that creating inventory requires admin role."""
        # Mock admin JWT
        mock_decode.return_value = {
            'id': 'user-123',
            'email': 'admin@test.com',
            'roles': ['admin']
        }
        
        response = client.post(
            '/api/inventory/',
            headers={'Authorization': '****** valid-admin-token'},
            json={
                'sku': 'TEST-SKU-001',
                'quantity': 100
            }
        )
        
        assert response.status_code == 201
    
    def test_create_inventory_without_auth(self, client):
        """Test that creating inventory without auth fails."""
        response = client.post(
            '/api/inventory/',
            json={
                'sku': 'TEST-SKU-001',
                'quantity': 100
            }
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data or 'success' in data
    
    @patch('src.middlewares.auth.decode_jwt')
    def test_create_inventory_without_admin_role(self, mock_decode, client):
        """Test that non-admin cannot create inventory."""
        # Mock user JWT without admin role
        mock_decode.return_value = {
            'id': 'user-456',
            'email': 'user@test.com',
            'roles': ['user']
        }
        
        response = client.post(
            '/api/inventory/',
            headers={'Authorization': '****** valid-user-token'},
            json={
                'sku': 'TEST-SKU-001',
                'quantity': 100
            }
        )
        
        assert response.status_code == 403
    
    @patch('src.middlewares.auth.decode_jwt')
    def test_update_inventory_requires_admin(self, mock_decode, client, db_session):
        """Test that updating inventory requires admin role."""
        # Create test item
        item = InventoryItem(
            sku='UPDATE-SKU-001',
            quantity_available=50,
            quantity_reserved=0
        )
        db_session.add(item)
        db_session.commit()
        
        # Mock admin JWT
        mock_decode.return_value = {
            'id': 'admin-123',
            'email': 'admin@test.com',
            'roles': ['admin']
        }
        
        response = client.put(
            '/api/inventory/UPDATE-SKU-001',
            headers={'Authorization': '****** valid-admin-token'},
            json={'quantity': 75}
        )
        
        assert response.status_code == 200
    
    @patch('src.middlewares.auth.decode_jwt')
    def test_delete_inventory_requires_admin(self, mock_decode, client, db_session):
        """Test that deleting inventory requires admin role."""
        # Create test item
        item = InventoryItem(
            sku='DELETE-SKU-001',
            quantity_available=50,
            quantity_reserved=0
        )
        db_session.add(item)
        db_session.commit()
        
        # Mock admin JWT
        mock_decode.return_value = {
            'id': 'admin-123',
            'email': 'admin@test.com',
            'roles': ['admin']
        }
        
        response = client.delete(
            '/api/inventory/DELETE-SKU-001',
            headers={'Authorization': '****** valid-admin-token'}
        )
        
        assert response.status_code == 204


class TestInventoryBatchEndpointIntegration:
    """Test batch inventory endpoint with inStockOnly filter."""
    
    def test_batch_endpoint_all_items(self, client, db_session):
        """Test batch endpoint returns all items."""
        # Create test items
        items = [
            InventoryItem(sku='BATCH-001', quantity_available=10, quantity_reserved=0),
            InventoryItem(sku='BATCH-002', quantity_available=0, quantity_reserved=0),
            InventoryItem(sku='BATCH-003', quantity_available=5, quantity_reserved=2)
        ]
        for item in items:
            db_session.add(item)
        db_session.commit()
        
        response = client.post(
            '/api/inventory/batch',
            json={'skus': ['BATCH-001', 'BATCH-002', 'BATCH-003']}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 3
    
    def test_batch_endpoint_in_stock_only_query_param(self, client, db_session):
        """Test batch endpoint with inStockOnly query parameter."""
        # Create test items
        items = [
            InventoryItem(sku='STOCK-001', quantity_available=10, quantity_reserved=0),
            InventoryItem(sku='STOCK-002', quantity_available=0, quantity_reserved=0),
            InventoryItem(sku='STOCK-003', quantity_available=5, quantity_reserved=2)
        ]
        for item in items:
            db_session.add(item)
        db_session.commit()
        
        response = client.post(
            '/api/inventory/batch?inStockOnly=true',
            json={'skus': ['STOCK-001', 'STOCK-002', 'STOCK-003']}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        # Should only return items with quantity > 0
        assert len(data) == 2
        skus = [item['sku'] for item in data]
        assert 'STOCK-001' in skus
        assert 'STOCK-003' in skus
        assert 'STOCK-002' not in skus
    
    def test_batch_endpoint_in_stock_only_body_param(self, client, db_session):
        """Test batch endpoint with in_stock_only in request body."""
        # Create test items
        items = [
            InventoryItem(sku='BODY-001', quantity_available=10, quantity_reserved=0),
            InventoryItem(sku='BODY-002', quantity_available=0, quantity_reserved=0)
        ]
        for item in items:
            db_session.add(item)
        db_session.commit()
        
        response = client.post(
            '/api/inventory/batch',
            json={
                'skus': ['BODY-001', 'BODY-002'],
                'in_stock_only': True
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['sku'] == 'BODY-001'


class TestReservationEndpointsIntegration:
    """Test new reservation endpoints (release and confirm)."""
    
    def test_release_reservation_endpoint(self, client, db_session):
        """Test POST /api/inventory/reservations/{id}/release endpoint."""
        # Create test inventory and reservation
        item = InventoryItem(
            sku='RELEASE-SKU-001',
            quantity_available=90,
            quantity_reserved=10
        )
        db_session.add(item)
        db_session.commit()
        
        reservation = Reservation(
            sku='RELEASE-SKU-001',
            order_id='order-123',
            quantity=10,
            status=ReservationStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(reservation)
        db_session.commit()
        
        response = client.post(
            f'/api/reservations/{reservation.id}/release'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'Reservation released successfully'
        assert 'reservation' in data
    
    def test_release_nonexistent_reservation(self, client):
        """Test releasing nonexistent reservation returns 404."""
        response = client.post('/api/reservations/nonexistent-id/release')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_confirm_reservation_endpoint(self, client, db_session):
        """Test POST /api/inventory/reservations/{id}/confirm endpoint."""
        # Create test inventory and reservation
        item = InventoryItem(
            sku='CONFIRM-SKU-001',
            quantity_available=90,
            quantity_reserved=10
        )
        db_session.add(item)
        db_session.commit()
        
        reservation = Reservation(
            sku='CONFIRM-SKU-001',
            order_id='order-456',
            quantity=10,
            status=ReservationStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(reservation)
        db_session.commit()
        
        response = client.post(
            f'/api/reservations/{reservation.id}/confirm',
            json={'order_id': 'order-456'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'successfully' in data['message'].lower()
    
    def test_confirm_reservation_requires_order_id(self, client, db_session):
        """Test that confirm endpoint requires order_id."""
        # Create test reservation
        item = InventoryItem(
            sku='CONFIRM-SKU-002',
            quantity_available=90,
            quantity_reserved=10
        )
        db_session.add(item)
        db_session.commit()
        
        reservation = Reservation(
            sku='CONFIRM-SKU-002',
            order_id='order-789',
            quantity=10,
            status=ReservationStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(reservation)
        db_session.commit()
        
        response = client.post(
            f'/api/reservations/{reservation.id}/confirm',
            json={}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestStandardizedErrorResponsesIntegration:
    """Test standardized error responses."""
    
    def test_sku_not_found_error_format(self, client):
        """Test SKU not found returns standardized error."""
        response = client.get('/api/inventory/NONEXISTENT-SKU')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error']['code'] == 'SKU_NOT_FOUND'
        assert 'sku' in data['error']['details']
        assert 'timestamp' in data['error']
    
    def test_validation_error_format(self, client):
        """Test validation error returns standardized format."""
        response = client.post(
            '/api/inventory/batch',
            json={}  # Missing required 'skus' field
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error']['code'] == 'VALIDATION_ERROR'
    
    @patch('src.middlewares.auth.decode_jwt')
    def test_delete_returns_204(self, mock_decode, client, db_session):
        """Test that DELETE returns 204 No Content per PRD."""
        # Create test item
        item = InventoryItem(
            sku='DELETE-204-SKU',
            quantity_available=50,
            quantity_reserved=0
        )
        db_session.add(item)
        db_session.commit()
        
        # Mock admin JWT
        mock_decode.return_value = {
            'id': 'admin-123',
            'email': 'admin@test.com',
            'roles': ['admin']
        }
        
        response = client.delete(
            '/api/inventory/DELETE-204-SKU',
            headers={'Authorization': '****** valid-admin-token'}
        )
        
        assert response.status_code == 204
        assert response.data == b''  # No content
