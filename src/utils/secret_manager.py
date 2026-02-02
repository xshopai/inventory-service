"""
Secret Manager Utility
Manages secrets retrieval using Dapr Secret Store building block

Naming Convention (same key names everywhere - Key Vault compatible):
- xshopai-{type}                  : Platform-wide secrets
- xshopai-{db}-server-connection  : Database server connections
- svc-{service}-token             : Service identity tokens

Same key names used in:
- .env.local (local dev without Dapr)
- .dapr/secrets.json (local dev with Dapr)
- Azure Key Vault (production)

Inventory Service Required Secrets:
- xshopai-mysql-server-connection : MySQL server connection (db name appended at runtime)
- xshopai-jwt-secret              : JWT signing secret
- xshopai-flask-secret            : Flask session secret
- xshopai-appinsights-connection  : Application Insights connection string
- xshopai-svc-product-token       : Product service auth token
- xshopai-svc-order-token         : Order service auth token
- xshopai-svc-cart-token          : Cart service auth token
- xshopai-svc-webbff-token        : Web BFF auth token
"""
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Secrets required by inventory-service (same names everywhere)
REQUIRED_SECRETS = [
    'xshopai-mysql-server-connection',
    'xshopai-jwt-secret',
    'xshopai-flask-secret',
    'xshopai-appinsights-connection',
    'xshopai-svc-product-token',
    'xshopai-svc-order-token',
    'xshopai-svc-cart-token',
    'xshopai-svc-webbff-token',
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
        Get secret by key name. Same name used everywhere.
        
        Args:
            key: Secret key (e.g., 'xshopai-jwt-secret')
        
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
        server_url = self.get_secret('xshopai-mysql-server-connection')
        db_name = database_name or os.environ.get('DB_NAME', 'inventory_service_db')
        
        if '?' in server_url:
            base_url, query = server_url.split('?', 1)
            return f"{base_url}/{db_name}?{query}"
        return f"{server_url}/{db_name}"
    
    def get_jwt_config(self) -> Dict[str, Any]:
        """Get JWT configuration."""
        return {
            'secret': self.get_secret('xshopai-jwt-secret'),
            'algorithm': os.environ.get('JWT_ALGORITHM', 'HS256'),
            'expiration': int(os.environ.get('JWT_EXPIRATION', '3600')),
            'issuer': os.environ.get('JWT_ISSUER', 'auth-service'),
            'audience': os.environ.get('JWT_AUDIENCE', 'xshopai-platform')
        }
    
    def get_flask_secret_key(self) -> str:
        """Get Flask SECRET_KEY."""
        return self.get_secret('xshopai-flask-secret')
    
    def get_service_tokens(self) -> Dict[str, str]:
        """
        Get service tokens for service-to-service auth.
        
        Checks environment variables first (set during ACA deployment),
        then falls back to Dapr secretstore. This avoids race conditions
        with Dapr sidecar startup.
        """
        token_keys = {
            'product-service': 'xshopai-svc-product-token',
            'order-service': 'xshopai-svc-order-token',
            'cart-service': 'xshopai-svc-cart-token',
            'web-bff': 'xshopai-svc-webbff-token',
        }
        
        tokens = {}
        for service, key in token_keys.items():
            # Check env var first (hyphenated key converted to underscore for env var)
            env_key = key.replace('-', '_').upper()
            env_value = os.environ.get(env_key)
            if env_value:
                tokens[service] = env_value
                logger.debug(f"Token for '{service}' loaded from env var {env_key}")
                continue
            
            # Fall back to Dapr secretstore
            try:
                tokens[service] = self.get_secret(key)
            except RuntimeError:
                logger.warning(f"Token for '{service}' not configured")
        
        return tokens
    
    def get_appinsights_connection_string(self) -> str:
        """
        Get Application Insights connection string.
        Returns None if not configured (telemetry will be disabled).
        
        Checks in order:
        1. APPLICATIONINSIGHTS_CONNECTION_STRING env var (standard Azure SDK name)
        2. Dapr secretstore: xshopai-appinsights-connection
        3. xshopai-appinsights-connection env var (fallback)
        """
        # Check standard Azure SDK env var first
        conn_string = os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING')
        if conn_string:
            logger.debug("App Insights connection loaded from APPLICATIONINSIGHTS_CONNECTION_STRING env")
            return conn_string
        
        # Fall back to Dapr secretstore / legacy env var
        try:
            return self.get_secret('xshopai-appinsights-connection')
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

def get_flask_secret_key() -> str:
    return get_secret_manager().get_flask_secret_key()

def get_appinsights_connection_string() -> str:
    return get_secret_manager().get_appinsights_connection_string()

def get_service_tokens() -> Dict[str, str]:
    return get_secret_manager().get_service_tokens()
