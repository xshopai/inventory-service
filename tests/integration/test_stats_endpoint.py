"""
Integration tests for /api/stats endpoint
Tests the stats endpoint with real database queries
"""

import pytest
from flask import Flask
from src import create_app
from src.database import db
from src.models import InventoryItem


@pytest.fixture
def app():
    """Create test Flask app"""
    app = create_app('test')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def sample_inventory_items(app):
    """Create sample inventory items for testing"""
    with app.app_context():
        items = [
            # Products with stock
            InventoryItem(
                sku='SKU-001',
                quantity_available=100,
                quantity_reserved=10,
                reorder_level=20,
                cost_per_unit=10.0
            ),
            InventoryItem(
                sku='SKU-002',
                quantity_available=50,
                quantity_reserved=5,
                reorder_level=15,
                cost_per_unit=15.0
            ),
            # Low stock item
            InventoryItem(
                sku='SKU-003',
                quantity_available=5,
                quantity_reserved=0,
                reorder_level=20,
                cost_per_unit=20.0
            ),
            # Out of stock item
            InventoryItem(
                sku='SKU-004',
                quantity_available=0,
                quantity_reserved=0,
                reorder_level=10,
                cost_per_unit=25.0
            ),
        ]
        
        for item in items:
            db.session.add(item)
        db.session.commit()
        
        return items


class TestStatsEndpoint:
    """Test suite for /api/stats endpoint"""
    
    def test_stats_endpoint_returns_200(self, client, sample_inventory_items):
        """Test that stats endpoint returns 200 OK"""
        response = client.get('/api/stats')
        assert response.status_code == 200
        assert response.json is not None
    
    def test_stats_endpoint_structure(self, client, sample_inventory_items):
        """Test that stats endpoint returns correct structure"""
        response = client.get('/api/stats')
        data = response.json
        
        assert 'productsWithStock' in data
        assert 'lowStockCount' in data
        assert 'outOfStockCount' in data
        assert 'totalInventoryValue' in data
        assert 'totalUnits' in data
        assert 'totalItems' in data
        assert 'service' in data
    
    def test_stats_products_with_stock_count(self, client, sample_inventory_items):
        """Test products with stock count"""
        response = client.get('/api/stats')
        data = response.json
        
        # Should have 3 products with stock > 0
        assert data['productsWithStock'] == 3
    
    def test_stats_low_stock_count(self, client, sample_inventory_items):
        """Test low stock count"""
        response = client.get('/api/stats')
        data = response.json
        
        # Should have 1 low stock item (quantity < reorder_level)
        assert data['lowStockCount'] == 1
    
    def test_stats_out_of_stock_count(self, client, sample_inventory_items):
        """Test out of stock count"""
        response = client.get('/api/stats')
        data = response.json
        
        # Should have 1 out of stock item
        assert data['outOfStockCount'] == 1
    
    def test_stats_total_items_count(self, client, sample_inventory_items):
        """Test total items count"""
        response = client.get('/api/stats')
        data = response.json
        
        # Should have 4 total items
        assert data['totalItems'] == 4
    
    def test_stats_total_units(self, client, sample_inventory_items):
        """Test total units calculation"""
        response = client.get('/api/stats')
        data = response.json
        
        # Total: 100 + 50 + 5 + 0 = 155 units
        assert data['totalUnits'] == 155
    
    def test_stats_total_inventory_value(self, client, sample_inventory_items):
        """Test total inventory value calculation"""
        response = client.get('/api/stats')
        data = response.json
        
        # Total value: (100*10) + (50*15) + (5*20) + (0*25) = 1000 + 750 + 100 + 0 = 1850
        assert data['totalInventoryValue'] == 1850.0
    
    def test_stats_empty_inventory(self, client):
        """Test stats with empty inventory"""
        response = client.get('/api/stats')
        data = response.json
        
        assert data['productsWithStock'] == 0
        assert data['lowStockCount'] == 0
        assert data['outOfStockCount'] == 0
        assert data['totalInventoryValue'] == 0.0
        assert data['totalUnits'] == 0
        assert data['totalItems'] == 0
    
    def test_stats_service_identifier(self, client, sample_inventory_items):
        """Test that service identifier is present"""
        response = client.get('/api/stats')
        data = response.json
        
        assert data['service'] == 'inventory-service'
