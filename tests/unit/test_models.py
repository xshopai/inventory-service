import pytest
from datetime import datetime, timedelta
from src.models import InventoryItem, Reservation, StockMovement, StockMovementType, ReservationStatus
from tests.conftest import create_test_inventory_item, create_test_reservation, create_test_stock_movement


class TestInventoryItem:
    """Test InventoryItem model."""
    
    def test_create_inventory_item(self, db_session):
        """Test creating an inventory item."""
        item = InventoryItem(
            sku='TEST-SKU-001',
            quantity_available=100,
            quantity_reserved=10,
            reorder_level=20,
            max_stock=200
        )
        
        db_session.add(item)
        db_session.commit()
        
        assert item.id is not None
        assert item.sku == 'TEST-SKU-001'
        assert item.quantity_available == 100
        assert item.quantity_reserved == 10
        assert item.reorder_level == 20
        assert item.max_stock == 200
        assert item.created_at is not None
        assert item.updated_at is not None
    
    def test_total_quantity_property(self, db_session):
        """Test total_quantity computed property."""
        item = create_test_inventory_item(
            db_session,
            quantity_available=100,
            quantity_reserved=30
        )
        
        assert item.total_quantity == 130  # available + reserved
    
    def test_is_low_stock_property(self, db_session):
        """Test is_low_stock computed property."""
        # Low stock case
        low_stock_item = create_test_inventory_item(
            db_session,
            sku='LOW-SKU-001',
            quantity_available=5,
            reorder_level=10
        )
        assert low_stock_item.is_low_stock is True
        
        # Normal stock case
        normal_stock_item = create_test_inventory_item(
            db_session,
            sku='NORMAL-SKU-001',
            quantity_available=50,
            reorder_level=10
        )
        assert normal_stock_item.is_low_stock is False
    
    def test_to_dict_method(self, db_session):
        """Test to_dict serialization method."""
        item = create_test_inventory_item(db_session)
        
        data = item.to_dict()
        
        assert data['id'] == item.id
        assert data['sku'] == item.sku
        assert data['quantity_available'] == item.quantity_available
        assert data['quantity_reserved'] == item.quantity_reserved
        assert data['total_quantity'] == item.total_quantity
        assert data['reorder_level'] == item.reorder_level
        assert data['max_stock'] == item.max_stock
        assert 'created_at' in data
        assert 'updated_at' in data
    
    def test_unique_sku_constraint(self, db_session):
        """Test unique constraint on sku."""
        # Create first item
        item1 = create_test_inventory_item(
            db_session,
            sku='UNIQUE-SKU-001'
        )
        
        # Try to create second item with same sku
        with pytest.raises(Exception):  # Should raise IntegrityError
            item2 = InventoryItem(
                sku='UNIQUE-SKU-001',
                quantity_available=50
            )
            db_session.add(item2)
            db_session.commit()


class TestReservation:
    """Test Reservation model."""
    
    def test_create_reservation(self, db_session, sample_inventory_item):
        """Test creating a reservation."""
        reservation = Reservation(
            sku=sample_inventory_item.sku,
            order_id='ORDER001',
            quantity=5,
            status=ReservationStatus.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        db_session.add(reservation)
        db_session.commit()
        
        assert reservation.id is not None
        assert reservation.sku == sample_inventory_item.sku
        assert reservation.order_id == 'ORDER001'
        assert reservation.quantity == 5
        assert reservation.status == ReservationStatus.ACTIVE
        assert reservation.expires_at is not None
        assert reservation.created_at is not None
        assert reservation.updated_at is not None
    
    def test_is_expired_property(self, db_session, sample_inventory_item):
        """Test is_expired computed property."""
        # Expired reservation
        expired_reservation = Reservation(
            sku=sample_inventory_item.sku,
            order_id='ORDER001',
            quantity=5,
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        db_session.add(expired_reservation)
        db_session.commit()
        
        assert expired_reservation.is_expired is True
        
        # Active reservation
        active_reservation = Reservation(
            sku=sample_inventory_item.sku,
            order_id='ORDER002',
            quantity=5,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(active_reservation)
        db_session.commit()
        
        assert active_reservation.is_expired is False
    
    def test_to_dict_method(self, db_session, sample_inventory_item):
        """Test to_dict serialization method."""
        reservation = create_test_reservation(db_session, sample_inventory_item)
        
        data = reservation.to_dict()
        
        assert data['id'] == reservation.id
        assert data['order_id'] == reservation.order_id
        assert data['sku'] == reservation.sku
        assert data['quantity'] == reservation.quantity
        assert data['status'] == reservation.status.value
        assert 'expires_at' in data
        assert 'created_at' in data
        assert 'updated_at' in data
    
    def test_reservation_statuses(self, db_session, sample_inventory_item):
        """Test different reservation statuses."""
        statuses = [
            ReservationStatus.PENDING,
            ReservationStatus.ACTIVE,
            ReservationStatus.CONFIRMED,
            ReservationStatus.RELEASED,
            ReservationStatus.EXPIRED
        ]
        
        for i, status in enumerate(statuses):
            reservation = Reservation(
                sku=sample_inventory_item.sku,
                order_id=f'ORDER00{i}',
                quantity=5,
                status=status,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            db_session.add(reservation)
            db_session.commit()
            
            assert reservation.status == status


class TestStockMovement:
    """Test StockMovement model."""
    
    def test_create_stock_movement(self, db_session, sample_inventory_item):
        """Test creating a stock movement."""
        movement = StockMovement(
            sku=sample_inventory_item.sku,
            movement_type=StockMovementType.IN,
            quantity=50,
            reference='REF001',
            reason='Test stock movement'
        )
        
        db_session.add(movement)
        db_session.commit()
        
        assert movement.id is not None
        assert movement.sku == sample_inventory_item.sku
        assert movement.movement_type == StockMovementType.IN
        assert movement.quantity == 50
        assert movement.reference == 'REF001'
        assert movement.reason == 'Test stock movement'
        assert movement.created_at is not None
    
    def test_to_dict_method(self, db_session, sample_inventory_item):
        """Test to_dict serialization method."""
        movement = create_test_stock_movement(db_session, sample_inventory_item)
        
        data = movement.to_dict()
        
        assert data['id'] == movement.id
        assert data['sku'] == movement.sku
        assert data['movement_type'] == movement.movement_type.value
        assert data['quantity'] == movement.quantity
        assert data['reference'] == movement.reference
        assert data['reason'] == movement.reason
        assert data['created_by'] == movement.created_by
        assert 'created_at' in data
    
    def test_movement_types(self, db_session, sample_inventory_item):
        """Test different movement types."""
        movement_types = [
            StockMovementType.IN,
            StockMovementType.OUT,
            StockMovementType.RESERVED,
            StockMovementType.RELEASED,
            StockMovementType.ADJUSTMENT
        ]
        
        for i, movement_type in enumerate(movement_types):
            movement = StockMovement(
                sku=sample_inventory_item.sku,
                movement_type=movement_type,
                quantity=10,
                reference=f'REF00{i}'
            )
            db_session.add(movement)
            db_session.commit()
            
            assert movement.movement_type == movement_type


class TestModelRelationships:
    """Test relationships between models."""
    
    def test_inventory_item_reservations_relationship(self, db_session):
        """Test one-to-many relationship between inventory item and reservations."""
        item = create_test_inventory_item(db_session)
        
        # Create multiple reservations for the same item
        reservation1 = create_test_reservation(
            db_session, 
            item, 
            order_id='ORDER001'
        )
        reservation2 = create_test_reservation(
            db_session, 
            item, 
            order_id='ORDER002'
        )
        
        # Test relationship access
        assert len(item.reservations) == 2
        assert reservation1 in item.reservations
        assert reservation2 in item.reservations
        
        # Test back reference
        assert reservation1.inventory_item == item
        assert reservation2.inventory_item == item
    
    def test_inventory_item_stock_movements_relationship(self, db_session):
        """Test one-to-many relationship between inventory item and stock movements."""
        item = create_test_inventory_item(db_session)
        
        # Create multiple stock movements for the same item
        movement1 = create_test_stock_movement(
            db_session, 
            item,
            movement_type=StockMovementType.IN,
            reference='REF001'
        )
        movement2 = create_test_stock_movement(
            db_session, 
            item,
            movement_type=StockMovementType.OUT,
            reference='REF002'
        )
        
        # Test relationship access
        assert len(item.stock_movements) == 2
        assert movement1 in item.stock_movements
        assert movement2 in item.stock_movements
        
        # Test back reference
        assert movement1.inventory_item == item
        assert movement2.inventory_item == item
