# Root conftest.py that re-exports all fixtures and helpers from unit/conftest.py
# This allows tests to import from tests.conftest

from tests.unit.conftest import (
    # Fixtures
    app,
    client,
    runner,
    db_session,
    sample_inventory_item,
    sample_reservation,
    sample_stock_movement,
    mock_dependencies,
    mock_product_service,
    auth_headers,
    
    # Helper functions
    create_test_inventory_item,
    create_test_reservation,
    create_test_stock_movement,
    assert_inventory_response,
    assert_reservation_response,
    assert_stock_movement_response,
    generate_inventory_data,
    generate_reservation_data,
    generate_stock_adjustment_data,
)

__all__ = [
    'app',
    'client',
    'runner',
    'db_session',
    'sample_inventory_item',
    'sample_reservation',
    'sample_stock_movement',
    'mock_dependencies',
    'mock_product_service',
    'auth_headers',
    'create_test_inventory_item',
    'create_test_reservation',
    'create_test_stock_movement',
    'assert_inventory_response',
    'assert_reservation_response',
    'assert_stock_movement_response',
    'generate_inventory_data',
    'generate_reservation_data',
    'generate_stock_adjustment_data',
]
