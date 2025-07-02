from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db, socketio
from app.models.order import Order, OrderItem, OrderStatus, OrderType
from app.models.table import Table
from app.models.menu import MenuItem
from app.utils.decorators import admin_required
from datetime import datetime

order_bp = Blueprint('order', __name__, url_prefix='/orders')


@order_bp.route('/')
@login_required
def index():
    """Order management route."""
    # Get active orders
    active_orders = Order.query.filter_by(status=OrderStatus.ACTIVE).order_by(Order.created_at.desc()).all()
    
    # Get completed orders (last 50)
    completed_orders = Order.query.filter_by(status=OrderStatus.COMPLETED).order_by(Order.completed_at.desc()).limit(50).all()
    
    return render_template('order/index.html', active_orders=active_orders, completed_orders=completed_orders)


@order_bp.route('/<int:order_id>')
@login_required
def view_order(order_id):
    """View order details."""
    order = Order.query.get_or_404(order_id)
    return render_template('order/view_order.html', order=order)


@order_bp.route('/<int:order_id>/complete', methods=['POST'])
@login_required
def complete_order(order_id):
    """Mark an order as completed."""
    order = Order.query.get_or_404(order_id)
    
    if order.status != OrderStatus.ACTIVE:
        flash('This order is already completed or cancelled!', 'warning')
        return redirect(url_for('order.view_order', order_id=order_id))
    
    order.complete()
    flash('Order has been marked as completed!', 'success')
    
    # Emit socket event to notify clients
    socketio.emit('order_updated', {'order_id': order.id, 'status': 'completed'})
    
    return redirect(url_for('order.view_order', order_id=order_id))


@order_bp.route('/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Cancel an order."""
    order = Order.query.get_or_404(order_id)
    
    if order.status != OrderStatus.ACTIVE:
        flash('This order is already completed or cancelled!', 'warning')
        return redirect(url_for('order.view_order', order_id=order_id))
    
    order.cancel()
    flash('Order has been cancelled!', 'success')
    
    # Emit socket event to notify clients
    socketio.emit('order_updated', {'order_id': order.id, 'status': 'cancelled'})
    
    return redirect(url_for('order.view_order', order_id=order_id))


@order_bp.route('/api/active')
@login_required
def api_active_orders():
    """API endpoint for active orders."""
    active_orders = Order.query.filter_by(status=OrderStatus.ACTIVE).all()
    
    orders_data = []
    for order in active_orders:
        order_data = {
            'id': order.id,
            'table_name': order.table.name if order.table else 'Delivery',
            'order_type': order.order_type.value,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'items_count': order.items.count(),
            'total_amount': order.total_amount,
            'items': []
        }
        
        for item in order.items:
            item_data = {
                'id': item.id,
                'name': item.menu_item.name,
                'quantity': item.quantity,
                'is_half': item.is_half,
                'price': item.price,
                'subtotal': item.subtotal,
                'notes': item.notes
            }
            order_data['items'].append(item_data)
        
        orders_data.append(order_data)
    
    return jsonify({'orders': orders_data})


@socketio.on('connect')
def handle_connect():
    """Handle socket connection."""
    print(f'Client connected: {request.sid}')


@socketio.on('disconnect')
def handle_disconnect():
    """Handle socket disconnection."""
    print(f'Client disconnected: {request.sid}') 