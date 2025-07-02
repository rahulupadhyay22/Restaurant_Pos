from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db, socketio, limiter
from app.models.order import Order, OrderItem, OrderStatus, OrderType
from app.models.delivery import DeliveryOrder, DeliveryStatus, DeliveryPlatform
from app.models.menu import MenuItem
from app.models.settings import Settings
from app.utils.decorators import admin_required
from app.services.delivery import ZomatoService, SwiggyService
from datetime import datetime
from app.utils.delivery import verify_signature
from app.utils.delivery_data import standardize_delivery_data, extract_items_data, validate_delivery_data
import json
import logging

logger = logging.getLogger(__name__)

delivery_bp = Blueprint('delivery', __name__, url_prefix='/delivery')


@delivery_bp.route('/')
@login_required
@admin_required
def index():
    """Delivery management route."""
    # Get pending delivery orders
    pending_status_list = [DeliveryStatus.PENDING, DeliveryStatus.ACCEPTED, DeliveryStatus.PREPARING]
    pending_orders = DeliveryOrder.query.filter(
        DeliveryOrder.status.in_(pending_status_list)
    ).order_by(DeliveryOrder.created_at.desc()).all()
    
    # Get completed delivery orders (last 50)
    completed_status_list = [DeliveryStatus.DELIVERED, DeliveryStatus.PICKED_UP]
    completed_orders = DeliveryOrder.query.filter(
        DeliveryOrder.status.in_(completed_status_list)
    ).order_by(DeliveryOrder.updated_at.desc()).limit(50).all()
    
    return render_template('delivery/index.html', pending_orders=pending_orders, completed_orders=completed_orders)


# Update these functions

@delivery_bp.route('/settings')
@login_required
@admin_required
def settings():
    """Delivery settings route."""
    # Load current settings from database
    zomato_api_key = Settings.get('zomato_api_key', '')
    swiggy_api_key = Settings.get('swiggy_api_key', '')
    zomato_enabled = Settings.get('zomato_enabled', 'false')
    swiggy_enabled = Settings.get('swiggy_enabled', 'false')
    zomato_webhook_secret = Settings.get('zomato_webhook_secret', '')
    swiggy_partner_id = Settings.get('swiggy_partner_id', '')
    swiggy_webhook_secret = Settings.get('swiggy_webhook_secret', '')
    base_delivery_fee = Settings.get('base_delivery_fee', '30')
    distance_fee_per_km = Settings.get('distance_fee_per_km', '10')
    max_delivery_radius = Settings.get('max_delivery_radius', '5')
    enable_delivery_radius_check = Settings.get('enable_delivery_radius_check', 'true')
    
    return render_template('delivery/settings.html',
                           zomato_api_key=zomato_api_key,
                           swiggy_api_key=swiggy_api_key,
                           zomato_enabled=zomato_enabled,
                           swiggy_enabled=swiggy_enabled,
                           zomato_webhook_secret=zomato_webhook_secret,
                           swiggy_partner_id=swiggy_partner_id,
                           swiggy_webhook_secret=swiggy_webhook_secret,
                           base_delivery_fee=base_delivery_fee,
                           distance_fee_per_km=distance_fee_per_km,
                           max_delivery_radius=max_delivery_radius,
                           enable_delivery_radius_check=enable_delivery_radius_check)


@delivery_bp.route('/settings/zomato', methods=['POST'])
@login_required
@admin_required
def update_zomato_settings():
    """Update Zomato integration settings."""
    api_key = request.form.get('zomato_api_key')
    webhook_secret = request.form.get('zomato_webhook_secret')
    enabled = 'zomato_enabled' in request.form
    
    # Save settings to database
    Settings.set('zomato_api_key', api_key)
    Settings.set('zomato_webhook_secret', webhook_secret)
    Settings.set('zomato_enabled', 'true' if enabled else 'false')
    
    flash('Zomato integration settings have been updated!', 'success')
    return redirect(url_for('delivery.settings'))


@delivery_bp.route('/settings/swiggy', methods=['POST'])
@login_required
@admin_required
def update_swiggy_settings():
    """Update Swiggy integration settings."""
    api_key = request.form.get('swiggy_api_key')
    partner_id = request.form.get('swiggy_partner_id')
    webhook_secret = request.form.get('swiggy_webhook_secret')
    enabled = 'swiggy_enabled' in request.form
    
    # Save settings to database
    Settings.set('swiggy_api_key', api_key)
    Settings.set('swiggy_partner_id', partner_id)
    Settings.set('swiggy_webhook_secret', webhook_secret)
    Settings.set('swiggy_enabled', 'true' if enabled else 'false')
    
    flash('Swiggy integration settings have been updated!', 'success')
    return redirect(url_for('delivery.settings'))


@delivery_bp.route('/settings/delivery-fees', methods=['POST'])
@login_required
@admin_required
def update_delivery_fees():
    """Update delivery fee settings."""
    base_fee = request.form.get('base_delivery_fee', type=float)
    fee_per_km = request.form.get('distance_fee_per_km', type=float)
    
    # Save settings to database
    Settings.set('base_delivery_fee', str(base_fee))
    Settings.set('distance_fee_per_km', str(fee_per_km))
    
    flash('Delivery fee settings have been updated!', 'success')
    return redirect(url_for('delivery.settings'))


@delivery_bp.route('/settings/delivery-radius', methods=['POST'])
@login_required
@admin_required
def update_delivery_radius():
    """Update delivery radius settings."""
    max_radius = request.form.get('max_delivery_radius', type=float)
    enforce_radius = 'enable_delivery_radius_check' in request.form
    
    # Save settings to database
    Settings.set('max_delivery_radius', str(max_radius))
    Settings.set('enable_delivery_radius_check', 'true' if enforce_radius else 'false')
    
    flash('Delivery radius settings have been updated!', 'success')
    return redirect(url_for('delivery.settings'))


@delivery_bp.route('/order/<int:delivery_id>')
@login_required
@admin_required
def view_order(delivery_id):
    """View delivery order details."""
    delivery_order = DeliveryOrder.query.get_or_404(delivery_id)
    return render_template('delivery/view_order.html', delivery_order=delivery_order)


@delivery_bp.route('/order/<int:delivery_id>/accept', methods=['POST'])
@login_required
@admin_required
def accept_order(delivery_id):
    """Accept a delivery order."""
    delivery_order = DeliveryOrder.query.get_or_404(delivery_id)
    
    if delivery_order.status != DeliveryStatus.PENDING:
        flash('This order is already accepted or cancelled!', 'warning')
        return redirect(url_for('delivery.view_order', delivery_id=delivery_id))
    
    # Create restaurant order if it doesn't exist
    if not delivery_order.order_id:
        # Create new order
        order = Order(
            user_id=current_user.id,
            status=OrderStatus.ACTIVE,
            order_type=OrderType.ZOMATO if delivery_order.platform == DeliveryPlatform.ZOMATO else OrderType.SWIGGY,
            delivery_id=delivery_order.platform_order_id,
            customer_name=delivery_order.customer_name,
            customer_phone=delivery_order.customer_phone,
            customer_address=delivery_order.customer_address
        )
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Add items from delivery order to restaurant order
        if delivery_order.items_data:
            try:
                # Parse the items_data as JSON
                items = json.loads(delivery_order.items_data)
                
                # Process each item
                for item_data in items:
                    # Get item details from standardized format
                    item_name = item_data.get('name', '')
                    
                    # Log the item being processed
                    logger.info(f"Processing delivery item: {item_name}")
                    
                    # Try exact match first
                    menu_item = MenuItem.query.filter(MenuItem.name == item_name).first()
                    
                    # If no exact match, try partial match
                    if not menu_item:
                        menu_item = MenuItem.query.filter(MenuItem.name.ilike(f'%{item_name}%')).first()
                    
                    # If still no match, use the first menu item as fallback
                    if not menu_item:
                        menu_item = MenuItem.query.first()
                        logger.warning(f"No menu item match found for '{item_name}', using fallback item: {menu_item.name if menu_item else 'None'}")
                    
                    if menu_item:
                        # Get quantity and price from standardized data
                        quantity = item_data.get('quantity', 1)
                        price = item_data.get('price', menu_item.full_price)
                        
                        # Create notes with additional details if available
                        notes = f"Delivery item: {item_name}"
                        if item_data.get('notes'):
                            notes += f" | Notes: {item_data['notes']}"
                        if item_data.get('variations') and item_data['variations']:
                            notes += f" | Variations: {', '.join(item_data['variations'])}"
                        
                        # Create order item
                        order_item = OrderItem(
                            order_id=order.id,
                            menu_item_id=menu_item.id,
                            quantity=quantity,
                            price=price,
                            notes=notes
                        )
                        db.session.add(order_item)
                        logger.info(f"Added order item: {quantity}x {menu_item.name} at price {price}")
                    else:
                        logger.error(f"No menu items found in the database")
            except Exception as e:
                # Log the error but continue with order creation
                logger.error(f"Error processing delivery order items: {str(e)}", exc_info=True)
                
                # Try to add at least one item as fallback
                try:
                    # Get the most popular menu item (or first if no better option)
                    menu_item = MenuItem.query.first()
                    if menu_item:
                        order_item = OrderItem(
                            order_id=order.id,
                            menu_item_id=menu_item.id,
                            quantity=1,
                            price=menu_item.full_price,
                            notes=f"Delivery order from {delivery_order.platform.value} (items parsing failed: {str(e)})"
                        )
                        db.session.add(order_item)
                        logger.info(f"Added fallback item {menu_item.name} due to parsing error")
                    else:
                        logger.error("Cannot add fallback item: no menu items found in database")
                except Exception as fallback_error:
                    logger.error(f"Failed to add fallback item: {str(fallback_error)}", exc_info=True)
        else:
            # No items data available, add a fallback item
            logger.warning(f"No items_data available for {delivery_order.platform.value} order {delivery_order.platform_order_id}")
            try:
                # Get the most popular menu item (or first if no better option)
                menu_item = MenuItem.query.first()
                if menu_item:
                    order_item = OrderItem(
                        order_id=order.id,
                        menu_item_id=menu_item.id,
                        quantity=1,
                        price=menu_item.full_price,
                        notes=f"Delivery order from {delivery_order.platform.value} (no items data)"
                    )
                    db.session.add(order_item)
                    logger.info(f"Added fallback item {menu_item.name} due to missing items data")
                else:
                    logger.error("Cannot add fallback item: no menu items found in database")
            except Exception as fallback_error:
                logger.error(f"Failed to add fallback item: {str(fallback_error)}", exc_info=True)
        
        # Link delivery order to restaurant order
        delivery_order.order_id = order.id
    
    # Accept the delivery order
    delivery_order.accept()
    flash('Delivery order has been accepted!', 'success')
    
    # Emit socket event to notify clients
    socketio.emit('delivery_updated', {
        'delivery_id': delivery_order.id, 
        'status': 'accepted',
        'customer_name': delivery_order.customer_name,
        'platform': delivery_order.platform.value
    })
    
    return redirect(url_for('delivery.view_order', delivery_id=delivery_id))


@delivery_bp.route('/order/<int:delivery_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_order(delivery_id):
    """Reject a delivery order."""
    delivery_order = DeliveryOrder.query.get_or_404(delivery_id)
    
    if delivery_order.status != DeliveryStatus.PENDING:
        flash('This order is already accepted or cancelled!', 'warning')
        return redirect(url_for('delivery.view_order', delivery_id=delivery_id))
    
    # Reject the delivery order
    delivery_order.reject()
    flash('Delivery order has been rejected!', 'success')
    
    # Emit socket event to notify clients
    socketio.emit('delivery_updated', {'delivery_id': delivery_order.id, 'status': 'rejected'})
    
    return redirect(url_for('delivery.index'))


@delivery_bp.route('/order/<int:delivery_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_status(delivery_id):
    """Update delivery order status."""
    delivery_order = DeliveryOrder.query.get_or_404(delivery_id)
    
    status = request.form.get('status')
    if not status:
        flash('Please select a status!', 'danger')
        return redirect(url_for('delivery.view_order', delivery_id=delivery_id))
    
    # Update the delivery order status
    delivery_order.update_status(status)
    flash('Delivery order status has been updated!', 'success')
    
    # Emit socket event to notify clients
    socketio.emit('delivery_updated', {'delivery_id': delivery_order.id, 'status': status})
    
    return redirect(url_for('delivery.view_order', delivery_id=delivery_id))


# Update these webhook handlers

@delivery_bp.route('/webhook/zomato', methods=['POST'])
@limiter.limit("10 per minute")
def zomato_webhook():
    """Webhook for Zomato orders."""
    # Verify the request is from Zomato using signature
    signature = request.headers.get('X-Zomato-Signature', '')
    webhook_secret = Settings.get('zomato_webhook_secret', '')
    
    # Verify signature
    if not verify_signature(request.data, signature, webhook_secret):
        logger.warning(f"Invalid Zomato webhook signature: {signature}")
        return jsonify({'error': 'Invalid signature'}), 401
    
    data = request.json
    
    # Standardize and validate the data
    standardized_data = standardize_delivery_data('zomato', data)
    is_valid, error_message = validate_delivery_data(standardized_data)
    
    if not is_valid:
        logger.error(f"Invalid Zomato webhook payload: {error_message}")
        return jsonify({'error': error_message}), 400
    
    # Process the order
    try:
        # Check if order already exists
        existing_order = DeliveryOrder.query.filter_by(
            platform=DeliveryPlatform.ZOMATO,
            platform_order_id=data.get('order_id')
        ).first()
        
        if existing_order:
            logger.warning(f"Duplicate Zomato order received: {data.get('order_id')}")
            return jsonify({
                'success': True, 
                'message': 'Order already exists',
                'order_id': existing_order.id
            }), 200
        
        # Use standardized data to create the delivery order
        delivery_order = DeliveryOrder(
            platform=DeliveryPlatform.ZOMATO,
            platform_order_id=standardized_data['order_id'],
            customer_name=standardized_data['customer']['name'],
            customer_phone=standardized_data['customer']['phone'],
            customer_address=standardized_data['address'],
            delivery_fee=standardized_data['fees']['delivery_fee'],
            platform_fee=standardized_data['fees']['platform_fee']
        )
        
        # Process and store standardized items data
        if standardized_data['items']:
            # Extract and standardize items data
            standardized_items = extract_items_data('zomato', standardized_data['items'])
            # Store items data as proper JSON
            delivery_order.items_data = json.dumps(standardized_items)
            logger.info(f"Stored {len(standardized_items)} standardized items for Zomato order {standardized_data['order_id']}")
        else:
            logger.warning(f"No items found in Zomato order {standardized_data['order_id']}")
        
        db.session.add(delivery_order)
        db.session.commit()
        
        # Log successful order creation
        logger.info(f"Successfully processed Zomato order: {data.get('order_id')}")
        
        # Emit socket event to notify clients
        socketio.emit('new_delivery_order', {
            'delivery_id': delivery_order.id, 
            'platform': 'zomato',
            'customer_name': delivery_order.customer_name,
            'order_time': delivery_order.created_at.strftime('%H:%M:%S')
        })
        
        return jsonify({
            'success': True, 
            'message': 'Order received',
            'order_id': delivery_order.id
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing Zomato webhook: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'message': 'Internal server error',
            'error': str(e)
        }), 500


@delivery_bp.route('/webhook/swiggy', methods=['POST'])
@limiter.limit("10 per minute")
def swiggy_webhook():
    """Webhook for Swiggy orders."""
    # Verify the request is from Swiggy using signature
    signature = request.headers.get('X-Swiggy-Signature', '')
    webhook_secret = Settings.get('swiggy_webhook_secret', '')
    
    # Verify signature
    if not verify_signature(request.data, signature, webhook_secret):
        logger.warning(f"Invalid Swiggy webhook signature: {signature}")
        return jsonify({'error': 'Invalid signature'}), 401
    
    data = request.json
    
    # Standardize and validate the data
    standardized_data = standardize_delivery_data('swiggy', data)
    is_valid, error_message = validate_delivery_data(standardized_data)
    
    if not is_valid:
        logger.error(f"Invalid Swiggy webhook payload: {error_message}")
        return jsonify({'error': error_message}), 400
    
    # Process the order
    try:
        # Check if order already exists
        existing_order = DeliveryOrder.query.filter_by(
            platform=DeliveryPlatform.SWIGGY,
            platform_order_id=data.get('order_id')
        ).first()
        
        if existing_order:
            logger.warning(f"Duplicate Swiggy order received: {data.get('order_id')}")
            return jsonify({
                'success': True, 
                'message': 'Order already exists',
                'order_id': existing_order.id
            }), 200
        
        # Use standardized data to create the delivery order
        delivery_order = DeliveryOrder(
            platform=DeliveryPlatform.SWIGGY,
            platform_order_id=standardized_data['order_id'],
            customer_name=standardized_data['customer']['name'],
            customer_phone=standardized_data['customer']['phone'],
            customer_address=standardized_data['address'],
            delivery_fee=standardized_data['fees']['delivery_fee'],
            platform_fee=standardized_data['fees']['platform_fee']
        )
        
        # Process and store standardized items data
        if standardized_data['items']:
            # Extract and standardize items data
            standardized_items = extract_items_data('swiggy', standardized_data['items'])
            # Store items data as proper JSON
            delivery_order.items_data = json.dumps(standardized_items)
            logger.info(f"Stored {len(standardized_items)} standardized items for Swiggy order {standardized_data['order_id']}")
        else:
            logger.warning(f"No items found in Swiggy order {standardized_data['order_id']}")
        
        db.session.add(delivery_order)
        db.session.commit()
        
        # Log successful order creation
        logger.info(f"Successfully processed Swiggy order: {data.get('order_id')}")
        
        # Emit socket event to notify clients
        socketio.emit('new_delivery_order', {
            'delivery_id': delivery_order.id, 
            'platform': 'swiggy',
            'customer_name': delivery_order.customer_name,
            'order_time': delivery_order.created_at.strftime('%H:%M:%S')
        })
        
        return jsonify({
            'success': True, 
            'message': 'Order received',
            'order_id': delivery_order.id
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing Swiggy webhook: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'message': 'Internal server error',
            'error': str(e)
        }), 500


@delivery_bp.route('/order/<int:delivery_id>/prepare', methods=['POST'])
@login_required
@admin_required
def prepare_order(delivery_id):
    """Mark a delivery order as preparing."""
    delivery_order = DeliveryOrder.query.get_or_404(delivery_id)
    
    if delivery_order.status != DeliveryStatus.ACCEPTED:
        flash('This order cannot be marked as preparing!', 'warning')
        return redirect(url_for('delivery.view_order', delivery_id=delivery_id))
    
    # Update the delivery order status
    delivery_order.status = DeliveryStatus.PREPARING
    delivery_order.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Emit socket event to notify clients
    socketio.emit('delivery_updated', {'delivery_id': delivery_order.id, 'status': 'preparing'})
    
    flash('Order is now being prepared!', 'success')
    return redirect(url_for('delivery.view_order', delivery_id=delivery_id))


@delivery_bp.route('/order/<int:delivery_id>/ready', methods=['POST'])
@login_required
@admin_required
def ready_order(delivery_id):
    """Mark a delivery order as ready for pickup."""
    delivery_order = DeliveryOrder.query.get_or_404(delivery_id)
    
    if delivery_order.status != DeliveryStatus.PREPARING:
        flash('This order cannot be marked as ready!', 'warning')
        return redirect(url_for('delivery.view_order', delivery_id=delivery_id))
    
    # Update the delivery order status
    delivery_order.status = DeliveryStatus.READY
    delivery_order.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Emit socket event to notify clients
    socketio.emit('delivery_updated', {'delivery_id': delivery_order.id, 'status': 'ready'})
    
    flash('Order is now ready for pickup!', 'success')
    return redirect(url_for('delivery.view_order', delivery_id=delivery_id))


@delivery_bp.route('/order/<int:delivery_id>/complete', methods=['POST'])
@login_required
@admin_required
def complete_order(delivery_id):
    """Mark a delivery order as picked up/completed."""
    delivery_order = DeliveryOrder.query.get_or_404(delivery_id)
    
    if delivery_order.status != DeliveryStatus.READY:
        flash('This order cannot be marked as completed!', 'warning')
        return redirect(url_for('delivery.view_order', delivery_id=delivery_id))
    
    # Update the delivery order status
    delivery_order.status = DeliveryStatus.PICKED_UP
    delivery_order.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Emit socket event to notify clients
    socketio.emit('delivery_updated', {'delivery_id': delivery_order.id, 'status': 'picked_up'})
    
    flash('Order has been picked up and completed!', 'success')
    return redirect(url_for('delivery.index'))