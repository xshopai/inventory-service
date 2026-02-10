"""
Inventory Events Service - Business logic for handling external events
"""

from flask import current_app
from typing import Dict, Any
from datetime import datetime, timedelta
import uuid

from src.database import db
from src.models import InventoryItem, Reservation
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
        Initialize inventory record for the new product.
        """
        try:
            data = event_data.get('data', {})
            product_id = data.get('productId')
            correlation_id = event_data.get('correlationid')
            
            if not product_id:
                raise ValueError("Missing productId in event data")
            
            current_app.logger.info(
                f"📦 Handling product.created for product: {product_id}",
                extra={"correlationId": correlation_id}
            )
            
            # Check if inventory already exists
            existing_inventory = InventoryItem.query.filter_by(product_id=product_id).first()
            if existing_inventory:
                current_app.logger.warning(
                    f"⚠️ InventoryItem already exists for product: {product_id}",
                    extra={"correlationId": correlation_id}
                )
                return {"status": "skipped", "message": "InventoryItem already exists"}
            
            # Create new inventory record with zero initial stock
            new_inventory = InventoryItem(
                product_id=product_id,
                quantity=0,
                reserved_quantity=0,
                warehouse="default",
                low_stock_threshold=10
            )
            
            db.session.add(new_inventory)
            db.session.commit()
            
            current_app.logger.info(
                f"✅ Created inventory for product: {product_id}",
                extra={"correlationId": correlation_id}
            )
            
            # Publish inventory.created event
            event_publisher.publish_inventory_created(
                product_id=product_id,
                initial_quantity=0,
                correlation_id=correlation_id
            )
            
            return {
                "status": "success",
                "message": f"InventoryItem created for product {product_id}"
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
        """
        try:
            data = event_data.get('data', {})
            product_id = data.get('productId')
            correlation_id = event_data.get('correlationid')
            
            if not product_id:
                raise ValueError("Missing productId in event data")
            
            current_app.logger.info(
                f"📝 Handling product.updated for product: {product_id}",
                extra={"correlationId": correlation_id}
            )
            
            # Find inventory record
            inventory = InventoryItem.query.filter_by(product_id=product_id).first()
            if not inventory:
                current_app.logger.warning(
                    f"⚠️ InventoryItem not found for product: {product_id}",
                    extra={"correlationId": correlation_id}
                )
                return {"status": "not_found", "message": "InventoryItem not found"}
            
            db.session.commit()
            
            current_app.logger.info(
                f"✅ Updated inventory metadata for product: {product_id}",
                extra={"correlationId": correlation_id}
            )
            
            return {
                "status": "success",
                "message": f"InventoryItem updated for product {product_id}"
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"❌ Error handling product.updated: {str(e)}",
                extra={"error": str(e), "correlationId": event_data.get('correlationid')}
            )
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def handle_product_deleted(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle product.deleted event from product-service.
        Archive inventory record.
        """
        try:
            data = event_data.get('data', {})
            product_id = data.get('productId')
            correlation_id = event_data.get('correlationid')
            
            if not product_id:
                raise ValueError("Missing productId in event data")
            
            current_app.logger.info(
                f"🗑️ Handling product.deleted for product: {product_id}",
                extra={"correlationId": correlation_id}
            )
            
            # Find inventory record
            inventory = InventoryItem.query.filter_by(product_id=product_id).first()
            if not inventory:
                current_app.logger.warning(
                    f"⚠️ InventoryItem not found for product: {product_id}",
                    extra={"correlationId": correlation_id}
                )
                return {"status": "not_found", "message": "InventoryItem not found"}
            
            # Soft delete (preserve history)
            inventory.is_active = False
            db.session.commit()
            
            current_app.logger.info(
                f"✅ Archived inventory for deleted product: {product_id}",
                extra={"correlationId": correlation_id}
            )
            
            return {
                "status": "success",
                "message": f"InventoryItem archived for product {product_id}"
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
        """
        try:
            data = event_data.get('data', {})
            order_id = data.get('orderId')
            items = data.get('items', [])
            correlation_id = event_data.get('correlationid')
            
            if not order_id or not items:
                raise ValueError("Missing orderId or items in event data")
            
            current_app.logger.info(
                f"📦 Handling order.created for order: {order_id}",
                extra={"correlationId": correlation_id, "itemCount": len(items)}
            )
            
            reservations_created = []
            
            for item in items:
                product_id = item.get('productId')
                quantity = item.get('quantity', 0)
                
                if not product_id or quantity <= 0:
                    current_app.logger.warning(
                        f"⚠️ Invalid item in order: {product_id}",
                        extra={"correlationId": correlation_id}
                    )
                    continue
                
                # Find inventory
                inventory = InventoryItem.query.filter_by(
                    product_id=product_id,
                    is_active=True
                ).with_for_update().first()
                
                if not inventory:
                    current_app.logger.error(
                        f"❌ InventoryItem not found for product: {product_id}",
                        extra={"correlationId": correlation_id}
                    )
                    db.session.rollback()
                    return {
                        "status": "error",
                        "message": f"InventoryItem not found for product {product_id}"
                    }
                
                # Check available stock
                available = inventory.quantity - inventory.reserved_quantity
                if available < quantity:
                    current_app.logger.error(
                        f"❌ Insufficient stock for product: {product_id} "
                        f"(available: {available}, requested: {quantity})",
                        extra={"correlationId": correlation_id}
                    )
                    db.session.rollback()
                    return {
                        "status": "error",
                        "message": f"Insufficient stock for product {product_id}"
                    }
                
                # Create reservation
                reservation_id = str(uuid.uuid4())
                reservation = Reservation(
                    id=reservation_id,
                    product_id=product_id,
                    order_id=order_id,
                    quantity=quantity,
                    status='reserved',
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
                )
                
                inventory.reserved_quantity += quantity
                
                db.session.add(reservation)
                reservations_created.append({
                    "reservationId": reservation_id,
                    "productId": product_id,
                    "quantity": quantity
                })
                
                # Publish stock.reserved event
                event_publisher.publish_stock_reserved(
                    product_id=product_id,
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
        """
        try:
            data = event_data.get('data', {})
            order_id = data.get('orderId')
            reason = data.get('reason', 'Order cancelled')
            correlation_id = event_data.get('correlationid')
            
            if not order_id:
                raise ValueError("Missing orderId in event data")
            
            current_app.logger.info(
                f"🔄 Handling order.cancelled for order: {order_id}",
                extra={"correlationId": correlation_id}
            )
            
            # Find all reservations for this order
            reservations = Reservation.query.filter_by(
                order_id=order_id,
                status='reserved'
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
                    product_id=reservation.product_id
                ).with_for_update().first()
                
                if inventory:
                    inventory.reserved_quantity = max(0, inventory.reserved_quantity - reservation.quantity)
                    reservation.status = 'released'
                    reservation.released_at = datetime.utcnow()
                    
                    event_publisher.publish_stock_released(
                        product_id=reservation.product_id,
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
        Deduct reserved stock permanently.
        """
        try:
            data = event_data.get('data', {})
            order_id = data.get('orderId')
            correlation_id = event_data.get('correlationid')
            
            if not order_id:
                raise ValueError("Missing orderId in event data")
            
            current_app.logger.info(
                f"✅ Handling order.completed for order: {order_id}",
                extra={"correlationId": correlation_id}
            )
            
            reservations = Reservation.query.filter_by(
                order_id=order_id,
                status='reserved'
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
                    product_id=reservation.product_id
                ).with_for_update().first()
                
                if inventory:
                    inventory.quantity = max(0, inventory.quantity - reservation.quantity)
                    inventory.reserved_quantity = max(0, inventory.reserved_quantity - reservation.quantity)
                    
                    reservation.status = 'completed'
                    reservation.completed_at = datetime.now(timezone.utc)
                    
                    event_publisher.publish_stock_updated(
                        product_id=reservation.product_id,
                        quantity=inventory.quantity,
                        correlation_id=correlation_id
                    )
                    
                    # Check for low stock
                    if inventory.quantity <= inventory.low_stock_threshold:
                        if inventory.quantity == 0:
                            event_publisher.publish_out_of_stock_alert(
                                product_id=reservation.product_id,
                                correlation_id=correlation_id
                            )
                        else:
                            event_publisher.publish_low_stock_alert(
                                product_id=reservation.product_id,
                                current_quantity=inventory.quantity,
                                threshold=inventory.low_stock_threshold,
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
        """
        try:
            data = event_data.get('data', {})
            order_id = data.get('orderId')
            payment_id = data.get('paymentId')
            correlation_id = event_data.get('correlationid')
            
            if not order_id:
                raise ValueError("Missing orderId in event data")
            
            current_app.logger.info(
                f"💳 Handling payment.received for order: {order_id}",
                extra={"correlationId": correlation_id, "paymentId": payment_id}
            )
            
            # Find all reservations for this order
            reservations = Reservation.query.filter_by(
                order_id=order_id,
                status='reserved'
            ).all()
            
            if not reservations:
                current_app.logger.warning(
                    f"⚠️ No active reservations found for order: {order_id}",
                    extra={"correlationId": correlation_id}
                )
                return {"status": "not_found", "message": "No reservations found"}
            
            confirmed_count = 0
            
            for reservation in reservations:
                reservation.status = 'confirmed'
                reservation.confirmed_at = datetime.utcnow()
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
        """
        try:
            data = event_data.get('data', {})
            order_id = data.get('orderId')
            reason = data.get('reason', 'Payment failed')
            correlation_id = event_data.get('correlationid')
            
            if not order_id:
                raise ValueError("Missing orderId in event data")
            
            current_app.logger.info(
                f"❌ Handling payment.failed for order: {order_id}",
                extra={"correlationId": correlation_id, "reason": reason}
            )
            
            # Find all reservations for this order
            reservations = Reservation.query.filter_by(
                order_id=order_id,
                status='reserved'
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
                    product_id=reservation.product_id
                ).with_for_update().first()
                
                if inventory:
                    inventory.reserved_quantity = max(0, inventory.reserved_quantity - reservation.quantity)
                    reservation.status = 'released'
                    reservation.released_at = datetime.utcnow()
                    
                    event_publisher.publish_stock_released(
                        product_id=reservation.product_id,
                        quantity=reservation.quantity,
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
