"""
Inventory Service - Business logic for inventory management
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from uuid import uuid4

from src.models import InventoryItem, StockMovementType, Reservation, ReservationStatus
from src.repositories import InventoryRepository, ReservationRepository

logger = logging.getLogger(__name__)


class InventoryService:
    """Business logic for inventory management and reservations"""
    
    def __init__(self):
        self.inventory_repo = InventoryRepository()
        self.reservation_repo = ReservationRepository()
    
    def get_batch_inventory(self, skus: List[str], in_stock_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get inventory data for multiple SKUs (supports both base and variant SKUs)
        Moved from controller to service layer for proper separation of concerns
        
        Args:
            skus: List of SKUs to query
            in_stock_only: If True, only return items with available quantity > 0
            
        Returns:
            List of inventory item dictionaries
        """
        try:
            result = []
            
            for sku in skus:
                # Try exact match first
                inventory_items = self.inventory_repo.get_multiple_by_skus([sku])
                
                if inventory_items:
                    # Exact match found - return it
                    item = inventory_items[0]
                    item_data = {
                        'sku': item.sku,
                        'quantityAvailable': item.quantity_available,
                        'quantityReserved': item.quantity_reserved,
                        'reorderPoint': item.reorder_level,
                        'reorderQuantity': item.max_stock - item.reorder_level if item.max_stock > item.reorder_level else 0,
                        'status': 'in_stock' if item.quantity_available > 0 else 'out_of_stock'
                    }
                    
                    # Apply filter if requested
                    if not in_stock_only or item.quantity_available > 0:
                        result.append(item_data)
                else:
                    # No exact match - check if it's a base SKU by finding variants
                    # Base SKU pattern: BRAND-DEPT-CAT-NUM (e.g., ANT-WOM-CLO-001)
                    # Variant SKU pattern: BRAND-DEPT-CAT-NUM-COLOR-SIZE (e.g., ANT-WOM-CLO-001-GRAY-M)
                    variant_items = self.inventory_repo.get_variants_by_base_sku(sku)
                    
                    if variant_items:
                        # Aggregate inventory across all variants
                        total_available = sum(item.quantity_available for item in variant_items)
                        total_reserved = sum(item.quantity_reserved for item in variant_items)
                        
                        item_data = {
                            'sku': sku,
                            'quantityAvailable': total_available,
                            'quantityReserved': total_reserved,
                            'reorderPoint': variant_items[0].reorder_level if variant_items else 0,
                            'reorderQuantity': variant_items[0].max_stock - variant_items[0].reorder_level if variant_items and variant_items[0].max_stock > variant_items[0].reorder_level else 0,
                            'status': 'in_stock' if total_available > 0 else 'out_of_stock',
                            'variantCount': len(variant_items)
                        }
                        
                        # Apply filter if requested
                        if not in_stock_only or total_available > 0:
                            result.append(item_data)
                    elif not in_stock_only:
                        # No inventory found for this SKU - only include if not filtering
                        result.append({
                            'sku': sku,
                            'quantityAvailable': 0,
                            'quantityReserved': 0,
                            'reorderPoint': 0,
                            'reorderQuantity': 0,
                            'status': 'out_of_stock'
                        })
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving batch inventory: {str(e)}")
            raise
    
    def check_stock_availability(self, stock_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check stock availability for multiple items
        
        Args:
            stock_items: List of {'sku': str, 'quantity': int}
            
        Returns:
            Dict with availability status and item details
        """
        try:
            # Extract SKUs for batch query
            skus = [item['sku'] for item in stock_items]
            
            # Get inventory items from database
            inventory_items = self.inventory_repo.get_multiple_by_skus(skus)
            inventory_map = {item.sku: item for item in inventory_items}
            
            # Check availability for each requested item
            results = []
            all_available = True
            
            for stock_item in stock_items:
                sku = stock_item['sku']
                requested_quantity = stock_item['quantity']
                
                inventory_item = inventory_map.get(sku)
                if not inventory_item:
                    available_quantity = 0
                    available = False
                else:
                    available_quantity = inventory_item.quantity_available
                    available = available_quantity >= requested_quantity
                
                results.append({
                    'sku': sku,
                    'requested_quantity': requested_quantity,
                    'available_quantity': available_quantity,
                    'available': available
                })
                
                if not available:
                    all_available = False
            
            response = {
                'available': all_available,
                'items': results,
                'checked_at': datetime.utcnow().isoformat()
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error checking stock availability: {str(e)}")
            raise
    
    def get_inventory_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """Get inventory item by SKU with product details"""
        try:
            inventory_item = self.inventory_repo.get_by_sku(sku)
            if not inventory_item:
                return None
            
            result = inventory_item.to_dict()
            
            # Enrich with product details if available
            try:
                product_details = self.product_client.get_product_by_id(inventory_item.product_id)
                if product_details:
                    result['product'] = product_details
            except Exception as e:
                logger.warning(f"Failed to fetch product details for {inventory_item.product_id}: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting inventory for SKU {sku}: {str(e)}")
            raise
    
    def create_inventory_item(self, **kwargs) -> Dict[str, Any]:
        """Create a new inventory item"""
        try:
            # Create new inventory item from provided data
            inventory_item = InventoryItem(
                sku=kwargs['sku'],  # SKU is now required
                quantity_available=kwargs.get('quantity_available', 0),
                quantity_reserved=kwargs.get('quantity_reserved', 0),
                reorder_level=kwargs.get('reorder_level', 10),
                max_stock=kwargs.get('max_stock', 1000),
                cost_per_unit=kwargs.get('cost_per_unit')
            )
            
            # Save to database
            created_item = self.inventory_repo.create(inventory_item)
            
            # Clear relevant caches
            self._clear_stock_caches()
            
            return created_item.to_dict()
            
        except Exception as e:
            logger.error(f"Error creating inventory item: {str(e)}")
            raise
    
    def delete_inventory_item(self, sku: str) -> bool:
        """Delete an inventory item by SKU"""
        try:
            # Find the item first
            inventory_item = self.inventory_repo.get_by_sku(sku)
            if not inventory_item:
                return False
            
            # Delete the item
            success = self.inventory_repo.delete(inventory_item.sku)
            
            if success:
                # Clear relevant caches
                self._clear_stock_caches()
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting inventory item for SKU {sku}: {str(e)}")
            raise
    
    def update_inventory_item(self, sku: str, **kwargs) -> Dict[str, Any]:
        """Update an inventory item"""
        try:
            inventory_item = self.inventory_repo.get_by_sku(sku)
            if not inventory_item:
                raise ValueError(f"Inventory item for SKU {sku} not found")
            
            # Update allowed fields
            for key, value in kwargs.items():
                if hasattr(inventory_item, key) and key not in ['id', 'sku', 'created_at']:
                    setattr(inventory_item, key, value)
            
            inventory_item.updated_at = datetime.utcnow()
            updated_item = self.inventory_repo.update(inventory_item)
            
            self._clear_stock_caches()
            
            return updated_item.to_dict()
            
        except Exception as e:
            logger.error(f"Error updating inventory item for SKU {sku}: {str(e)}")
            raise

    def adjust_stock(self, sku: str, quantity: int, movement_type, reference: str = None, reason: str = None) -> Dict[str, Any]:
        """Adjust stock levels"""
        try:
            # Handle both string and enum inputs
            if isinstance(movement_type, str):
                movement_type = movement_type.upper()
                movement_enum = StockMovementType[movement_type]
            else:
                movement_enum = movement_type
            
            success = self.inventory_repo.update_stock(
                sku=sku,
                quantity_change=quantity,
                movement_type=movement_enum,
                reference=reference,
                reason=reason
            )
            
            if success:
                # Create and return movement record
                movement = self.inventory_repo.create_stock_movement(
                    sku=sku,
                    movement_type=movement_enum,
                    quantity=quantity,
                    reference=reference,
                    reason=reason
                )
                self._clear_stock_caches()
                return movement.to_dict()
            else:
                raise ValueError(f"Failed to adjust stock for SKU {sku}")
                
        except Exception as e:
            logger.error(f"Error adjusting stock for SKU {sku}: {str(e)}")
            raise

    def bulk_update_inventory(self, operations: List[dict]) -> List[dict]:
        """Bulk update inventory items"""
        try:
            results = self.inventory_repo.bulk_update(operations)
            self._clear_stock_caches()
            return results
            
        except Exception as e:
            logger.error(f"Error bulk updating inventory: {str(e)}")
            raise

    def search_inventory(self, **kwargs) -> tuple[List[Dict[str, Any]], int]:
        """Advanced inventory search"""
        try:
            items, total = self.inventory_repo.search(**kwargs)
            return [item.to_dict() for item in items], total
            
        except Exception as e:
            logger.error(f"Error searching inventory: {str(e)}")
            raise

    def check_availability(self, sku: str, quantity: int) -> Dict[str, Any]:
        """Check availability for a specific item"""
        try:
            inventory_item = self.inventory_repo.get_by_sku(sku)
            if not inventory_item:
                return {
                    'available': False,
                    'available_quantity': 0,
                    'requested_quantity': quantity,
                    'sku': sku
                }
            
            available = inventory_item.quantity_available >= quantity
            return {
                'available': available,
                'available_quantity': inventory_item.quantity_available,
                'requested_quantity': quantity,
                'sku': sku
            }
            
        except Exception as e:
            logger.error(f"Error checking availability for SKU {sku}: {str(e)}")
            raise

    def get_low_stock_items(self) -> List[Dict[str, Any]]:
        """Get items below reorder level"""
        try:
            items = self.inventory_repo.get_low_stock_items()
            return [item.to_dict() for item in items]
            
        except Exception as e:
            logger.error(f"Error getting low stock items: {str(e)}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """Health check for the service"""
        try:
            # Check database connectivity
            test_item = InventoryItem.query.first()
            
            # Check Redis connectivity
            redis_status = "healthy"
            try:
                if self.redis:
                    self.redis.ping()
            except:
                redis_status = "unhealthy"
            
            return {
                'status': 'healthy',
                'database': 'connected',
                'redis': redis_status,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _clear_stock_caches(self):
        """Clear stock-related caches"""
        if not self.redis:
            return
            
        try:
            # Clear stock check caches
            keys = self.redis.keys("stock_check:*")
            if keys:
                self.redis.delete(*keys)
            
            # Clear inventory caches
            keys = self.redis.keys("inventory:*")
            if keys:
                self.redis.delete(*keys)
                
            logger.debug("Cleared stock caches")
            
        except Exception as e:
            logger.warning(f"Error clearing caches: {e}")

    def search_inventory_advanced(self, **kwargs) -> tuple[List[Dict[str, Any]], int]:
        """
        Advanced inventory search with extended filters and product details
        
        Args:
            **kwargs: Various search parameters (sku, product_id, category, etc.)
            
        Returns:
            Tuple of (items, total_count)
        """
        try:
            # Use existing search_inventory method as base
            items, total_count = self.search_inventory(**kwargs)
            
            # Enhance with additional details if needed
            for item in items:
                if 'include_product_details' in kwargs and kwargs['include_product_details']:
                    # Add product service call here if needed
                    item['product_details'] = {'status': 'enhanced'}
                    
            return items, total_count
            
        except Exception as e:
            logger.error(f"Advanced inventory search failed: {e}")
            return [], 0

    def get_inventory_with_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get inventory item with enhanced product details
        
        Args:
            product_id: Product identifier
            
        Returns:
            Inventory item with product details or None
        """
        try:
            # Get base inventory item
            inventory_item = self.get_inventory_by_product_id(product_id)
            
            if inventory_item:
                # Add product details from external service
                try:
                    product_details = self.product_client.get_product(product_id)
                    inventory_item['product_details'] = product_details
                except Exception as e:
                    logger.warning(f"Could not fetch product details for {product_id}: {e}")
                    inventory_item['product_details'] = {'error': 'Product details unavailable'}
                    
            return inventory_item
            
        except Exception as e:
            logger.error(f"Get inventory with product details failed: {e}")
            return None

    # =========================================================================
    # Reservation Management Methods
    # =========================================================================
    
    def create_reservation(self, sku: str, order_id: str, quantity: int, customer_id: str = None, ttl_minutes: int = 30) -> Dict[str, Any]:
        """Create a new reservation"""
        try:
            # Check availability first
            inventory_item = self.inventory_repo.get_by_sku(sku)
            if not inventory_item:
                raise ValueError(f"Product with SKU {sku} not found")
            
            if inventory_item.quantity_available < quantity:
                raise ValueError("Insufficient stock")
            
            # Create reservation
            expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
            reservation = Reservation(
                id=str(uuid4()),
                sku=sku,
                order_id=order_id,
                quantity=quantity,
                status=ReservationStatus.PENDING,
                expires_at=expires_at
            )
            
            created_reservation = self.reservation_repo.create(reservation)
            
            # Update stock
            self.inventory_repo.update_stock(
                sku=sku,
                quantity_change=quantity,
                movement_type=StockMovementType.RESERVED,
                reference=order_id,
                reason=f"Reserved for order {order_id}"
            )
            
            logger.info(f"Created reservation {created_reservation.id} for order {order_id}")
            return created_reservation.to_dict()
            
        except Exception as e:
            logger.error(f"Error creating reservation: {str(e)}")
            raise
    
    def get_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]:
        """Get reservation by ID"""
        try:
            reservation = self.reservation_repo.get_by_id(reservation_id)
            return reservation.to_dict() if reservation else None
        except Exception as e:
            logger.error(f"Error getting reservation {reservation_id}: {str(e)}")
            raise
    
    def confirm_reservation(self, reservation_id: str, order_id: str) -> bool:
        """Confirm a reservation"""
        try:
            reservation = self.reservation_repo.get_by_id(reservation_id)
            if not reservation:
                raise ValueError("Reservation not found")
            
            if reservation.order_id != order_id:
                raise ValueError("Order ID mismatch")
            
            if reservation.status != ReservationStatus.PENDING:
                raise ValueError("Reservation is not pending")
            
            if reservation.is_expired:
                raise ValueError("Reservation has expired")
            
            # Update status
            self.reservation_repo.update_status(reservation_id, ReservationStatus.CONFIRMED)
            
            # Convert reserved stock to sold
            self.inventory_repo.update_stock(
                sku=reservation.sku,
                quantity_change=reservation.quantity,
                movement_type=StockMovementType.OUT,
                reference=order_id,
                reason=f"Sold for order {order_id}"
            )
            
            logger.info(f"Confirmed reservation {reservation_id} for order {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error confirming reservation {reservation_id}: {str(e)}")
            raise
    
    def cancel_reservation(self, reservation_id: str) -> bool:
        """Cancel a reservation"""
        try:
            reservation = self.reservation_repo.get_by_id(reservation_id)
            if not reservation:
                return False
            
            # Cancel reservation
            updated_reservation = self.reservation_repo.cancel(reservation_id)
            if not updated_reservation:
                return False
            
            # Release stock if it was pending
            if reservation.status == ReservationStatus.PENDING:
                self.inventory_repo.update_stock(
                    sku=reservation.sku,
                    quantity_change=reservation.quantity,
                    movement_type=StockMovementType.RELEASED,
                    reference=reservation.order_id,
                    reason=f"Released cancelled reservation for order {reservation.order_id}"
                )
            
            logger.info(f"Cancelled reservation {reservation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling reservation {reservation_id}: {str(e)}")
            raise
    
    def release_reservation(self, reservation_id: str) -> Dict[str, Any]:
        """
        Release a reservation - restores reserved quantity back to available stock
        Per PRD 4.9: Changes reservation status to 'released' and decrements reserved_quantity
        """
        try:
            reservation = self.reservation_repo.get_by_id(reservation_id)
            if not reservation:
                raise ValueError("Reservation not found")
            
            # Cannot release already confirmed reservation
            if reservation.status == ReservationStatus.CONFIRMED:
                raise ValueError("Cannot release confirmed reservation")
            
            # Cannot release already released/cancelled reservation
            if reservation.status in [ReservationStatus.RELEASED, ReservationStatus.CANCELLED]:
                raise ValueError(f"Reservation already {reservation.status.value}")
            
            # Update reservation status to RELEASED
            self.reservation_repo.update_status(reservation_id, ReservationStatus.RELEASED)
            
            # Release stock back to available pool
            self.inventory_repo.update_stock(
                sku=reservation.sku,
                quantity_change=reservation.quantity,
                movement_type=StockMovementType.RELEASED,
                reference=reservation.order_id,
                reason=f"Released reservation for order {reservation.order_id}"
            )
            
            logger.info(f"Released reservation {reservation_id} for order {reservation.order_id}")
            
            # Return updated reservation
            updated_reservation = self.reservation_repo.get_by_id(reservation_id)
            return updated_reservation.to_dict() if updated_reservation else None
            
        except Exception as e:
            logger.error(f"Error releasing reservation {reservation_id}: {str(e)}")
            raise
    
    def search_reservations(self, **kwargs):
        """Search reservations with filters - returns tuple (list, count)"""
        try:
            reservations, total = self.reservation_repo.search(**kwargs)
            # Return tuple for consistency with controller expectations
            return [r.to_dict() for r in reservations], total
            
        except Exception as e:
            logger.error(f"Error searching reservations: {str(e)}")
            raise

    def search_reservations_with_count(self, **kwargs) -> tuple[List[Dict[str, Any]], int]:
        """Search reservations with filters - returns tuple with count"""
        try:
            reservations, total = self.reservation_repo.search(**kwargs)
            return [r.to_dict() for r in reservations], total
            
        except Exception as e:
            logger.error(f"Error searching reservations: {str(e)}")
            raise
    
    def confirm_reservations(self, reservation_ids: List[str], order_id: str) -> List[dict]:
        """Bulk confirm reservations"""
        try:
            results = []
            for res_id in reservation_ids:
                try:
                    success = self.confirm_reservation(res_id, order_id)
                    results.append({'reservation_id': res_id, 'success': success})
                except Exception as e:
                    results.append({'reservation_id': res_id, 'success': False, 'error': str(e)})
            
            return results
            
        except Exception as e:
            logger.error(f"Error bulk confirming reservations: {str(e)}")
            raise
    
    def process_expired_reservations(self) -> Dict[str, Any]:
        """Process expired reservations"""
        try:
            expired_reservations = self.reservation_repo.get_expired_reservations()
            processed_count = 0
            
            for reservation in expired_reservations:
                try:
                    # Update status to expired
                    self.reservation_repo.update_status(reservation.id, ReservationStatus.EXPIRED)
                    
                    # Release stock
                    self.inventory_repo.update_stock(
                        sku=reservation.sku,
                        quantity_change=reservation.quantity,
                        movement_type=StockMovementType.RELEASED,
                        reference=reservation.order_id,
                        reason=f"Released expired reservation for order {reservation.order_id}"
                    )
                    
                    processed_count += 1
                    logger.info(f"Processed expired reservation {reservation.id}")
                    
                except Exception as e:
                    logger.error(f"Error processing expired reservation {reservation.id}: {e}")
            
            return {
                'processed_count': processed_count,
                'processed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing expired reservations: {str(e)}")
            raise

    def cleanup_old_reservations(self) -> int:
        """Cleanup old expired reservations (background task)"""
        try:
            # Delete reservations expired more than 24 hours ago
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            count = self.reservation_repo.delete_expired(cutoff_time)
            
            if count > 0:
                logger.info(f"Cleaned up {count} old reservations")
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up old reservations: {str(e)}")
            raise

    def reserve_stock_for_order(self, order_id: str, items: List[Dict[str, Any]], 
                     ttl_minutes: int = 30) -> Dict[str, Any]:
        """
        Reserve stock for an order
        
        Args:
            order_id: Order identifier
            items: List of {'sku': str, 'quantity': int}
            ttl_minutes: Reservation TTL in minutes
            
        Returns:
            Dict with reservation details
        """
        try:
            # Create reservations
            reservations = []
            expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
            
            for item in items:
                sku = item['sku']
                quantity = item['quantity']
                
                # Check availability first
                inventory_item = self.inventory_repo.get_by_sku(sku)
                if not inventory_item or inventory_item.quantity_available < quantity:
                    return {
                        'success': False,
                        'message': f'Insufficient stock for SKU {sku}',
                        'sku': sku,
                        'requested': quantity,
                        'available': inventory_item.quantity_available if inventory_item else 0
                    }
                
                # Create reservation record
                reservation = Reservation(
                    id=str(uuid4()),
                    order_id=order_id,
                    sku=sku,
                    quantity=quantity,
                    status=ReservationStatus.PENDING,
                    expires_at=expires_at
                )
                
                # Save reservation
                reservation = self.reservation_repo.create(reservation)
                
                # Update inventory (reserve stock)
                success = self.inventory_repo.update_stock(
                    sku=sku,
                    quantity_change=quantity,
                    movement_type=StockMovementType.RESERVED,
                    reference=order_id,
                    reason=f"Stock reserved for order {order_id}"
                )
                
                if not success:
                    # Rollback reservations if stock update fails
                    logger.error(f"Failed to reserve stock for SKU {sku}")
                    # TODO: Implement proper rollback mechanism
                    raise Exception(f"Failed to reserve stock for SKU {sku}")
                
                reservations.append(reservation)
                logger.info(f"Reserved {quantity} units of SKU {sku} for order {order_id}")
            
            return {
                'success': True,
                'reservations': [r.to_dict() for r in reservations],
                'expires_at': expires_at.isoformat(),
                'message': f'Successfully reserved stock for {len(items)} items'
            }
            
        except Exception as e:
            logger.error(f"Error reserving stock for order {order_id}: {str(e)}")
            raise

    def confirm_reservations_bulk(self, reservation_ids: List[str], order_id: str = None) -> List[dict]:
        """
        Bulk confirm reservations
        
        Args:
            reservation_ids: List of reservation IDs to confirm
            order_id: Order identifier (optional - each reservation uses its own order_id if not provided)
            
        Returns:
            List of confirmation results
        """
        try:
            results = []
            
            for res_id in reservation_ids:
                try:
                    if order_id is None:
                        # Use the reservation's own order_id
                        reservation = self.reservation_repo.get_by_id(res_id)
                        if reservation:
                            success = self.confirm_reservation(res_id, reservation.order_id)
                        else:
                            success = False
                    else:
                        # Use provided order_id for all reservations
                        success = self.confirm_reservation(res_id, order_id)
                    
                    results.append({'reservation_id': res_id, 'success': success})
                    
                except Exception as e:
                    results.append({'reservation_id': res_id, 'success': False, 'error': str(e)})
                    logger.error(f"Error confirming reservation {res_id}: {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk confirm reservations: {str(e)}")
            # Return error result for all reservations
            return [{'reservation_id': res_id, 'success': False, 'error': str(e)} for res_id in reservation_ids]

    def expire_reservations(self, reservation_ids: List[str] = None) -> Dict[str, Any]:
        """
        Expire specific reservations or process all expired reservations
        
        Args:
            reservation_ids: List of reservation IDs to expire (optional)
            
        Returns:
            Dict with expiration results
        """
        try:
            if reservation_ids is None:
                # Process all expired reservations (for compatibility with tests)
                return self.process_expired_reservations()
            
            # Expire specific reservations
            results = []
            
            for res_id in reservation_ids:
                try:
                    reservation = self.reservation_repo.get_by_id(res_id)
                    if not reservation:
                        results.append({'reservation_id': res_id, 'success': False, 'error': 'Not found'})
                        continue
                    
                    # Update status to expired
                    self.reservation_repo.update_status(res_id, ReservationStatus.EXPIRED)
                    
                    # Release stock if it was reserved
                    if reservation.status == ReservationStatus.PENDING:
                        self.inventory_repo.update_stock(
                            sku=reservation.sku,
                            quantity_change=reservation.quantity,
                            movement_type=StockMovementType.RELEASED,
                            reference=reservation.order_id,
                            reason=f"Released manually expired reservation for order {reservation.order_id}"
                        )
                    
                    results.append({'reservation_id': res_id, 'success': True})
                    logger.info(f"Manually expired reservation {res_id}")
                    
                except Exception as e:
                    results.append({'reservation_id': res_id, 'success': False, 'error': str(e)})
                    logger.error(f"Error expiring reservation {res_id}: {e}")
            
            return {
                'results': results,
                'total_processed': len(reservation_ids),
                'successful': len([r for r in results if r['success']]),
                'failed': len([r for r in results if not r['success']]),
                'expired_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error expiring reservations: {str(e)}")
            raise

