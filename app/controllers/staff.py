from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.table import Table
from app.models.menu import Category, MenuItem
from app.models.order import Order, OrderItem, OrderStatus, OrderType
from app.utils.decorators import staff_required
from datetime import datetime

staff_bp = Blueprint('staff', __name__, url_prefix='/staff')


@staff_bp.route('/')
@login_required
def dashboard():
    """Staff dashboard route."""
    tables = Table.query.all()
    return render_template('staff/dashboard.html', tables=tables)


@staff_bp.route('/tables/<int:table_id>')
@login_required
def table_detail(table_id):
    """Staff table detail route."""
    table = Table.query.get_or_404(table_id)
    categories = Category.query.all()
    
    # Get active order for this table, if any
    active_order = Order.query.filter_by(
        table_id=table_id,
        status=OrderStatus.ACTIVE
    ).first()
    
    return render_template('staff/table_detail.html', 
                          table=table, 
                          categories=categories,
                          active_order=active_order)


@staff_bp.route('/orders/create', methods=['POST'])
@login_required
def create_order():
    """Create a new order."""
    data = request.json
    table_id = data.get('table_id')
    items = data.get('items', [])
    
    if not table_id or not items:
        return jsonify({'success': False, 'message': 'Missing required data'}), 400
    
    # Check if table exists
    table = Table.query.get_or_404(table_id)
    
    # Check if table already has an active order
    existing_order = Order.query.filter_by(
        table_id=table_id,
        status=OrderStatus.ACTIVE
    ).first()
    
    if existing_order:
        # Add items to existing order
        order = existing_order
    else:
        # Create new order
        order = Order(
            table_id=table_id,
            user_id=current_user.id,
            status=OrderStatus.ACTIVE,
            order_type=OrderType.DINE_IN
        )
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Mark table as occupied
        table.is_occupied = True
    
    # Add items to order
    for item_data in items:
        menu_item_id = item_data.get('menu_item_id')
        quantity = item_data.get('quantity', 1)
        is_half = item_data.get('is_half', False)
        notes = item_data.get('notes', '')
        
        # Get menu item
        menu_item = MenuItem.query.get_or_404(menu_item_id)
        
        # Determine price
        price = menu_item.half_price if is_half and menu_item.half_price else menu_item.full_price
        
        # Create order item
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item_id,
            quantity=quantity,
            is_half=is_half,
            price=price,
            notes=notes
        )
        db.session.add(order_item)
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Order created successfully',
        'order_id': order.id
    })


@staff_bp.route('/orders/<int:order_id>/add_item', methods=['POST'])
@login_required
def add_order_item(order_id):
    """Add an item to an existing order."""
    data = request.json
    menu_item_id = data.get('menu_item_id')
    quantity = data.get('quantity', 1)
    is_half = data.get('is_half', False)
    notes = data.get('notes', '')
    
    if not menu_item_id:
        return jsonify({'success': False, 'message': 'Missing required data'}), 400
    
    # Check if order exists
    order = Order.query.get_or_404(order_id)
    
    # Check if order is active
    if order.status != OrderStatus.ACTIVE:
        return jsonify({'success': False, 'message': 'Cannot add items to a completed or cancelled order'}), 400
    
    # Get menu item
    menu_item = MenuItem.query.get_or_404(menu_item_id)
    
    # Determine price
    price = menu_item.half_price if is_half and menu_item.half_price else menu_item.full_price
    
    # Create order item
    order_item = OrderItem(
        order_id=order.id,
        menu_item_id=menu_item_id,
        quantity=quantity,
        is_half=is_half,
        price=price,
        notes=notes
    )
    db.session.add(order_item)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Item added to order successfully',
        'order_item_id': order_item.id
    })


@staff_bp.route('/orders/<int:order_id>/remove_item/<int:item_id>', methods=['POST'])
@login_required
def remove_order_item(order_id, item_id):
    """Remove an item from an existing order."""
    # Check if order exists
    order = Order.query.get_or_404(order_id)
    
    # Check if order is active
    if order.status != OrderStatus.ACTIVE:
        return jsonify({'success': False, 'message': 'Cannot remove items from a completed or cancelled order'}), 400
    
    # Check if order item exists
    order_item = OrderItem.query.get_or_404(item_id)
    
    # Check if order item belongs to order
    if order_item.order_id != order.id:
        return jsonify({'success': False, 'message': 'Item does not belong to this order'}), 400
    
    # Remove order item
    db.session.delete(order_item)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Item removed from order successfully'
    }) 