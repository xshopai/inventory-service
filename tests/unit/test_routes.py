#!/usr/bin/env python3
"""
Simple script to test all health endpoints
"""

from src import create_app

def test_routes():
    app = create_app()
    
    print('=== Available Routes ===')
    routes = []
    for rule in app.url_map.iter_rules():
        methods = [m for m in rule.methods if m not in ['HEAD', 'OPTIONS']]
        routes.append((rule.rule, methods))
        print(f'{rule.rule:<40} -> {methods}')
    
    print(f'\nTotal routes: {len(routes)}')
    
    print('\n=== Testing Health Endpoints ===')
    with app.test_client() as client:
        # Test direct health endpoints (outside /api/v1)
        direct_endpoints = [
            '/health',
            '/health/ready', 
            '/health/live',
            '/metrics'
        ]
        
        print('\nDirect endpoints (outside /api/v1):')
        for endpoint in direct_endpoints:
            try:
                response = client.get(endpoint)
                print(f'  {endpoint:<20}: {response.status_code}')
            except Exception as e:
                print(f'  {endpoint:<20}: ERROR - {e}')
        
        # Test API v1 health endpoints 
        api_endpoints = [
            '/api/v1/health/',
            '/api/v1/operational/health',
            '/api/v1/operational/ready',
            '/api/v1/operational/live', 
            '/api/v1/operational/metrics',
            '/api/v1/metrics'
        ]
        
        print('\nAPI v1 endpoints:')
        for endpoint in api_endpoints:
            try:
                response = client.get(endpoint)
                print(f'  {endpoint:<30}: {response.status_code}')
            except Exception as e:
                print(f'  {endpoint:<30}: ERROR - {e}')

if __name__ == '__main__':
    test_routes()
