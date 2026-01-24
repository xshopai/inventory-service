"""
Controllers package initialization
"""

# Import all blueprints for registration
from src.controllers.inventory import inventory_bp
from src.controllers.reservations import reservations_bp
from src.controllers.stats import stats_bp
from src.controllers.home import home_bp
from src.controllers.events import events_bp
from src.controllers.operational import operational_hp
from src.controllers.admin import admin_bp

__all__ = ['inventory_bp', 'reservations_bp', 'stats_bp', 'home_bp', 'events_bp', 'operational_hp', 'admin_bp']
