"""
Health Check Utilities for inventory service
Provides standardized health checks for database and external services
"""

import time
import os
import psutil
import requests
from datetime import datetime, timezone
from sqlalchemy import text
from src.database import db
import logging

logger = logging.getLogger(__name__)

def check_database_health():
    """Check MySQL database connectivity and performance"""
    try:
        start_time = time.time()
        
        # Test database connection with a simple query
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Get database info
        result = db.session.execute(text('SELECT VERSION() as version'))
        version = result.fetchone()[0]
        
        return {
            'status': 'healthy',
            'message': 'MySQL database connection is healthy',
            'response_time': round(response_time, 2),
            'details': {
                'version': version,
                'pool_size': db.engine.pool.size(),
                'checked_in': db.engine.pool.checkedin(),
                'checked_out': db.engine.pool.checkedout(),
            },
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'MySQL database health check failed: {str(e)}',
            'response_time': 0,
            'details': {
                'error': str(e),
                'database_url': db.engine.url.render_as_string(hide_password=True),
            },
        }


def check_redis_health():
    """Redis disabled - returning unavailable status"""
    return {
        'status': 'unavailable',
        'message': 'Redis disabled',
        'latency_ms': None
    }
def check_external_service_health(service_name, service_url, timeout=5):
    """Check external service connectivity"""
    start_time = time.time()
    
    try:
        if not service_url or service_url in ['http://localhost:3001', 'http://localhost:3002']:
            return {
                'status': 'skipped',
                'message': f'{service_name} URL not configured or is development default',
                'response_time': 0,
            }
        
        response = requests.get(
            f'{service_url}/health',
            timeout=timeout,
            headers={
                'Accept': 'application/json',
                'User-Agent': 'inventory-service-health-check/1.0',
            }
        )
        
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            try:
                response_body = response.json()
            except ValueError:
                response_body = {}
            
            return {
                'status': 'healthy',
                'message': f'{service_name} is healthy',
                'response_time': round(response_time, 2),
                'details': {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'body': response_body,
                },
            }
        else:
            return {
                'status': 'unhealthy',
                'message': f'{service_name} returned {response.status_code}',
                'response_time': round(response_time, 2),
                'details': {
                    'status_code': response.status_code,
                    'reason': response.reason,
                },
            }
    
    except requests.exceptions.Timeout:
        response_time = (time.time() - start_time) * 1000
        return {
            'status': 'unhealthy',
            'message': f'{service_name} health check timed out after {timeout}s',
            'response_time': round(response_time, 2),
            'details': {'error': 'timeout'},
        }
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return {
            'status': 'unhealthy',
            'message': f'{service_name} health check failed: {str(e)}',
            'response_time': round(response_time, 2),
            'details': {'error': str(e)},
        }


def perform_readiness_check():
    """Perform comprehensive readiness check"""
    checks = {}
    overall_healthy = True
    check_start_time = time.time()
    
    try:
        # Check database connectivity
        logger.debug('Performing database health check')
        checks['database'] = check_database_health()
        if checks['database']['status'] != 'healthy':
            overall_healthy = False
        
        # Redis disabled
        logger.debug('Redis health check skipped (disabled)')
        checks['redis'] = {
            'status': 'unavailable',
            'message': 'Redis disabled',
            'latency_ms': None
        }
        
        # Check external services — resolve URL via SERVICE_BASE_URL template or fallback
        def resolve_service_url(name):
            base = os.environ.get('SERVICE_BASE_URL', '')
            if base:
                return base.replace('{name}', name)
            return None

        external_services = [
            {'name': 'product-service', 'url': resolve_service_url('product-service')},
        ]
        
        for service in external_services:
            if service['url']:
                logger.debug(f'Performing {service["name"]} service health check')
                checks[service['name']] = check_external_service_health(
                    service['name'], 
                    service['url'], 
                    timeout=3
                )
                
                # For readiness, external services should be healthy or skipped
                if checks[service['name']]['status'] not in ['healthy', 'skipped']:
                    overall_healthy = False
            else:
                checks[service['name']] = {
                    'status': 'skipped',
                    'message': f'{service["name"]} service check skipped (URL not configured)',
                    'response_time': 0,
                }
        
        total_check_time = round((time.time() - check_start_time) * 1000, 2)
        
        return {
            'status': 'ready' if overall_healthy else 'not ready',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_check_time': total_check_time,
            'checks': checks,
        }
    
    except Exception as e:
        logger.error('Readiness check failed', extra={'error': str(e)})
        
        return {
            'status': 'not ready',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_check_time': round((time.time() - check_start_time) * 1000, 2),
            'error': str(e),
            'checks': checks,
        }


def perform_liveness_check():
    """Perform liveness check (should be fast and not check external dependencies)"""
    try:
        # Get process information
        process = psutil.Process()
        
        # Check memory usage - if memory usage is > 90% of available, consider unhealthy
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        memory_healthy = memory_percent < 90.0
        
        # Check CPU usage over a short period
        cpu_percent = process.cpu_percent(interval=0.1)
        cpu_healthy = cpu_percent < 95.0  # Less than 95% CPU is healthy
        
        # Check if we can create a simple thread (basic responsiveness check)
        import threading
        thread_healthy = True
        try:
            def dummy_task():
                time.sleep(0.01)
            
            thread = threading.Thread(target=dummy_task)
            thread.start()
            thread.join(timeout=1.0)
            if thread.is_alive():
                thread_healthy = False
        except Exception:
            thread_healthy = False
        
        is_healthy = memory_healthy and cpu_healthy and thread_healthy
        
        return {
            'status': 'alive' if is_healthy else 'unhealthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'uptime': round(time.time() - psutil.boot_time(), 2),
            'checks': {
                'memory': {
                    'healthy': memory_healthy,
                    'usage': {
                        'rss': memory_info.rss,
                        'vms': memory_info.vms,
                        'percent': round(memory_percent, 2),
                    },
                },
                'cpu': {
                    'healthy': cpu_healthy,
                    'percent': round(cpu_percent, 2),
                },
                'threading': {
                    'healthy': thread_healthy,
                    'active_count': threading.active_count(),
                },
                'process': {
                    'pid': os.getpid(),
                    'python_version': f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}",
                    'platform': psutil.sys.platform,
                },
            },
        }
    
    except Exception as e:
        logger.error('Liveness check failed', extra={'error': str(e)})
        
        return {
            'status': 'unhealthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': str(e),
        }


def get_system_metrics():
    """Get system metrics for monitoring"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'uptime': round(time.time() - psutil.boot_time(), 2),
            'memory': {
                'rss': memory_info.rss,
                'vms': memory_info.vms,
                'percent': round(process.memory_percent(), 2),
                'available': psutil.virtual_memory().available,
                'total': psutil.virtual_memory().total,
            },
            'cpu': {
                'percent': round(process.cpu_percent(interval=0.1), 2),
                'times': process.cpu_times()._asdict(),
                'count': psutil.cpu_count(),
            },
            'process': {
                'pid': os.getpid(),
                'ppid': os.getppid(),
                'python_version': f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}",
                'platform': psutil.sys.platform,
                'threads': process.num_threads(),
            },
            'disk': {
                'usage': psutil.disk_usage('/')._asdict(),
            },
            'environment': {
                'flask_env': os.environ.get('FLASK_ENV', 'development'),
                'version': os.environ.get('API_VERSION', '1.0.0'),
            },
        }
    
    except Exception as e:
        logger.error('Metrics collection failed', extra={'error': str(e)})
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': str(e),
        }
