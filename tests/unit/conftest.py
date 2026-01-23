import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json

# Set test environment variables before importing the app
os.environ['FLASK_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['REDIS_URL'] = 'redis://localhost:6379/1'

from src import create_app
from src.models import db, InventoryItem, Reservation, StockMovement, StockMovementType, ReservationStatus


@pytest.fixture(scope='session')
def app():
    """Create application for the tests."""
    app = create_app('testing')
    
    with app.app_context():
        # Create all database tables
        db.create_all()
        yield app
        # Clean up
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def db_session(app):
    """Create a database session for a test."""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        yield db.session
        
        # Clean up tables
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture
def sample_inventory_item(db_session):
    """Create a sample inventory item for testing."""
    item = InventoryItem(
        sku='TEST-SKU-001',
        product_id='TEST001',
        quantity_available=100,
        quantity_reserved=10,
        reorder_level=20,
        max_stock=200
    )
    db_session.add(item)
    db_session.commit()
    return item


@pytest.fixture
def sample_reservation(db_session, sample_inventory_item):
    """Create a sample reservation for testing."""
    reservation = Reservation(
        sku=sample_inventory_item.sku,
        order_id='ORDER001',
        quantity=5,
        status=ReservationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db_session.add(reservation)
    db_session.commit()
    return reservation


@pytest.fixture
def sample_stock_movement(db_session, sample_inventory_item):
    """Create a sample stock movement for testing."""
    movement = StockMovement(
        sku=sample_inventory_item.sku,
        movement_type=StockMovementType.IN,
        quantity=50,
        reference='REF001',
        reason='Test stock movement'
    )
    db_session.add(movement)
    db_session.commit()
    return movement


@pytest.fixture
def mock_dependencies(monkeypatch):
    """Mock external dependencies"""
    # Mock product service client
    mock_product_client = MagicMock()


@pytest.fixture
def mock_product_service():
    """Mock Product Service client for testing."""
    with patch('src.shared.utils.external_service_client.ProductServiceClient') as mock_client:
        mock_instance = MagicMock()
        mock_instance.get_product.return_value = {
            'id': 'TEST001',
            'name': 'Test Product',
            'category': 'Electronics',
            'price': 99.99
        }
        mock_instance.get_products.return_value = [
            {
                'id': 'TEST001',
                'name': 'Test Product',
                'category': 'Electronics',
                'price': 99.99
            }
        ]
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def auth_headers():
    """Mock authentication headers for testing."""
    return {
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
    }


# Helper functions for tests
def create_test_inventory_item(db_session, **kwargs):
    """Create a test inventory item with default values."""
    import uuid
    defaults = {
        'sku': f'TEST-SKU-{str(uuid.uuid4())[:8]}',  # Generate unique SKU
        'product_id': 'TEST001',
        'quantity_available': 100,
        'quantity_reserved': 0,
        'reorder_level': 10,
        'max_stock': 200
    }
    defaults.update(kwargs)
    
    item = InventoryItem(**defaults)
    db_session.add(item)
    db_session.commit()
    return item


def create_test_reservation(db_session, inventory_item, **kwargs):
    """Create a test reservation with default values."""
    defaults = {
        'sku': inventory_item.sku,
        'order_id': 'ORDER001',
        'quantity': 5,
        'status': ReservationStatus.PENDING,
        'expires_at': datetime.utcnow() + timedelta(hours=24)
    }
    defaults.update(kwargs)
    
    reservation = Reservation(**defaults)
    db_session.add(reservation)
    db_session.commit()
    return reservation


def create_test_stock_movement(db_session, inventory_item, **kwargs):
    """Create a test stock movement with default values."""
    defaults = {
        'sku': inventory_item.sku,
        'movement_type': StockMovementType.IN,
        'quantity': 10,
        'reference': 'REF001',
        'reason': 'Test movement',
        'created_by': 'test'
    }
    defaults.update(kwargs)
    
    movement = StockMovement(**defaults)
    db_session.add(movement)
    db_session.commit()
    return movement


# Custom assertions
def assert_inventory_response(response_data, expected_item):
    """Assert inventory item response format."""
    assert response_data['id'] == expected_item.id
    assert response_data['sku'] == expected_item.sku
    assert response_data['product_id'] == expected_item.product_id
    assert response_data['quantity_available'] == expected_item.quantity_available
    assert response_data['quantity_reserved'] == expected_item.quantity_reserved
    assert response_data['total_quantity'] == expected_item.total_quantity
    assert response_data['reorder_level'] == expected_item.reorder_level
    assert response_data['max_stock'] == expected_item.max_stock


def assert_reservation_response(response_data, expected_reservation):
    """Assert reservation response format."""
    assert response_data['id'] == expected_reservation.id
    assert response_data['sku'] == expected_reservation.sku
    assert response_data['order_id'] == expected_reservation.order_id
    assert response_data['quantity'] == expected_reservation.quantity
    assert response_data['status'] == expected_reservation.status.value


def assert_stock_movement_response(response_data, expected_movement):
    """Assert stock movement response format."""
    assert response_data['id'] == expected_movement.id
    assert response_data['sku'] == expected_movement.sku
    assert response_data['movement_type'] == expected_movement.movement_type.value
    assert response_data['quantity'] == expected_movement.quantity
    assert response_data['reference'] == expected_movement.reference


# Test data generators
def generate_inventory_data(**kwargs):
    """Generate inventory item test data."""
    defaults = {
        'sku': 'TEST-SKU-001',
        'product_id': 'PROD001',
        'quantity_available': 100,
        'quantity_reserved': 0,
        'reorder_level': 10,
        'max_stock': 200
    }
    defaults.update(kwargs)
    return defaults


def generate_reservation_data(**kwargs):
    """Generate reservation test data."""
    defaults = {
        'sku': 'TEST-SKU-001',
        'order_id': 'ORDER001',
        'quantity': 5,
        'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }
    defaults.update(kwargs)
    return defaults


def generate_stock_adjustment_data(**kwargs):
    """Generate stock adjustment test data."""
    defaults = {
        'quantity': 10,
        'movement_type': StockMovementType.IN.value,
        'reference': 'REF001',
        'reason': 'Test adjustment'
    }
    defaults.update(kwargs)
    return defaults
