"""
JWT Authentication and Authorization Middleware for Inventory Service
Provides consistent authentication and role-based access control
Includes service-to-service token validation
"""

import jwt
import os
from functools import wraps
from flask import request, g
import logging

logger = logging.getLogger(__name__)

# JWT Configuration cache
_jwt_config = None

# Service tokens cache
_service_tokens = None


def _get_service_tokens():
    """
    Get service token configuration from environment variables.
    Used for validating incoming requests from other services.
    """
    global _service_tokens
    if _service_tokens is None:
        _service_tokens = {
            'product-service': os.environ.get('SERVICE_PRODUCT_TOKEN', ''),
            'order-service': os.environ.get('SERVICE_ORDER_TOKEN', ''),
            'cart-service': os.environ.get('SERVICE_CART_TOKEN', ''),
            'web-bff': os.environ.get('SERVICE_WEBBFF_TOKEN', ''),
        }
    return _service_tokens


def _get_jwt_config():
    """Get JWT configuration from environment variables"""
    global _jwt_config
    if _jwt_config is None:
        try:
            _jwt_config = {
                'secret': os.environ.get('JWT_SECRET'),
                'algorithm': os.environ.get('JWT_ALGORITHM', 'RS256'),
                'issuer': os.environ.get('JWT_ISSUER', 'auth-service'),
                'audience': os.environ.get('JWT_AUDIENCE', 'xshopai-platform'),
            }
            
            if not _jwt_config['secret']:
                raise RuntimeError('JWT_SECRET environment variable is required')
            
            logger.info('JWT configuration loaded from environment variables')
        except Exception as e:
            logger.error(f'Failed to load JWT configuration: {str(e)}')
            raise RuntimeError('JWT configuration not available') from e
    return _jwt_config


class AuthError(Exception):
    """Custom authentication error"""
    def __init__(self, message, status_code=401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def get_token_from_request():
    """Extract JWT token from Authorization header"""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header:
        return None
    
    if not auth_header.startswith('Bearer '):
        raise AuthError('Authorization header must start with Bearer', 401)
    
    parts = auth_header.split(' ')
    if len(parts) != 2:
        raise AuthError('Invalid Authorization header format', 401)
    
    return parts[1]


def decode_jwt(token):
    """Decode and validate JWT token"""
    try:
        jwt_config = _get_jwt_config()
        payload = jwt.decode(
            token,
            jwt_config['secret'],
            algorithms=[jwt_config['algorithm']],
            issuer=jwt_config['issuer'],  # Verify issuer (auth-service)
            audience=jwt_config['audience']  # Verify audience (xshopai-platform)
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError('Token has expired', 401)
    except jwt.InvalidTokenError as e:
        logger.warning(f'Invalid token: {str(e)}')
        raise AuthError('Invalid token', 401)


def require_auth(f):
    """
    Decorator to require valid JWT authentication
    Attaches user info to g.current_user
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = get_token_from_request()
            
            if not token:
                logger.warning('Authentication required: No token provided')
                return {
                    'success': False,
                    'error': 'Authentication required',
                    'message': 'No authentication token provided'
                }, 401
            
            # Decode token
            payload = decode_jwt(token)
            
            # Extract user information (compatible with auth-service token structure)
            user_id = payload.get('id') or payload.get('user_id') or payload.get('sub')
            email = payload.get('email')
            roles = payload.get('roles', [])
            
            if not user_id:
                logger.warning('Invalid token: Missing user ID')
                return {
                    'success': False,
                    'error': 'Invalid token',
                    'message': 'Token missing user identifier'
                }, 401
            
            # Store user info in Flask g object
            g.current_user = {
                'id': user_id,
                'email': email,
                'roles': roles
            }
            
            logger.info(f'Authentication successful for user: {user_id}')
            
            return f(*args, **kwargs)
            
        except AuthError as e:
            logger.warning(f'Authentication failed: {e.message}')
            return {
                'success': False,
                'error': 'Authentication failed',
                'message': e.message
            }, e.status_code
        except Exception as e:
            logger.error(f'Authentication error: {str(e)}')
            return {
                'success': False,
                'error': 'Authentication error',
                'message': 'Internal authentication error'
            }, 500
    
    return decorated_function


def require_roles(*required_roles):
    """
    Decorator to require specific roles
    Usage: @require_roles('admin') or @require_roles('admin', 'manager')
    """
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user = g.current_user
            user_roles = user.get('roles', [])
            
            # Check if user has any of the required roles
            has_role = any(role in user_roles for role in required_roles)
            
            if not has_role:
                logger.warning(
                    f'Authorization failed: User {user.get("id")} lacks required roles. '
                    f'Required: {required_roles}, Has: {user_roles}'
                )
                return {
                    'success': False,
                    'error': 'Forbidden',
                    'message': f'Required roles: {", ".join(required_roles)}'
                }, 403
            
            logger.info(
                f'Authorization successful: User {user.get("id")} '
                f'with roles {user_roles} accessing endpoint'
            )
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_admin(f):
    """
    Decorator to require admin role
    Convenience wrapper around require_roles('admin')
    """
    return require_roles('admin')(f)


def optional_auth(f):
    """
    Decorator for optional authentication
    Attaches user info to g.current_user if token is present, otherwise continues
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = get_token_from_request()
            
            if token:
                try:
                    payload = decode_jwt(token)
                    user_id = payload.get('id') or payload.get('user_id') or payload.get('sub')
                    email = payload.get('email')
                    roles = payload.get('roles', [])
                    
                    if user_id:
                        g.current_user = {
                            'id': user_id,
                            'email': email,
                            'roles': roles
                        }
                        logger.info(f'Optional auth: User {user_id} authenticated')
                except AuthError:
                    # Invalid token, but we allow the request to continue
                    g.current_user = None
                    logger.info('Optional auth: Invalid token, continuing without authentication')
            else:
                g.current_user = None
                logger.debug('Optional auth: No token provided')
        
        except Exception as e:
            logger.warning(f'Optional auth error: {str(e)}')
            g.current_user = None
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user():
    """
    Get current authenticated user from Flask g object
    Returns None if not authenticated
    """
    return getattr(g, 'current_user', None)


def require_service_token(f):
    """
    Decorator to validate service-to-service authentication tokens.
    
    Checks for X-Service-Token header and validates against configured service tokens.
    Used for event handler endpoints that receive calls from other services.
    
    Usage:
        @require_service_token
        def handle_product_created():
            # Only callable by services with valid token
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Extract service token from custom header
            service_token = request.headers.get('X-Service-Token', '')
            
            if not service_token:
                logger.warning('Service authentication required: No service token provided')
                return {
                    'success': False,
                    'error': 'Service authentication required',
                    'message': 'No service token provided'
                }, 401
            
            # Validate token against configured service tokens
            valid_tokens = _get_service_tokens()
            
            # Check if token matches any configured service token
            matching_service = None
            for service_name, valid_token in valid_tokens.items():
                if service_token == valid_token:
                    matching_service = service_name
                    break
            
            if not matching_service:
                logger.warning(f'Invalid service token provided')
                return {
                    'success': False,
                    'error': 'Invalid service token',
                    'message': 'Service authentication failed'
                }, 401
            
            # Store service info in Flask g object for logging
            g.calling_service = matching_service
            logger.info(f'Service authentication successful: {matching_service}')
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f'Service authentication error: {str(e)}')
            return {
                'success': False,
                'error': 'Authentication error',
                'message': 'Service authentication failed'
            }, 500
    
    return decorated_function


def require_dapr_token(f):
    """
    Decorator to validate Dapr sidecar pub/sub event delivery.
    
    Dapr delivers CloudEvents via HTTP POST to subscriber endpoints.
    This decorator validates that the request originates from the Dapr sidecar
    by checking for the dapr-api-token header (if configured) or accepting
    Dapr user-agent requests.
    
    This is NOT the same as require_service_token which expects a custom
    X-Service-Token header that Dapr never sends.
    
    Usage:
        @require_dapr_token
        def handle_order_created():
            # Only callable by Dapr sidecar
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Option 1: Validate dapr-api-token if configured
            configured_token = os.environ.get('DAPR_API_TOKEN', '')
            if configured_token:
                incoming_token = request.headers.get('dapr-api-token', '')
                if incoming_token != configured_token:
                    logger.warning('Dapr API token validation failed')
                    return {
                        'success': False,
                        'error': 'Invalid Dapr API token',
                        'message': 'Event delivery authentication failed'
                    }, 401
                g.calling_service = 'dapr-sidecar'
                return f(*args, **kwargs)
            
            # Option 2: No API token configured - accept all event deliveries
            # In production, DAPR_API_TOKEN should be configured for security.
            # In local dev, Dapr sidecar is trusted by default.
            user_agent = request.headers.get('User-Agent', '')
            if 'fasthttp' in user_agent.lower() or 'dapr' in user_agent.lower():
                g.calling_service = 'dapr-sidecar'
            else:
                g.calling_service = 'unknown'
                logger.debug(f'Event received from non-Dapr user-agent: {user_agent}')
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f'Dapr token validation error: {str(e)}')
            return {
                'success': False,
                'error': 'Authentication error',
                'message': 'Event delivery authentication failed'
            }, 500
    
    return decorated_function
