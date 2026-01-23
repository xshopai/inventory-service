import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.services import InventoryService
from src.models import InventoryItem, Reservation, StockMovementType, ReservationStatus
from tests.unit.conftest import create_test_inventory_item, create_test_reservation


class TestInventoryService:
    """Test InventoryService business logic."""
    
    def test_get_inventory_by_sku(self, db_session):
        """Test getting inventory by SKU."""
        service = InventoryService()
        create_test_inventory_item(db_session, sku='SERVICE001')
        
        result = service.get_inventory_by_sku('SERVICE001')
        
        assert result is not None
        assert result['sku'] == 'SERVICE001'
    
    def test_create_inventory_item(self, db_session):
        """Test creating inventory item through service."""
        service = InventoryService()
        
        item = service.create_inventory_item(
            sku='CREATE001',
            quantity_available=50,
            reorder_level=10
        )
        
        assert item['sku'] == 'CREATE001'
        assert item['quantity_available'] == 50
    
    def test_create_inventory_item_duplicate_sku(self, db_session):
        """Test creating duplicate inventory item fails."""
        service = InventoryService()
        
        # Create first item
        service.create_inventory_item(sku='DUP001')
        
        # Create item with same SKU should fail
        with pytest.raises(ValueError, match="already exists"):
            service.create_inventory_item(sku='DUP001')
    
    def test_update_inventory_item(self, db_session):
        """Test updating inventory item."""
        service = InventoryService()
        
        # First create an item
        created = service.create_inventory_item(sku='UPDATE001')
        
        # Update it
        updated_item = service.update_inventory_item(
            'UPDATE001',
            quantity_available=200,
            reorder_level=20
        )
        
        assert updated_item['quantity_available'] == 200
        assert updated_item['reorder_level'] == 20
    
    def test_adjust_stock(self, db_session):
        """Test adjusting stock levels."""
        service = InventoryService()
        item = create_test_inventory_item(db_session, sku='ADJUST001', quantity_available=100)
        
        movement = service.adjust_stock(
            sku='ADJUST001',
            quantity=50,
            movement_type=StockMovementType.IN,
            reference='RESTOCK001'
        )
        
        assert movement['quantity'] == 50
        assert movement['movement_type'] == StockMovementType.IN.value
    
    def test_adjust_stock_outbound(self, db_session):
        """Test outbound stock adjustment."""
        service = InventoryService()
        item = create_test_inventory_item(db_session, sku='OUT001', quantity_available=100)
        
        movement = service.adjust_stock(
            sku='OUT001',
            quantity=30,
            movement_type=StockMovementType.OUT,
            reference='SALE001'
        )
        
        assert movement['quantity'] == 30
        assert movement['movement_type'] == StockMovementType.OUT.value
    
    def test_adjust_stock_insufficient_quantity(self, db_session):
        """Test adjusting stock with insufficient quantity."""
        service = InventoryService()
        create_test_inventory_item(db_session, sku='LOW001', quantity_available=10)
        
        with pytest.raises(ValueError, match="Insufficient stock"):
            service.adjust_stock(
                sku='LOW001',
                quantity=50,
                movement_type=StockMovementType.OUT
            )
    
    def test_check_availability(self, db_session):
        """Test checking stock availability."""
        service = InventoryService()
        item = create_test_inventory_item(db_session, sku='CHECK001', quantity_available=25)
        
        result = service.check_availability('CHECK001', 20)
        
        assert result['available'] is True
        assert result['available_quantity'] == 25
        assert result['requested_quantity'] == 20
    
    def test_search_inventory_advanced(self, db_session):
        """Test advanced inventory search."""
        service = InventoryService()
        
        # Create test items
        create_test_inventory_item(
            db_session, 
            sku='SEARCH001',
            quantity_available=5,
            reorder_level=10
        )
        create_test_inventory_item(
            db_session,
            sku='SEARCH002',
            quantity_available=50,
            reorder_level=10
        )
        
        # Search for low stock
        items, total = service.search_inventory(**{'low_stock': True})
        
        assert total >= 1
        assert len(items) >= 1
    
    def test_bulk_update_inventory(self, db_session):
        """Test bulk updating inventory."""
        service = InventoryService()
        
        # Create items
        create_test_inventory_item(db_session, sku='BULK001')
        create_test_inventory_item(db_session, sku='BULK002')
        
        operations = [
            {'sku': 'BULK001', 'quantity_available': 150},
            {'sku': 'BULK002', 'quantity_available': 200}
        ]
        
        results = service.bulk_update_inventory(operations)
        
        assert len(results) == 2
        assert all(result['success'] for result in results)
    
    def test_get_inventory_by_sku_not_found(self, db_session):
        """Test getting non-existent inventory by SKU."""
        service = InventoryService()
        
        result = service.get_inventory_by_sku('NONEXISTENT')
        
        assert result is None
    
    def test_health_check(self, db_session):
        """Test health check."""
        service = InventoryService()
        
        health_data = service.health_check()
        
        assert health_data['status'] == 'healthy'
        assert 'timestamp' in health_data


class TestReservationService:
    """Test reservation methods in InventoryService."""
    
    def test_create_reservation(self, db_session):
        """Test creating a reservation."""
        service = InventoryService()
        item = create_test_inventory_item(db_session, sku='RESERVE001', quantity_available=100)
        
        reservation = service.create_reservation(
            sku='RESERVE001',
            order_id='ORDER001',
            quantity=10
        )
        
        assert reservation['order_id'] == 'ORDER001'
        assert reservation['quantity'] == 10
        assert reservation['status'] == ReservationStatus.PENDING.value
    
    def test_create_reservation_insufficient_stock(self, db_session):
        """Test creating reservation with insufficient stock."""
        service = InventoryService()
        create_test_inventory_item(db_session, sku='LOW001', quantity_available=5)
        
        with pytest.raises(ValueError, match="Insufficient stock"):
            service.create_reservation(
                sku='LOW001',
                order_id='ORDER002',
                quantity=10
            )
    
    def test_confirm_reservation(self, db_session):
        """Test confirming a reservation."""
        service = InventoryService()
        inventory_item = create_test_inventory_item(db_session, sku='CONFIRM001')
        
        # Create reservation
        reservation = service.create_reservation(
            sku='CONFIRM001',
            order_id='ORDER003',
            quantity=10
        )
        
        # Confirm it
        result = service.confirm_reservation(reservation['id'], 'ORDER003')
        
        assert result is True
    
    def test_cancel_reservation(self, db_session):
        """Test cancelling a reservation."""
        service = InventoryService()
        inventory_item = create_test_inventory_item(db_session, sku='CANCEL001')
        
        # Create reservation
        reservation = service.create_reservation(
            sku='CANCEL001',
            order_id='ORDER004',
            quantity=10
        )
        
        # Cancel it
        result = service.cancel_reservation(reservation['id'])
        
        assert result is True
    
    def test_confirm_reservations_bulk(self, db_session):
        """Test bulk confirming reservations."""
        service = InventoryService()
        inventory_item = create_test_inventory_item(db_session, sku='BULK-RES001')
        
        # Create reservations
        res1 = service.create_reservation('BULK-RES001', 'ORDER005', 5)
        res2 = service.create_reservation('BULK-RES001', 'ORDER006', 5)
        
        results = service.confirm_reservations_bulk([res1['id'], res2['id']])
        
        assert len(results) == 2
        assert all(result['success'] for result in results)
    
    def test_search_reservations(self, db_session):
        """Test searching reservations."""
        service = InventoryService()
        inventory_item = create_test_inventory_item(db_session, sku='SEARCH-RES001')
        
        # Create reservations
        service.create_reservation('SEARCH-RES001', 'SEARCH-ORDER', 5)
        
        results, total = service.search_reservations(order_id='SEARCH-ORDER')
        
        assert total >= 1
        assert len(results) >= 1
        assert all(r['order_id'] == 'SEARCH-ORDER' for r in results)
    
    def test_expire_reservations(self, db_session):
        """Test processing expired reservations."""
        service = InventoryService()
        
        # This is mostly a system process, so just test it doesn't error
        result = service.expire_reservations()
        
        assert 'processed_count' in result
        assert 'processed_at' in result
    
    def test_get_reservation_not_found(self, db_session):
        """Test getting non-existent reservation."""
        service = InventoryService()
        
        result = service.get_reservation('non-existent-id')
        
        assert result is None
    
    def test_confirm_reservation_wrong_order(self, db_session):
        """Test confirming reservation with wrong order ID."""
        service = InventoryService()
        inventory_item = create_test_inventory_item(db_session, sku='WRONG-ORDER')
        
        # Create reservation
        reservation = service.create_reservation('WRONG-ORDER', 'ORDER-CORRECT', 5)
        
        # Try to confirm with wrong order ID
        with pytest.raises(ValueError, match="Order ID mismatch"):
            service.confirm_reservation(reservation['id'], 'ORDER-WRONG')
