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
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        Get database configuration from secrets
        
        Returns:
            Dictionary with database configuration
        """
        return {
            'host': self.get_secret('mysql-host'),
            'port': int(self.get_secret('mysql-port')),
            'database': self.get_secret('mysql-database'),
            'user': self.get_secret('mysql-username'),
            'password': self.get_secret('mysql-password'),
            'root_password': self.get_secret('mysql-root-password')
        }
    
    def get_jwt_config(self) -> Dict[str, Any]:
        """
        Get JWT configuration from secrets and environment
        Only JWT_SECRET is truly secret - algorithm and expiration are just config
        
        Returns:
            Dictionary with JWT configuration
        """
        import os
        return {
            'secret': self.get_secret('jwt-secret'),
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
def get_database_config() -> Dict[str, Any]:
    """Get database configuration"""
    return get_secret_manager().get_database_config()


def get_jwt_config() -> Dict[str, Any]:
    """Get JWT configuration"""
    return get_secret_manager().get_jwt_config()


