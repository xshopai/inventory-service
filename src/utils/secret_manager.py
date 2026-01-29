"""
Secret Manager Utility
Manages secrets retrieval using Dapr Secret Store building block

Key Vault Secret Naming Convention:
- xshopai-{resource}-{type}-connection : Database/service connections (server/account level)
  Examples: xshopai-mysql-server-connection, xshopai-cosmos-account-connection
- xshopai-{name} : Other platform-wide secrets (e.g., xshopai-jwt-secret)
- svc-{service}-token : Service identity tokens (e.g., svc-product-token)
"""
import os
import logging
from typing import Dict, Any, Optional
from dapr.clients import DaprClient

logger = logging.getLogger(__name__)

# Key Vault secret name mappings (code name -> Key Vault name)
# Server/account-level connection strings - services append their database name
SECRET_KEY_MAPPING = {
    # Database connections (server/account-level, no db specified - services append their db)
    'DATABASE_URL': 'xshopai-mysql-server-connection',  # URL format: mysql+pymysql://user:pass@host:port
    'MYSQL_SERVER_CONNECTION': 'xshopai-mysql-server-connection',
    'POSTGRES_SERVER_CONNECTION': 'xshopai-postgres-server-connection',
    'COSMOS_ACCOUNT_CONNECTION': 'xshopai-cosmos-account-connection',
    'SQL_SERVER_CONNECTION': 'xshopai-sql-server-connection',
    # Messaging & Cache
    'REDIS_PASSWORD': 'xshopai-redis-password',
    'SERVICEBUS_CONNECTION': 'xshopai-servicebus-connection',
    # Security
    'JWT_SECRET': 'xshopai-jwt-secret',
    'FLASK_SECRET_KEY': 'xshopai-flask-secret',
    # Observability (connection string includes instrumentation key + endpoints)
    'APPINSIGHTS_CONNECTION': 'xshopai-appinsights-connection',
    # Service tokens
    'PRODUCT_SERVICE_TOKEN': 'svc-product-token',
    'ORDER_SERVICE_TOKEN': 'svc-order-token',
    'CART_SERVICE_TOKEN': 'svc-cart-token',
    'WEB_BFF_TOKEN': 'svc-webbff-token',
}


class DaprSecretManager:
    """Client for retrieving secrets from Dapr Secret Store"""
    
    def __init__(self):
        self.secret_store_name = 'secretstore'
        self.dapr_client = DaprClient()
    
    def _get_kv_key(self, key: str) -> str:
        """
        Get the Key Vault secret name for a given code key.
        Uses mapping table, falls back to lowercase with hyphens.
        """
        if key in SECRET_KEY_MAPPING:
            return SECRET_KEY_MAPPING[key]
        # Fallback: convert to lowercase and replace underscores with hyphens
        return key.lower().replace('_', '-')
    
    def get_secret(self, key: str) -> str:
        """
        Get a single secret value from Dapr Secret Store
        
        Args:
            key: Secret key to retrieve (code name, will be mapped to KV name)
            
        Returns:
            Secret value
            
        Raises:
            Exception if secret not found or error occurs
        """
        try:
            # Map code key to Key Vault secret name
            kv_key = self._get_kv_key(key)
            
            secret_response = self.dapr_client.get_secret(
                store_name=self.secret_store_name,
                key=kv_key
            )
            
            if secret_response and secret_response.secret:
                # Azure Key Vault returns the key name
                value = secret_response.secret.get(kv_key)
                if value:
                    return value
            
            raise Exception(f"Secret '{kv_key}' not found in store '{self.secret_store_name}'")
            
        except Exception as e:
            logger.error(f"Error retrieving secret '{key}': {str(e)}")
            raise
    
    def get_database_url(self) -> str:
        """
        Get database URL from Dapr Secret Store
        
        Returns:
            Database connection URL string
        """
        return self.get_secret('DATABASE_URL')
    
    def get_jwt_config(self) -> Dict[str, Any]:
        """
        Get JWT configuration from secrets and environment
        Only JWT_SECRET is truly secret - algorithm and expiration are just config
        
        Returns:
            Dictionary with JWT configuration
        """
        import os
        return {
            'secret': self.get_secret('JWT_SECRET'),
            'algorithm': os.environ.get('JWT_ALGORITHM', 'HS256'),
            'expiration': int(os.environ.get('JWT_EXPIRATION', '3600')),
            'issuer': os.environ.get('JWT_ISSUER', 'auth-service'),
            'audience': os.environ.get('JWT_AUDIENCE', 'xshopai-platform')
        }



# Singleton instance
_secret_manager = None


def get_secret_manager() -> DaprSecretManager:
    """Get singleton secret manager instance"""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = DaprSecretManager()
    return _secret_manager


# Convenience functions for direct access
def get_database_url() -> str:
    """
    Get database URL.
    
    First tries Dapr Secret Store (for production/Dapr mode).
    Falls back to DATABASE_URL environment variable (for local dev without Dapr).
    
    Returns:
        Database connection URL string
    """
    # Try Dapr Secret Store first
    try:
        return get_secret_manager().get_database_url()
    except Exception as e:
        logger.warning(f'Dapr Secret Store not available, falling back to env vars: {e}')
    
    # Fallback to environment variable for local development without Dapr
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError(
            'DATABASE_URL not configured. Set DATABASE_URL env var for non-Dapr mode, '
            'or ensure Dapr sidecar is running with secrets configured.'
        )
    
    return database_url


def get_jwt_config() -> Dict[str, Any]:
    """
    Get JWT configuration.
    
    First tries Dapr Secret Store (for production/Dapr mode).
    Falls back to environment variables (for local dev without Dapr).
    
    Returns:
        Dictionary with JWT configuration
    """
    # Try Dapr Secret Store first
    try:
        return get_secret_manager().get_jwt_config()
    except Exception as e:
        logger.warning(f'Dapr Secret Store not available, falling back to env vars: {e}')
    
    # Fallback to environment variables for local development without Dapr
    jwt_secret = os.environ.get('JWT_SECRET')
    if not jwt_secret:
        raise RuntimeError(
            'JWT_SECRET not configured. Set JWT_SECRET env var for non-Dapr mode, '
            'or ensure Dapr sidecar is running with secrets configured.'
        )
    
    return {
        'secret': jwt_secret,
        'algorithm': os.environ.get('JWT_ALGORITHM', 'HS256'),
        'expiration': int(os.environ.get('JWT_EXPIRATION', '3600')),
        'issuer': os.environ.get('JWT_ISSUER', 'auth-service'),
        'audience': os.environ.get('JWT_AUDIENCE', 'xshopai-platform')
    }


def get_service_tokens() -> Dict[str, str]:
    """
    Get service tokens for service-to-service authentication.
    
    First tries Dapr Secret Store (for production/Dapr mode).
    Falls back to environment variables (for local dev without Dapr).
    
    Returns:
        Dictionary mapping service names to their tokens
    """
    service_token_keys = {
        'product-service': 'PRODUCT_SERVICE_TOKEN',
        'order-service': 'ORDER_SERVICE_TOKEN',
        'cart-service': 'CART_SERVICE_TOKEN',
        'web-bff': 'WEB_BFF_TOKEN'
    }
    
    tokens = {}
    
    # Try Dapr Secret Store first
    try:
        secret_manager = get_secret_manager()
        for service_name, secret_key in service_token_keys.items():
            try:
                token = secret_manager.get_secret(secret_key)
                if token:
                    tokens[service_name] = token
            except Exception:
                pass  # Skip if specific token not found
        
        if tokens:
            logger.info(f'Service tokens loaded from Dapr for {len(tokens)} services')
            return tokens
    except Exception as e:
        logger.warning(f'Dapr Secret Store not available for service tokens: {e}')
    
    # Fallback to environment variables for local development without Dapr
    for service_name, env_key in service_token_keys.items():
        token = os.environ.get(env_key)
        if token:
            tokens[service_name] = token
    
    if tokens:
        logger.info(f'Service tokens loaded from env vars for {len(tokens)} services')
    else:
        logger.warning('No service tokens configured')
    
    return tokens


def get_flask_secret_key() -> str:
    """
    Get Flask SECRET_KEY for session signing.
    
    First tries Dapr Secret Store (for production/Dapr mode).
    Falls back to environment variable (for local dev without Dapr).
    
    Returns:
        Flask secret key string
    """
    # Try Dapr Secret Store first
    try:
        return get_secret_manager().get_secret('FLASK_SECRET_KEY')
    except Exception as e:
        logger.warning(f'Dapr Secret Store not available for Flask secret: {e}')
    
    # Fallback to environment variable for local development without Dapr
    secret_key = os.environ.get('SECRET_KEY')
    if secret_key:
        return secret_key
    
    # Default for development only
    logger.warning('Using default Flask SECRET_KEY - not secure for production!')
    return 'dev-secret-key-change-in-production'


