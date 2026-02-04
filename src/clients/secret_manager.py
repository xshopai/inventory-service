"""
Dapr Secret Management Service
Provides secret management using Dapr's secret store building block with ENV fallback.

Priority Order:
1. Dapr Secret Store (.dapr/secrets.json) - when running with Dapr
2. Environment Variable (.env file) - when running without Dapr

Secret Naming Convention:
  Local (.dapr/secrets.json): UPPER_SNAKE_CASE (e.g., JWT_SECRET)
  Azure Key Vault: lower-kebab-case (e.g., jwt-secret)
  The mapping is handled by Dapr component configuration in Azure.
"""

import os
import logging
from dapr.clients import DaprClient
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DaprSecretManager:
    """
    Secret manager with Dapr first, ENV fallback pattern.
    
    Priority:
    1. Dapr Secret Store (.dapr/secrets.json or Azure Key Vault)
    2. Environment Variable (.env file loaded by python-dotenv)
    """
    
    def __init__(self):
        self.dapr_http_port = os.getenv('DAPR_HTTP_PORT', '3500')
        self.dapr_host = os.getenv('DAPR_HOST', 'localhost')
        self.secret_store_name = 'secretstore'
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        logger.info(f"Secret manager initialized (environment={self.environment}, store={self.secret_store_name})")
    
    def _get_dapr_client(self) -> DaprClient:
        """Get Dapr client instance"""
        return DaprClient(address=f'{self.dapr_host}:{self.dapr_http_port}')
    
    def get_secret(self, secret_name: str) -> str:
        """
        Get secret from Dapr secret store
        
        Args:
            secret_name: Name of the secret to retrieve
            
        Returns:
            Secret value as string
            
        Raises:
            Exception: If secret not found in Dapr store
        """
        try:
            with self._get_dapr_client() as client:
                secret_response = client.get_secret(
                    store_name=self.secret_store_name,
                    key=secret_name
                )
                
                if secret_response and hasattr(secret_response, 'secret'):
                    secret_dict = secret_response.secret
                    if secret_name in secret_dict:
                        logger.debug(f"Retrieved {secret_name} from Dapr secret store")
                        return secret_dict[secret_name]
                
                raise Exception(f"Secret '{secret_name}' not found in Dapr store")
        except Exception as e:
            logger.debug(f"Failed to get {secret_name} from Dapr: {str(e)}")
            raise
    
    def get_secret_with_fallback(self, secret_name: str) -> str:
        """
        Get secret with Dapr first, ENV fallback
        
        Priority:
        1. Try Dapr secret store first
        2. Fallback to environment variable (from .env file)
        
        Args:
            secret_name: Name of the secret to retrieve
            
        Returns:
            Secret value as string
            
        Raises:
            Exception: If secret not found in either Dapr or ENV
        """
        # Priority 1: Try Dapr secret store
        try:
            value = self.get_secret(secret_name)
            logger.debug(f"{secret_name} retrieved from Dapr secret store")
            return value
        except Exception:
            logger.debug(f"{secret_name} not in Dapr store, trying ENV variable")
        
        # Priority 2: Fallback to environment variable (from .env file)
        env_value = os.getenv(secret_name)
        if env_value:
            logger.debug(f"{secret_name} retrieved from ENV variable")
            return env_value
        
        raise Exception(f"{secret_name} not found in Dapr secret store or ENV variables")
    
    def get_database_config(self) -> Dict[str, str]:
        """
        Get database configuration from Dapr or ENV
        
        Returns:
            Dictionary with database configuration
        """
        mongodb_uri = self.get_secret_with_fallback('MONGODB_URI')
        
        return {
            'uri': mongodb_uri,
            'database': os.getenv('MONGODB_DATABASE', 'product_service_db'),
            'min_pool_size': int(os.getenv('MONGODB_MIN_POOL_SIZE', '10')),
            'max_pool_size': int(os.getenv('MONGODB_MAX_POOL_SIZE', '50')),
        }
    
    def get_jwt_config(self) -> Dict[str, str]:
        """
        Get JWT configuration from Dapr or ENV
        
        Returns:
            Dictionary with JWT configuration
        """
        jwt_secret = self.get_secret_with_fallback('JWT_SECRET')
        
        return {
            'secret': jwt_secret,
            'algorithm': os.getenv('JWT_ALGORITHM', 'HS256'),
            'issuer': os.getenv('JWT_ISSUER', 'product-service'),
        }


# Singleton instance
secret_manager = DaprSecretManager()


# Helper functions for easy access
def get_database_config() -> Dict[str, str]:
    """Get database configuration with secret fallback"""
    return secret_manager.get_database_config()


def get_jwt_config() -> Dict[str, str]:
    """Get JWT configuration with secret fallback"""
    return secret_manager.get_jwt_config()
