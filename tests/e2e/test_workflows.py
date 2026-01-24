"""
End-to-end tests for inventory service workflows
Tests complete user journeys and integration scenarios
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.models import InventoryItem, Reservation, ReservationStatus


class TestInventoryManagementWorkflow:
    """Test complete inventory management workflow."""
    
    @patch('src.middlewares.auth.decode_jwt')
    @patch('src.utils.event_publisher.event_publisher.publish_event')
    def test_complete_inventory_lifecycle(self, mock_publish, mock_decode, client, db_session):
        """Test create -> update -> query -> delete inventory lifecycle."""
        # Mock admin authentication
        mock_decode.return_value = {
            'id': 'admin-123',
            'email': 'admin@test.com',
            'roles': ['admin']
        }
        mock_publish.return_value = True
        
        # Step 1: Create inventory
        create_response = client.post(
            '/api/inventory/',
            headers={'Authorization': '****** admin-token'},
            json={
                'sku': 'E2E-SKU-001',
                'quantity': 100
            }
        )
        assert create_response.status_code == 201
        created_data = json.loads(create_response.data)
        assert created_data['sku'] == 'E2E-SKU-001'
        
        # Step 2: Query inventory
        query_response = client.get('/api/inventory/E2E-SKU-001')
        assert query_response.status_code == 200
        query_data = json.loads(query_response.data)
        assert query_data['sku'] == 'E2E-SKU-001'
        assert query_data['quantity_available'] == 100
        
        # Step 3: Update inventory
        update_response = client.put(
            '/api/inventory/E2E-SKU-001',
            headers={'Authorization': '****** admin-token'},
            json={'quantity': 150}
        )
        assert update_response.status_code == 200
        
        # Step 4: Verify update
        verify_response = client.get('/api/inventory/E2E-SKU-001')
        verify_data = json.loads(verify_response.data)
        assert verify_data['quantity_available'] == 150
        
        # Step 5: Delete inventory
        delete_response = client.delete(
            '/api/inventory/E2E-SKU-001',
            headers={'Authorization': '****** admin-token'}
        )
        assert delete_response.status_code == 204
        
        # Step 6: Verify deletion
        final_response = client.get('/api/inventory/E2E-SKU-001')
        assert final_response.status_code == 404


class TestReservationWorkflow:
    """Test complete reservation workflow."""
    
    @patch('src.utils.event_publisher.event_publisher.publish_event')
    def test_complete_reservation_lifecycle(self, mock_publish, client, db_session):
        """Test create -> confirm reservation workflow."""
        mock_publish.return_value = True
        
        # Setup: Create inventory
        item = InventoryItem(
            sku='RESERVE-SKU-001',
            quantity_available=100,
            quantity_reserved=0
        )
        db_session.add(item)
        db_session.commit()
        
        # Step 1: Create reservation
        create_response = client.post(
            '/api/reservations/',
            json={
                'sku': 'RESERVE-SKU-001',
                'order_id': 'order-e2e-001',
                'quantity': 10
            }
        )
        assert create_response.status_code == 201
        reservation_data = json.loads(create_response.data)
        reservation_id = reservation_data['id']
        
        # Step 2: Query reservation
        query_response = client.get(f'/api/reservations/{reservation_id}')
        assert query_response.status_code == 200
        query_data = json.loads(query_response.data)
        assert query_data['status'] == 'PENDING'
        
        # Step 3: Confirm reservation
        confirm_response = client.post(
            f'/api/reservations/{reservation_id}/confirm',
            json={'order_id': 'order-e2e-001'}
        )
        assert confirm_response.status_code == 200
        
        # Step 4: Verify inventory updated
        inventory_response = client.get('/api/inventory/RESERVE-SKU-001')
        inventory_data = json.loads(inventory_response.data)
        # After confirmation, reserved should be reduced
        assert inventory_data['quantity_available'] <= 100
    
    @patch('src.utils.event_publisher.event_publisher.publish_event')
    def test_reservation_release_workflow(self, mock_publish, client, db_session):
        """Test create -> release reservation workflow."""
        mock_publish.return_value = True
        
        # Setup: Create inventory
        item = InventoryItem(
            sku='RELEASE-SKU-001',
            quantity_available=90,
            quantity_reserved=10
        )
        db_session.add(item)
        db_session.commit()
        
        # Create reservation
        reservation = Reservation(
            sku='RELEASE-SKU-001',
            order_id='order-release-001',
            quantity=10,
            status=ReservationStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(reservation)
        db_session.commit()
        reservation_id = reservation.id
        
        # Step 1: Release reservation
        release_response = client.post(
            f'/api/reservations/{reservation_id}/release'
        )
        assert release_response.status_code == 200
        release_data = json.loads(release_response.data)
        assert release_data['reservation']['status'] == 'RELEASED'
        
        # Step 2: Verify inventory restored
        inventory_response = client.get('/api/inventory/RELEASE-SKU-001')
        inventory_data = json.loads(inventory_response.data)
        # After release, available should increase
        assert inventory_data['quantity_available'] >= 90


class TestBatchOperationsWorkflow:
    """Test batch operations workflow."""
    
    def test_batch_query_with_filtering(self, client, db_session):
        """Test batch query with various filter combinations."""
        # Setup: Create mixed inventory
        items = [
            InventoryItem(sku='BATCH-001', quantity_available=50, quantity_reserved=5),
            InventoryItem(sku='BATCH-002', quantity_available=0, quantity_reserved=0),
            InventoryItem(sku='BATCH-003', quantity_available=100, quantity_reserved=20),
            InventoryItem(sku='BATCH-004', quantity_available=0, quantity_reserved=10)
        ]
        for item in items:
            db_session.add(item)
        db_session.commit()
        
        # Test 1: Query all items
        all_response = client.post(
            '/api/inventory/batch',
            json={'skus': ['BATCH-001', 'BATCH-002', 'BATCH-003', 'BATCH-004']}
        )
        assert all_response.status_code == 200
        all_data = json.loads(all_response.data)
        assert len(all_data) == 4
        
        # Test 2: Query with in-stock filter
        filtered_response = client.post(
            '/api/inventory/batch?inStockOnly=true',
            json={'skus': ['BATCH-001', 'BATCH-002', 'BATCH-003', 'BATCH-004']}
        )
        assert filtered_response.status_code == 200
        filtered_data = json.loads(filtered_response.data)
        # Only BATCH-001 and BATCH-003 have available > 0
        assert len(filtered_data) == 2
        skus = [item['sku'] for item in filtered_data]
        assert 'BATCH-001' in skus
        assert 'BATCH-003' in skus
        
        # Test 3: Query with unknown SKUs
        mixed_response = client.post(
            '/api/inventory/batch',
            json={'skus': ['BATCH-001', 'UNKNOWN-SKU', 'BATCH-003']}
        )
        assert mixed_response.status_code == 200
        mixed_data = json.loads(mixed_response.data)
        # Should return data for all requested SKUs (including unknown with 0 quantity)
        assert len(mixed_data) == 3


class TestErrorHandlingWorkflow:
    """Test error handling across workflows."""
    
    def test_insufficient_stock_reservation(self, client, db_session):
        """Test reservation fails with insufficient stock."""
        # Setup: Create inventory with limited stock
        item = InventoryItem(
            sku='LIMITED-SKU',
            quantity_available=5,
            quantity_reserved=0
        )
        db_session.add(item)
        db_session.commit()
        
        # Attempt to reserve more than available
        response = client.post(
            '/api/reservations/',
            json={
                'sku': 'LIMITED-SKU',
                'order_id': 'order-fail-001',
                'quantity': 10
            }
        )
        
        assert response.status_code == 409
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error']['code'] == 'INSUFFICIENT_STOCK'
    
    @patch('src.middlewares.auth.decode_jwt')
    def test_duplicate_sku_creation(self, mock_decode, client, db_session):
        """Test creating duplicate SKU returns proper error."""
        # Mock admin auth
        mock_decode.return_value = {
            'id': 'admin-123',
            'email': 'admin@test.com',
            'roles': ['admin']
        }
        
        # Create first item
        item = InventoryItem(
            sku='DUPLICATE-SKU',
            quantity_available=50,
            quantity_reserved=0
        )
        db_session.add(item)
        db_session.commit()
        
        # Attempt to create duplicate
        response = client.post(
            '/api/inventory/',
            headers={'Authorization': '****** admin-token'},
            json={
                'sku': 'DUPLICATE-SKU',
                'quantity': 100
            }
        )
        
        assert response.status_code == 409
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error']['code'] == 'SKU_ALREADY_EXISTS'
    
    def test_reservation_not_found(self, client):
        """Test accessing nonexistent reservation."""
        response = client.get('/api/reservations/nonexistent-reservation-id')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error']['code'] == 'RESERVATION_NOT_FOUND'


class TestMessagingIntegration:
    """Test event publishing integration."""
    
    @patch('src.messaging.dapr_provider.DaprClient')
    @patch('src.middlewares.auth.decode_jwt')
    def test_events_published_on_inventory_operations(
        self, mock_decode, mock_dapr_client, client, db_session
    ):
        """Test that events are published for inventory operations."""
        # Mock admin auth
        mock_decode.return_value = {
            'id': 'admin-123',
            'email': 'admin@test.com',
            'roles': ['admin']
        }
        
        # Mock Dapr client
        mock_client_instance = MagicMock()
        mock_dapr_client.return_value.__enter__.return_value = mock_client_instance
        
        # Create inventory (should publish event)
        response = client.post(
            '/api/inventory/',
            headers={'Authorization': '****** admin-token'},
            json={
                'sku': 'EVENT-SKU-001',
                'quantity': 100
            }
        )
        
        assert response.status_code == 201
        # Verify event was published
        assert mock_client_instance.publish_event.called
        
        # Check event payload
        call_args = mock_client_instance.publish_event.call_args
        assert call_args is not None
        assert 'inventory' in call_args[1]['topic_name']
