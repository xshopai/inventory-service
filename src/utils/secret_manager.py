"""
Secret Manager Utility
Manages secrets retrieval using Dapr Secret Store building block
"""
import os
import logging
from typing import Dict, Any, Optional
from dapr.clients import DaprClient

logger = logging.getLogger(__name__)


class DaprSecretManager:
    """Client for retrieving secrets from Dapr Secret Store"""
    
    def __init__(self):
        self.secret_store_name = 'secret-store'
        self.dapr_client = DaprClient()
    
    def get_secret(self, key: str) -> str:
        """
        Get a single secret value from Dapr Secret Store
        
        Args:
            key: Secret key to retrieve
            
        Returns:
            Secret value
            
        Raises:
            Exception if secret not found or error occurs
        """
        try:
            secret_response = self.dapr_client.get_secret(
                store_name=self.secret_store_name,
                key=key
            )
            
            if secret_response and secret_response.secret:
                value = secret_response.secret.get(key)
                if value:
                    return value
            
            raise Exception(f"Secret '{key}' not found in store '{self.secret_store_name}'")
            
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


