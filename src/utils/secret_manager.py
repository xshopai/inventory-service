"""
Secret Manager Utility
Manages secrets retrieval using Dapr Secret Store building block

Naming Convention:
- Application code uses UPPER_SNAKE_CASE environment variables
- Local dev (.env, .dapr/secrets.json) uses UPPER_SNAKE_CASE
- Azure Key Vault uses lower-kebab-case (infra layer translates)

Inventory Service Required Secrets:
- MYSQL_SERVER_CONNECTION   : MySQL server connection (db name appended at runtime)
- JWT_SECRET                : JWT signing secret
- APPINSIGHTS_CONNECTION    : Application Insights connection string
- SERVICE_PRODUCT_TOKEN     : Product service auth token
- SERVICE_ORDER_TOKEN       : Order service auth token
- SERVICE_CART_TOKEN        : Cart service auth token
- SERVICE_WEBBFF_TOKEN      : Web BFF auth token
"""
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Secrets required by inventory-service (UPPER_SNAKE_CASE everywhere)
REQUIRED_SECRETS = [
    'MYSQL_SERVER_CONNECTION',
    'JWT_SECRET',
    'APPINSIGHTS_CONNECTION',
    'SERVICE_PRODUCT_TOKEN',
    'SERVICE_ORDER_TOKEN',
    'SERVICE_CART_TOKEN',
    'SERVICE_WEBBFF_TOKEN',
]


class SecretManager:
    """
    Unified secret manager - same key names everywhere.
    Tries Dapr first, falls back to env vars.
    """
    
    def __init__(self):
        self.secret_store_name = 'secretstore'
        self._dapr_client = None
        self._cache: Dict[str, str] = {}
    
    @property
    def dapr_client(self):
        """Lazy load Dapr client"""
        if self._dapr_client is None:
            try:
                from dapr.clients import DaprClient
                self._dapr_client = DaprClient()
            except Exception as e:
                logger.debug(f"Dapr client not available: {e}")
                self._dapr_client = False
        return self._dapr_client if self._dapr_client else None
    
    def get_secret(self, key: str) -> str:
        """
        Get secret by key name (UPPER_SNAKE_CASE).
        
        Args:
            key: Secret key (e.g., 'JWT_SECRET')
        
        Returns:
            Secret value
        
        Raises:
            RuntimeError if secret not found
        """
        # Check cache
        if key in self._cache:
            return self._cache[key]
        
        value = None
        
        # Try Dapr Secret Store first
        if self.dapr_client:
            try:
                response = self.dapr_client.get_secret(
                    store_name=self.secret_store_name,
                    key=key
                )
                if response and response.secret:
                    value = response.secret.get(key)
                    if value:
                        logger.debug(f"Secret '{key}' loaded from Dapr")
            except Exception as e:
                logger.debug(f"Dapr lookup failed for '{key}': {e}")
        
        # Fallback to environment variable (same key name)
        if not value:
            value = os.environ.get(key)
            if value:
                logger.debug(f"Secret '{key}' loaded from env")
        
        if not value:
            raise RuntimeError(f"Secret '{key}' not found")
        
        self._cache[key] = value
        return value
    
    def get_database_url(self, database_name: str = None) -> str:
        """Get database URL with database name appended."""
        server_url = self.get_secret('MYSQL_SERVER_CONNECTION')
        db_name = database_name or os.environ.get('DB_NAME', 'inventory_service_db')
        
        if '?' in server_url:
            base_url, query = server_url.split('?', 1)
            return f"{base_url}/{db_name}?{query}"
        return f"{server_url}/{db_name}"
    
    def get_jwt_config(self) -> Dict[str, Any]:
        """Get JWT configuration."""
        return {
            'secret': self.get_secret('JWT_SECRET'),
            'algorithm': os.environ.get('JWT_ALGORITHM', 'HS256'),
            'expiration': int(os.environ.get('JWT_EXPIRATION', '3600')),
            'issuer': os.environ.get('JWT_ISSUER', 'auth-service'),
            'audience': os.environ.get('JWT_AUDIENCE', 'xshopai-platform')
        }
    
    def get_service_tokens(self) -> Dict[str, str]:
        """
        Get service tokens for service-to-service auth.
        
        Uses UPPER_SNAKE_CASE keys - same in env vars, Dapr secrets.json,
        and mapped from Key Vault at deployment time.
        """
        token_keys = {
            'product-service': 'SERVICE_PRODUCT_TOKEN',
            'order-service': 'SERVICE_ORDER_TOKEN',
            'cart-service': 'SERVICE_CART_TOKEN',
            'web-bff': 'SERVICE_WEBBFF_TOKEN',
        }
        
        tokens = {}
        for service, key in token_keys.items():
            try:
                tokens[service] = self.get_secret(key)
            except RuntimeError:
                logger.warning(f"Token for '{service}' not configured (key: {key})")
        
        return tokens
    
    def get_appinsights_connection_string(self) -> str:
        """
        Get Application Insights connection string.
        Returns None if not configured (telemetry will be disabled).
        
        Checks in order:
        1. APPLICATIONINSIGHTS_CONNECTION_STRING env var (standard Azure SDK name)
        2. APPINSIGHTS_CONNECTION via Dapr secretstore or env var
        """
        # Check standard Azure SDK env var first
        conn_string = os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING')
        if conn_string:
            logger.debug("App Insights connection loaded from APPLICATIONINSIGHTS_CONNECTION_STRING env")
            return conn_string
        
        # Fall back to Dapr secretstore / env var
        try:
            return self.get_secret('APPINSIGHTS_CONNECTION')
        except RuntimeError:
            logger.info("App Insights connection not configured - telemetry disabled")
            return None


# Singleton
_manager = None

def get_secret_manager() -> SecretManager:
    global _manager
    if _manager is None:
        _manager = SecretManager()
    return _manager


# Convenience functions
def get_database_url() -> str:
    return get_secret_manager().get_database_url()

def get_jwt_config() -> Dict[str, Any]:
    return get_secret_manager().get_jwt_config()

def get_appinsights_connection_string() -> str:
    return get_secret_manager().get_appinsights_connection_string()

def get_service_tokens() -> Dict[str, str]:
    return get_secret_manager().get_service_tokens()
