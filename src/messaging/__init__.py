"""
Messaging Abstraction Layer for Inventory Service
Implements Architecture spec section 5.5
"""
from .provider import MessagingProvider
from .factory import create_messaging_provider

__all__ = ['MessagingProvider', 'create_messaging_provider']
