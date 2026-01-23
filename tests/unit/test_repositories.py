import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

from src.repositories import InventoryRepository, ReservationRepository
from src.models import InventoryItem, Reservation, StockMovement, StockMovementType, ReservationStatus
from tests.conftest import create_test_inventory_item, create_test_reservation, create_test_stock_movement


class TestInventoryRepository:
    """Test InventoryRepository implementations."""
    
    def test_create_inventory_item(self, db_session):
        """Test creating inventory item through repository."""
        repo = InventoryRepository()
        
        # Create item using the model directly (as the repo expects)
        item = InventoryItem(
            sku='TEST-SKU-001',
            quantity_available=100,
            reorder_level=10
        )
        
        created_item = repo.create(item)
        
        assert created_item.id is not None
        assert created_item.sku == 'TEST-SKU-001'
        assert created_item.quantity_available == 100
    
    def test_get_by_sku(self, db_session):
        """Test getting inventory item by SKU."""
        repo = InventoryRepository()
        original_item = create_test_inventory_item(db_session, sku='GET-SKU-001')
        
        retrieved_item = repo.get_by_sku('GET-SKU-001')
        
        assert retrieved_item is not None
        assert retrieved_item.sku == 'GET-SKU-001'
        assert retrieved_item.id == original_item.id
    
    def test_get_by_id(self, db_session):
        """Test getting inventory item by ID."""
        repo = InventoryRepository()
        original_item = create_test_inventory_item(db_session)
        
        retrieved_item = repo.get_by_id(original_item.id)
        
        assert retrieved_item is not None
        assert retrieved_item.id == original_item.id
    
    def test_get_all_with_pagination(self, db_session):
        """Test getting all items with pagination."""
        repo = InventoryRepository()
        
        # Create multiple test items
        for i in range(5):
            create_test_inventory_item(db_session, sku=f'PAGINATE-{i:03d}')
        
        items, total = repo.get_all(page=1, per_page=3)
        
        assert len(items) == 3
        assert total >= 5
    
    def test_search_with_pagination(self, db_session):
        """Test search with pagination."""
        repo = InventoryRepository()
        
        create_test_inventory_item(db_session, sku='SEARCH001')
        create_test_inventory_item(db_session, sku='SEARCH002')
        create_test_inventory_item(db_session, sku='SEARCH003')
        
        items, total = repo.search(page=1, per_page=2)
        
        assert len(items) == 2
        assert total == 3
        
        # Test second page
        items2, total2 = repo.search(page=2, per_page=2)
        assert len(items2) == 1
        assert total2 == 3
    
    def test_search_low_stock(self, db_session):
        """Test searching for low stock items."""
        repo = InventoryRepository()
        
        # Create items with different stock levels
        create_test_inventory_item(
            db_session, 
            sku='LOW001',
            quantity_available=5,
            reorder_level=10
        )
        create_test_inventory_item(
            db_session,
            sku='HIGH001',
            quantity_available=50,
            reorder_level=10
        )
        
        items, total = repo.search(low_stock=True)
        
        assert len(items) >= 1
        # Verify at least one item has low stock
        low_stock_items = [item for item in items if item.quantity_available <= item.reorder_level]
        assert len(low_stock_items) >= 1
    
    def test_search_out_of_stock(self, db_session):
        """Test searching for out of stock items."""
        repo = InventoryRepository()
        
        # Create out of stock item
        create_test_inventory_item(
            db_session,
            sku='OUT001',
            quantity_available=0
        )
        create_test_inventory_item(
            db_session,
            sku='IN001',
            quantity_available=50
        )
        
        items, total = repo.search(out_of_stock=True)
        
        assert len(items) >= 1
        # Verify all returned items are out of stock
        for item in items:
            assert item.quantity_available == 0
    
    def test_update_inventory_item(self, db_session):
        """Test updating inventory item."""
        repo = InventoryRepository()
        original_item = create_test_inventory_item(db_session, quantity_available=100)
        
        # Update the item
        original_item.quantity_available = 150
        updated_item = repo.update(original_item)
        
        assert updated_item.quantity_available == 150
        assert updated_item.updated_at is not None
    
    def test_delete_inventory_item(self, db_session):
        """Test deleting inventory item."""
        repo = InventoryRepository()
        item = create_test_inventory_item(db_session, sku='DELETE-ME')
        
        success = repo.delete('DELETE-ME')
        
        assert success is True
        
        # Verify item is deleted
        deleted_item = repo.get_by_sku('DELETE-ME')
        assert deleted_item is None
    
    def test_create_stock_movement(self, db_session):
        """Test creating stock movement."""
        repo = InventoryRepository()
        item = create_test_inventory_item(db_session, sku='MOVEMENT-SKU')
        
        movement = repo.create_stock_movement(
            sku='MOVEMENT-SKU',
            movement_type=StockMovementType.IN,
            quantity=25,
            reference='RESTOCK-001',
            reason='Restocking'
        )
        
        assert movement.id is not None
        assert movement.sku == 'MOVEMENT-SKU'
        assert movement.quantity == 25
        assert movement.movement_type == StockMovementType.IN
    
    def test_get_stock_movements(self, db_session):
        """Test getting stock movements for SKU."""
        repo = InventoryRepository()
        item = create_test_inventory_item(db_session, sku='HISTORY-SKU')
        
        # Create movements
        create_test_stock_movement(db_session, item, movement_type=StockMovementType.IN, quantity=50)
        create_test_stock_movement(db_session, item, movement_type=StockMovementType.OUT, quantity=10)
        
        movements = repo.get_stock_movements('HISTORY-SKU')
        
        assert len(movements) >= 2
        for movement in movements:
            assert movement.sku == 'HISTORY-SKU'
    
    def test_bulk_update(self, db_session):
        """Test bulk updating inventory items."""
        repo = InventoryRepository()
        
        # Create items
        item1 = create_test_inventory_item(db_session, sku='BULK001')
        item2 = create_test_inventory_item(db_session, sku='BULK002')
        
        updates = [
            {'sku': 'BULK001', 'quantity_available': 200},
            {'sku': 'BULK002', 'quantity_available': 300}
        ]
        
        results = repo.bulk_update(updates)
        
        assert len(results) == 2
        assert all(result['success'] for result in results)


class TestReservationRepository:
    """Test ReservationRepository implementations."""
    
    def test_create_reservation(self, db_session):
        """Test creating reservation through repository."""
        repo = ReservationRepository()
        inventory_item = create_test_inventory_item(db_session, sku='RESERVE-SKU')
        
        reservation = Reservation(
            sku='RESERVE-SKU',
            order_id='ORDER001',
            quantity=10,
            status=ReservationStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        created_reservation = repo.create(reservation)
        
        assert created_reservation.id is not None
        assert created_reservation.order_id == 'ORDER001'
        assert created_reservation.quantity == 10
    
    def test_get_by_id(self, db_session):
        """Test getting reservation by ID."""
        repo = ReservationRepository()
        inventory_item = create_test_inventory_item(db_session, sku='RESERVE-SKU')
        original_reservation = create_test_reservation(db_session, inventory_item)
        
        retrieved_reservation = repo.get_by_id(original_reservation.id)
        
        assert retrieved_reservation is not None
        assert retrieved_reservation.id == original_reservation.id
    
    def test_get_by_order_id(self, db_session):
        """Test getting reservations by order ID."""
        repo = ReservationRepository()
        inventory_item = create_test_inventory_item(db_session, sku='RESERVE-SKU')
        
        # Create multiple reservations for same order
        create_test_reservation(db_session, inventory_item, order_id='ORDER123')
        create_test_reservation(db_session, inventory_item, order_id='ORDER123', quantity=15)
        
        reservations = repo.get_by_order_id('ORDER123')
        
        assert len(reservations) == 2
        for reservation in reservations:
            assert reservation.order_id == 'ORDER123'
    
    def test_update_reservation_status(self, db_session):
        """Test updating reservation status."""
        repo = ReservationRepository()
        inventory_item = create_test_inventory_item(db_session, sku='RESERVE-SKU')
        reservation = create_test_reservation(db_session, inventory_item)
        
        updated_reservation = repo.update_status(reservation.id, ReservationStatus.CONFIRMED)
        
        assert updated_reservation is not None
        assert updated_reservation.status == ReservationStatus.CONFIRMED
    
    def test_cancel_reservation(self, db_session):
        """Test cancelling a reservation."""
        repo = ReservationRepository()
        inventory_item = create_test_inventory_item(db_session, sku='RESERVE-SKU')
        reservation = create_test_reservation(db_session, inventory_item)
        
        cancelled_reservation = repo.cancel(reservation.id)
        
        assert cancelled_reservation is not None
        assert cancelled_reservation.status == ReservationStatus.CANCELLED
    
    def test_get_expired_reservations(self, db_session):
        """Test getting expired reservations."""
        repo = ReservationRepository()
        inventory_item = create_test_inventory_item(db_session, sku='RESERVE-SKU')
        
        # Create expired reservation
        expired_reservation = create_test_reservation(
            db_session, 
            inventory_item, 
            expires_at=datetime.utcnow() - timedelta(hours=1),
            status=ReservationStatus.PENDING
        )
        
        expired_reservations = repo.get_expired_reservations()
        
        assert len(expired_reservations) >= 1
        expired_ids = [r.id for r in expired_reservations]
        assert expired_reservation.id in expired_ids
    
    def test_bulk_confirm(self, db_session):
        """Test bulk confirming reservations."""
        repo = ReservationRepository()
        inventory_item = create_test_inventory_item(db_session, sku='RESERVE-SKU')
        
        # Create reservations
        reservation1 = create_test_reservation(db_session, inventory_item)
        reservation2 = create_test_reservation(db_session, inventory_item, order_id='ORDER002')
        
        results = repo.bulk_confirm([reservation1.id, reservation2.id])
        
        assert len(results) == 2
        assert all(result['success'] for result in results)
