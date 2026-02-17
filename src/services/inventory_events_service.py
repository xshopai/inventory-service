"""
Inventory Events Service - Business logic for handling external events
"""

from flask import current_app
from typing import Dict, Any
from datetime import datetime, timedelta, timezone
import uuid

from src.database import db
from src.models import InventoryItem, Reservation
from src.models.enums import ReservationStatus
from src.utils.event_publisher import event_publisher


class InventoryEventsService:
    """Service for handling inventory-related events from other services"""
    
    # ============================================================================
    # Product Events
    # ============================================================================
    
    @staticmethod
    def handle_product_created(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle product.created event from product-service.
        Initialize inventory records for all product variants (SKUs).
        
        Event payload structure:
        {
            "data": {
                "productId": "prod-123",
                "name": "iPhone 15",
                "variants": [
                    {"sku": "IP15-BLK-128", "color": "Black", "size": "128GB", "initial_stock": 50},
                    {"sku": "IP15-WHT-128", "color": "White", "size": "128GB", "initial_stock": 30}
                ]
            }
        }
        """
        try:
            data = event_data.get('data', {})
            product_id = data.get('productId')
            product_name = data.get('name', 'Unknown Product')
            variants = data.get('variants', [])
            correlation_id = event_data.get('correlationid') or event_data.get('correlationId')
            
            if not product_id:
                raise ValueError("Missing productId in event data")
            
            if not variants:
                current_app.logger.warning(
                    f"⚠️ No variants found for product: {product_id}. Skipping inventory creation.",
                    extra={"correlationId": correlation_id, "productId": product_id}
                )
                return {"status": "skipped", "message": "No variants to process"}
            
            current_app.logger.info(
                f"📦 Handling product.created for product: {product_id} ({product_name}) with {len(variants)} variants",
                extra={"correlationId": correlation_id, "productId": product_id, "variantCount": len(variants)}
            )
            
            created_items = []
            
            # Create inventory record for each variant/SKU
            for variant in variants:
                sku = variant.get('sku')
                initial_stock = variant.get('initial_stock', 0)
                color = variant.get('color')
                size = variant.get('size')
                
                if not sku:
                    current_app.logger.warning(
                        f"⚠️ Variant missing SKU, skipping",
                        extra={"correlationId": correlation_id, "variant": variant}
                    )
                    continue
                
                # Check if inventory already exists for this SKU
                existing_inventory = InventoryItem.query.filter_by(sku=sku).first()
                if existing_inventory:
                    current_app.logger.warning(
                        f"⚠️ InventoryItem already exists for SKU: {sku}",
                        extra={"correlationId": correlation_id, "sku": sku}
                    )
                    continue
                
                # Create new inventory record with initial stock
                new_inventory = InventoryItem(
                    sku=sku,
                    quantity_available=initial_stock,
                    quantity_reserved=0,
                    reorder_level=10,
                    max_stock=1000
                )
                
                db.session.add(new_inventory)
                created_items.append({
                    "sku": sku,
                    "initial_stock": initial_stock,
                    "color": color,
                    "size": size
                })
                
                current_app.logger.info(
                    f"✅ Created inventory for SKU: {sku} (initial stock: {initial_stock})",
                    extra={"correlationId": correlation_id, "sku": sku, "initialStock": initial_stock}
                )
            
            db.session.commit()
            
            # Publish inventory.created event for each SKU
            for item in created_items:
                event_publisher.publish_inventory_created(
                    sku=item["sku"],
                    initial_quantity=item["initial_stock"],
                    correlation_id=correlation_id
                )
            
            current_app.logger.info(
                f"✅ Created {len(created_items)} inventory records for product: {product_id}",
                extra={"correlationId": correlation_id, "productId": product_id, "createdCount": len(created_items)}
            )
            
            return {
                "status": "success",
                "message": f"Created {len(created_items)} inventory records for product {product_id}",
                "created_skus": [item["sku"] for item in created_items]
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"❌ Error handling product.created: {str(e)}",
                extra={"error": str(e), "correlationId": event_data.get('correlationid')}
            )
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def handle_product_updated(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle product.updated event from product-service.
        Update product reference information in inventory.
        Currently minimal processing - inventory tracks by SKU only.
        """
        try:
            data = event_data.get('data', {})
            product_id = data.get('productId')
            variants = data.get('variants', [])
            correlation_id = event_data.get('correlationid') or event_data.get('correlationId')
            
            if not product_id:
                raise ValueError("Missing productId in event data")
            
            current_app.logger.info(
                f"📝 Handling product.updated for product: {product_id} with {len(variants)} variants",
                extra={"correlationId": correlation_id, "productId": product_id}
            )
            
            # Inventory is SKU-based, not product-based
            # No action needed unless variants changed (which would be handled separately)
            # This event is mainly for audit/logging purposes
            
            current_app.logger.info(
                f"✅ Acknowledged product.updated for product: {product_id}",
                extra={"correlationId": correlation_id}
            )
            
            return {
                "status": "success",
                "message": f"Product update acknowledged for {product_id}"
            }
            
        except Exception as e:
            current_app.logger.error(
                f"❌ Error handling product.updated: {str(e)}",
                extra={"error": str(e), "correlationId": event_data.get('correlationid')}
            )
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def handle_product_deleted(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle product.deleted event from product-service.
        Archive all inventory records for product's SKUs.
        """
        try:
            data = event_data.get('data', {})
            product_id = data.get('productId')
            variants = data.get('variants', [])
            correlation_id = event_data.get('correlationid') or event_data.get('correlationId')
            
            if not product_id:
                raise ValueError("Missing productId in event data")
            
            # Extract all SKUs from variants
            skus = [v.get('sku') for v in variants if v.get('sku')]
            
            current_app.logger.info(
                f"🗑️ Handling product.deleted for product: {product_id} with {len(skus)} SKUs to archive",
                extra={"correlationId": correlation_id, "productId": product_id, "skus": skus}
            )
            
            if not skus:
                current_app.logger.warning(
                    f"⚠️ No SKUs found in product.deleted event for product: {product_id}",
                    extra={"correlationId": correlation_id}
                )
                return {"status": "skipped", "message": "No SKUs to archive"}
            
            deleted_count = 0
            
            # Delete inventory for each SKU (soft-delete not supported - model has no is_active)
            for sku in skus:
                inventory = InventoryItem.query.filter_by(sku=sku).first()
                if inventory:
                    # Check if there are active reservations
                    active_reservations = Reservation.query.filter(
                        Reservation.sku == sku,
                        Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.CONFIRMED])
                    ).count()
                    
                    if active_reservations > 0:
                        current_app.logger.warning(
                            f"⚠️ Cannot delete inventory for SKU: {sku} - has {active_reservations} active reservations",
                            extra={"correlationId": correlation_id, "sku": sku, "activeReservations": active_reservations}
                        )
                        continue
                    
                    db.session.delete(inventory)
                    deleted_count += 1
                    current_app.logger.info(
                        f"✅ Deleted inventory for SKU: {sku}",
                        extra={"correlationId": correlation_id, "sku": sku}
                    )
                else:
                    current_app.logger.warning(
                        f"⚠️ InventoryItem not found for SKU: {sku}",
                        extra={"correlationId": correlation_id, "sku": sku}
                    )
            
            db.session.commit()
            
            current_app.logger.info(
                f"✅ Deleted {deleted_count} inventory records for deleted product: {product_id}",
                extra={"correlationId": correlation_id, "deletedCount": deleted_count}
            )
            
            return {
                "status": "success",
                "message": f"Deleted {deleted_count} inventory records for product {product_id}",
                "deleted_skus": skus
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"❌ Error handling product.deleted: {str(e)}",
                extra={"error": str(e), "correlationId": event_data.get('correlationid')}
            )
            return {"status": "error", "message": str(e)}
    
    # ============================================================================
    # Order Events
    # ============================================================================
    
    @staticmethod
    def handle_order_created(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle order.created event from order-service.
        Reserve stock for the order items.
        
        Event payload structure:
        {
            "data": {
                "orderId": "order-123",
                "items": [
                    {"sku": "SKU-001", "quantity": 2},
                    {"sku": "SKU-002", "quantity": 1}
                ]
            }
        }
        
        Note: SKUs may be variant SKUs (e.g., "WOM-CLO-TOP-001-BLACK-M") or base SKUs.
        This handler extracts the base SKU (first 4 segments) if the variant SKU is not found.
        """
        try:
            data = event_data.get('data', {})
            order_id = data.get('orderId')
            items = data.get('items', [])
            correlation_id = event_data.get('correlationid') or event_data.get('correlationId')
            
            if not order_id or not items:
                raise ValueError("Missing orderId or items in event data")
            
            current_app.logger.info(
                f"📦 Handling order.created for order: {order_id}",
                extra={"correlationId": correlation_id, "itemCount": len(items)}
            )
            
            reservations_created = []
            
            for item in items:
                sku = item.get('sku')
                quantity = item.get('quantity', 0)
                
                if not sku or quantity <= 0:
                    current_app.logger.warning(
                        f"⚠️ Invalid item in order: sku={sku}, quantity={quantity}",
                        extra={"correlationId": correlation_id}
                    )
                    continue
                
                # Find inventory by SKU (lock for update to prevent race conditions)
                inventory = InventoryItem.query.filter_by(
                    sku=sku
                ).with_for_update().first()
                
                # If not found, try to extract base SKU from variant SKU
                # Variant SKU format: BASE-SKU-COLOR-SIZE (e.g., WOM-CLO-TOP-001-BLACK-M)
                # Base SKU format: DEPT-CAT-SUBCAT-NUM (e.g., WOM-CLO-TOP-001)
                lookup_sku = sku
                if not inventory:
                    parts = sku.split('-')
                    # Base SKU has 4 parts (e.g., WOM-CLO-TOP-001)
                    # If we have more parts, it's likely a variant SKU
                    if len(parts) > 4:
                        base_sku = '-'.join(parts[:4])
                        current_app.logger.info(
                            f"🔍 Variant SKU detected, trying base SKU: {base_sku}",
                            extra={"correlationId": correlation_id, "originalSku": sku}
                        )
                        inventory = InventoryItem.query.filter_by(
                            sku=base_sku
                        ).with_for_update().first()
                        lookup_sku = base_sku
                
                if not inventory:
                    current_app.logger.error(
                        f"❌ InventoryItem not found for SKU: {sku} (also tried base SKU extraction)",
                        extra={"correlationId": correlation_id}
                    )
                    db.session.rollback()
                    # Publish failure event for saga compensation
                    event_publisher.publish_reservation_failed(
                        order_id=order_id,
                        sku=sku,
                        reason="Inventory item not found",
                        requested_quantity=quantity,
                        available_quantity=0,
                        correlation_id=correlation_id
                    )
                    # Return business_error - permanent failure, should not retry
                    return {
                        "status": "business_error",
                        "message": f"InventoryItem not found for SKU {sku}"
                    }
                
                # Check available stock (quantity_available minus already reserved)
                if inventory.quantity_available < quantity:
                    current_app.logger.error(
                        f"❌ Insufficient stock for SKU: {lookup_sku} "
                        f"(available: {inventory.quantity_available}, requested: {quantity})",
                        extra={"correlationId": correlation_id}
                    )
                    db.session.rollback()
                    # Publish failure event for saga compensation
                    event_publisher.publish_reservation_failed(
                        order_id=order_id,
                        sku=lookup_sku,
                        reason="Insufficient stock",
                        requested_quantity=quantity,
                        available_quantity=inventory.quantity_available,
                        correlation_id=correlation_id
                    )
                    # Return business_error - permanent failure, should not retry
                    return {
                        "status": "business_error",
                        "message": f"Insufficient stock for SKU {lookup_sku}"
                    }
                
                # Create reservation (using the lookup SKU for consistency)
                reservation_id = str(uuid.uuid4())
                reservation = Reservation(
                    id=reservation_id,
                    sku=lookup_sku,
                    order_id=order_id,
                    quantity=quantity,
                    status=ReservationStatus.PENDING,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
                )
                
                # Move stock from available to reserved
                inventory.quantity_available -= quantity
                inventory.quantity_reserved += quantity
                
                db.session.add(reservation)
                reservations_created.append({
                    "reservationId": reservation_id,
                    "sku": sku,
                    "quantity": quantity
                })
                
                # Publish stock.reserved event
                event_publisher.publish_stock_reserved(
                    sku=sku,
                    quantity=quantity,
                    order_id=order_id,
                    reservation_id=reservation_id,
                    correlation_id=correlation_id
                )
            
            db.session.commit()
            
            current_app.logger.info(
                f"✅ Reserved stock for order: {order_id} ({len(reservations_created)} items)",
                extra={"correlationId": correlation_id}
            )
            
            return {
                "status": "success",
                "message": f"Stock reserved for order {order_id}",
                "reservations": reservations_created
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"❌ Error handling order.created: {str(e)}",
                extra={"error": str(e), "correlationId": event_data.get('correlationid')}
            )
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def handle_order_cancelled(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle order.cancelled event from order-service.
        Release reserved stock for the cancelled order.
        
        Event payload structure:
        {
            "data": {
                "orderId": "order-123",
                "reason": "Customer cancelled"
            }
        }
        """
        try:
            data = event_data.get('data', {})
            order_id = data.get('orderId')
            reason = data.get('reason', 'Order cancelled')
            correlation_id = event_data.get('correlationid') or event_data.get('correlationId')
            
            if not order_id:
                raise ValueError("Missing orderId in event data")
            
            current_app.logger.info(
                f"🔄 Handling order.cancelled for order: {order_id}",
                extra={"correlationId": correlation_id}
            )
            
            # Find all reservations for this order (PENDING or ACTIVE status)
            reservations = Reservation.query.filter(
                Reservation.order_id == order_id,
                Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.ACTIVE])
            ).all()
            
            if not reservations:
                current_app.logger.warning(
                    f"⚠️ No active reservations found for order: {order_id}",
                    extra={"correlationId": correlation_id}
                )
                return {"status": "not_found", "message": "No reservations found"}
            
            released_count = 0
            
            for reservation in reservations:
                inventory = InventoryItem.query.filter_by(
                    sku=reservation.sku
                ).with_for_update().first()
                
                if inventory:
                    # Move stock from reserved back to available
                    inventory.quantity_reserved = max(0, inventory.quantity_reserved - reservation.quantity)
                    inventory.quantity_available += reservation.quantity
                    
                    # Update reservation status to CANCELLED
                    reservation.status = ReservationStatus.CANCELLED
                    
                    event_publisher.publish_stock_released(
                        sku=reservation.sku,
                        quantity=reservation.quantity,
                        order_id=order_id,
                        reason=reason,
                        correlation_id=correlation_id
                    )
                    
                    released_count += 1
            
            db.session.commit()
            
            current_app.logger.info(
                f"✅ Released stock for cancelled order: {order_id} ({released_count} items)",
                extra={"correlationId": correlation_id}
            )
            
            return {
                "status": "success",
                "message": f"Stock released for order {order_id}",
                "itemsReleased": released_count
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"❌ Error handling order.cancelled: {str(e)}",
                extra={"error": str(e), "correlationId": event_data.get('correlationid')}
            )
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def handle_order_completed(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle order.completed event from order-service.
        Confirm reserved stock finalization - reserved stock is now sold.
        
        Event payload structure:
        {
            "data": {
                "orderId": "order-123"
            }
        }
        """
        try:
            data = event_data.get('data', {})
            order_id = data.get('orderId')
            correlation_id = event_data.get('correlationid') or event_data.get('correlationId')
            
            if not order_id:
                raise ValueError("Missing orderId in event data")
            
            current_app.logger.info(
                f"✅ Handling order.completed for order: {order_id}",
                extra={"correlationId": correlation_id}
            )
            
            reservations = Reservation.query.filter(
                Reservation.order_id == order_id,
                Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.ACTIVE, ReservationStatus.CONFIRMED])
            ).all()
            
            if not reservations:
                current_app.logger.warning(
                    f"⚠️ No active reservations found for order: {order_id}",
                    extra={"correlationId": correlation_id}
                )
                return {"status": "not_found", "message": "No reservations found"}
            
            completed_count = 0
            
            for reservation in reservations:
                inventory = InventoryItem.query.filter_by(
                    sku=reservation.sku
                ).with_for_update().first()
                
                if inventory:
                    # Reserved stock is now officially sold - just reduce the reserved quantity
                    # (quantity_available was already reduced when reservation was created)
                    inventory.quantity_reserved = max(0, inventory.quantity_reserved - reservation.quantity)
                    
                    # Mark reservation as released (completed)
                    reservation.status = ReservationStatus.RELEASED
                    
                    event_publisher.publish_stock_updated(
                        sku=reservation.sku,
                        quantity=inventory.quantity_available,
                        correlation_id=correlation_id
                    )
                    
                    # Check for low stock (compare available against reorder_level)
                    if inventory.quantity_available <= inventory.reorder_level:
                        if inventory.quantity_available == 0:
                            event_publisher.publish_out_of_stock_alert(
                                sku=reservation.sku,
                                correlation_id=correlation_id
                            )
                        else:
                            event_publisher.publish_low_stock_alert(
                                sku=reservation.sku,
                                current_quantity=inventory.quantity_available,
                                threshold=inventory.reorder_level,
                                correlation_id=correlation_id
                            )
                    
                    completed_count += 1
            
            db.session.commit()
            
            current_app.logger.info(
                f"✅ Completed stock deduction for order: {order_id} ({completed_count} items)",
                extra={"correlationId": correlation_id}
            )
            
            return {
                "status": "success",
                "message": f"Stock deducted for order {order_id}",
                "itemsCompleted": completed_count
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"❌ Error handling order.completed: {str(e)}",
                extra={"error": str(e), "correlationId": event_data.get('correlationid')}
            )
            return {"status": "error", "message": str(e)}

    # ============================================================================
    # Payment Events
    # ============================================================================
    
    @staticmethod
    def handle_payment_received(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle payment.received event from payment-service.
        Confirm stock reservation (mark as confirmed).
        
        Event payload structure:
        {
            "data": {
                "orderId": "order-123",
                "paymentId": "payment-456"
            }
        }
        """
        try:
            data = event_data.get('data', {})
            order_id = data.get('orderId')
            payment_id = data.get('paymentId')
            correlation_id = event_data.get('correlationid') or event_data.get('correlationId')
            
            if not order_id:
                raise ValueError("Missing orderId in event data")
            
            current_app.logger.info(
                f"💳 Handling payment.received for order: {order_id}",
                extra={"correlationId": correlation_id, "paymentId": payment_id}
            )
            
            # Find all reservations for this order (PENDING or ACTIVE status)
            reservations = Reservation.query.filter(
                Reservation.order_id == order_id,
                Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.ACTIVE])
            ).all()
            
            if not reservations:
                current_app.logger.warning(
                    f"⚠️ No active reservations found for order: {order_id}",
                    extra={"correlationId": correlation_id}
                )
                return {"status": "not_found", "message": "No reservations found"}
            
            confirmed_count = 0
            
            for reservation in reservations:
                reservation.status = ReservationStatus.CONFIRMED
                confirmed_count += 1
            
            db.session.commit()
            
            current_app.logger.info(
                f"✅ Confirmed stock reservation for order: {order_id} ({confirmed_count} items)",
                extra={"correlationId": correlation_id}
            )
            
            return {
                "status": "success",
                "message": f"Reservation confirmed for order {order_id}",
                "itemsConfirmed": confirmed_count
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"❌ Error handling payment.received: {str(e)}",
                extra={"error": str(e), "correlationId": event_data.get('correlationid')}
            )
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def handle_payment_failed(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle payment.failed event from payment-service.
        Release reserved stock (same as order cancelled).
        
        Event payload structure:
        {
            "data": {
                "orderId": "order-123",
                "reason": "Insufficient funds"
            }
        }
        """
        try:
            data = event_data.get('data', {})
            order_id = data.get('orderId')
            reason = data.get('reason', 'Payment failed')
            correlation_id = event_data.get('correlationid') or event_data.get('correlationId')
            
            if not order_id:
                raise ValueError("Missing orderId in event data")
            
            current_app.logger.info(
                f"❌ Handling payment.failed for order: {order_id}",
                extra={"correlationId": correlation_id, "reason": reason}
            )
            
            # Find all reservations for this order (PENDING or ACTIVE status)
            reservations = Reservation.query.filter(
                Reservation.order_id == order_id,
                Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.ACTIVE])
            ).all()
            
            if not reservations:
                current_app.logger.warning(
                    f"⚠️ No active reservations found for order: {order_id}",
                    extra={"correlationId": correlation_id}
                )
                return {"status": "not_found", "message": "No reservations found"}
            
            released_count = 0
            
            for reservation in reservations:
                inventory = InventoryItem.query.filter_by(
                    sku=reservation.sku
                ).with_for_update().first()
                
                if inventory:
                    # Return stock from reserved to available
                    inventory.quantity_reserved = max(0, inventory.quantity_reserved - reservation.quantity)
                    inventory.quantity_available += reservation.quantity
                    
                    # Mark reservation as released
                    reservation.status = ReservationStatus.RELEASED
                    
                    event_publisher.publish_stock_released(
                        sku=reservation.sku,
                        quantity=reservation.quantity,
                        order_id=order_id,
                        reason=f"Payment failed: {reason}",
                        correlation_id=correlation_id
                    )
                    
                    released_count += 1
            
            db.session.commit()
            
            current_app.logger.info(
                f"✅ Released reserved stock for order: {order_id} ({released_count} items)",
                extra={"correlationId": correlation_id}
            )
            
            return {
                "status": "success",
                "message": f"Stock released for order {order_id}",
                "itemsReleased": released_count
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"❌ Error handling payment.failed: {str(e)}",
                extra={"error": str(e), "correlationId": event_data.get('correlationid')}
            )
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def handle_inventory_release(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle inventory.release compensation event from order-processor-service.
        
        This is a CRITICAL saga compensation transaction that prevents inventory leaks.
        Triggered when order saga fails and needs rollback after inventory was reserved.
        
        Scenarios:
        - Payment fails after inventory reserved → Release inventory back to available pool
        - Shipping fails after inventory reserved → Release inventory
        - Order cancelled by admin/user → Release inventory
        
        Event payload structure:
        {
            "data": {
                "orderId": "order-123",
                "reservationId": "res-456"  // Optional - specific reservation to release
            }
        }
        """
        try:
            data = event_data.get('data', {})
            order_id = data.get('orderId')
            reservation_id = data.get('reservationId')
            correlation_id = event_data.get('correlationid') or event_data.get('correlationId')
            
            if not order_id:
                raise ValueError("Missing orderId in compensation event data")
            
            current_app.logger.info(
                f"🔄 SAGA COMPENSATION: Handling inventory.release for order: {order_id}",
                extra={"correlationId": correlation_id, "orderId": order_id, "reservationId": reservation_id}
            )
            
            # Find reservations to release (PENDING or ACTIVE status)
            if reservation_id:
                # Release specific reservation
                reservations = Reservation.query.filter(
                    Reservation.id == reservation_id,
                    Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.ACTIVE])
                ).all()
            else:
                # Release all active reservations for this order
                reservations = Reservation.query.filter(
                    Reservation.order_id == order_id,
                    Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.ACTIVE])
                ).all()
            
            if not reservations:
                current_app.logger.warning(
                    f"⚠️ SAGA COMPENSATION: No active reservations found for order: {order_id}",
                    extra={"correlationId": correlation_id, "orderId": order_id}
                )
                # Return success even if no reservations - idempotent operation
                return {"status": "success", "message": "No active reservations to release"}
            
            released_count = 0
            total_quantity_released = 0
            
            for reservation in reservations:
                # Lock inventory row for update (prevent race conditions)
                inventory = InventoryItem.query.filter_by(
                    sku=reservation.sku
                ).with_for_update().first()
                
                if inventory:
                    # Return reserved quantity back to available pool
                    inventory.quantity_reserved = max(0, inventory.quantity_reserved - reservation.quantity)
                    inventory.quantity_available += reservation.quantity
                    
                    # Mark reservation as released (compensation completed)
                    reservation.status = ReservationStatus.RELEASED
                    
                    # Publish stock.released event for audit/analytics
                    event_publisher.publish_stock_released(
                        sku=reservation.sku,
                        quantity=reservation.quantity,
                        order_id=order_id,
                        reason=f"Saga compensation for order {order_id}",
                        correlation_id=correlation_id
                    )
                    
                    released_count += 1
                    total_quantity_released += reservation.quantity
                    
                    current_app.logger.debug(
                        f"✅ Released reservation: sku={reservation.sku}, qty={reservation.quantity}",
                        extra={"correlationId": correlation_id, "sku": reservation.sku}
                    )
            
            # Commit all changes atomically
            db.session.commit()
            
            current_app.logger.info(
                f"✅ SAGA COMPENSATION COMPLETE: Released inventory for order: {order_id} "
                f"({released_count} reservations, {total_quantity_released} total units)",
                extra={
                    "correlationId": correlation_id,
                    "orderId": order_id,
                    "reservationsReleased": released_count,
                    "totalQuantity": total_quantity_released
                }
            )
            
            return {
                "status": "success",
                "message": f"Compensation completed: Released stock for order {order_id}",
                "reservationsReleased": released_count,
                "totalQuantityReleased": total_quantity_released
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"❌ SAGA COMPENSATION FAILED: Error handling inventory.release: {str(e)}",
                extra={"error": str(e), "correlationId": event_data.get('correlationid'), "orderId": data.get('orderId')}
            )
            # Return error to trigger RETRY - compensation must succeed
            return {"status": "error", "message": str(e)}

    # ============================================================================
    # Return Events
    # ============================================================================
    
    @staticmethod
    def handle_inventory_return_release(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle inventory.return.release event from order-processor-service.
        Add returned items back to available stock.
        
        Event payload structure:
        {
            "data": {
                "returnId": "uuid",
                "orderId": "uuid",
                "returnNumber": "RET-12345",
                "items": [
                    {"sku": "SKU-001", "productName": "iPhone 15", "quantityToReturn": 1},
                    {"sku": "SKU-002", "productName": "Case", "quantityToReturn": 2}
                ]
            }
        }
        """
        try:
            data = event_data.get('data', {})
            return_id = data.get('returnId')
            order_id = data.get('orderId')
            return_number = data.get('returnNumber')
            items = data.get('items', [])
            correlation_id = event_data.get('correlationid') or event_data.get('correlationId')
            
            if not return_id or not order_id or not items:
                raise ValueError("Missing returnId, orderId, or items in event data")
            
            current_app.logger.info(
                f"📦 Handling inventory.return.release for return: {return_number} (order: {order_id})",
                extra={"correlationId": correlation_id, "returnId": return_id, "itemCount": len(items)}
            )
            
            items_returned = 0
            total_quantity_returned = 0
            
            for item in items:
                sku = item.get('sku')
                quantity_to_return = item.get('quantityToReturn', 0)
                product_name = item.get('productName', 'Unknown Product')
                
                if not sku or quantity_to_return <= 0:
                    current_app.logger.warning(
                        f"⚠️ Invalid item in return: sku={sku}",
                        extra={"correlationId": correlation_id}
                    )
                    continue
                
                # Find inventory record (lock for update to prevent race conditions)
                inventory = InventoryItem.query.filter_by(
                    sku=sku
                ).with_for_update().first()
                
                if not inventory:
                    current_app.logger.error(
                        f"❌ InventoryItem not found for SKU: {sku}",
                        extra={"correlationId": correlation_id, "sku": sku}
                    )
                    # Continue with other items even if one fails
                    continue
                
                # Add returned quantity back to available stock
                inventory.quantity_available += quantity_to_return
                
                current_app.logger.info(
                    f"✅ Returned {quantity_to_return} units of {product_name} to stock",
                    extra={
                        "correlationId": correlation_id,
                        "sku": sku,
                        "quantityReturned": quantity_to_return,
                        "newQuantity": inventory.quantity_available
                    }
                )
                
                # Publish stock.updated event for audit/analytics
                event_publisher.publish_stock_updated(
                    sku=sku,
                    quantity=inventory.quantity_available,
                    correlation_id=correlation_id
                )
                
                items_returned += 1
                total_quantity_returned += quantity_to_return
            
            # Commit all changes atomically
            db.session.commit()
            
            current_app.logger.info(
                f"✅ Completed inventory return for: {return_number} "
                f"({items_returned} items, {total_quantity_returned} total units)",
                extra={
                    "correlationId": correlation_id,
                    "returnId": return_id,
                    "itemsReturned": items_returned,
                    "totalQuantity": total_quantity_returned
                }
            )
            
            return {
                "status": "success",
                "message": f"Inventory return completed for {return_number}",
                "itemsReturned": items_returned,
                "totalQuantityReturned": total_quantity_returned
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"❌ Error handling inventory.return.release: {str(e)}",
                extra={"error": str(e), "correlationId": event_data.get('correlationid')}
            )
            return {"status": "error", "message": str(e)}
