from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.menu import Category, MenuItem
from app.utils.decorators import admin_required
from app.forms.menu import CategoryForm, MenuItemForm

menu_bp = Blueprint('menu', __name__, url_prefix='/menu')


@menu_bp.route('/')
@login_required
def index():
    """Menu index route."""
    categories = Category.query.all()
    menu_items = MenuItem.query.all()
    return render_template('menu/index.html', categories=categories, menu_items=menu_items)


@menu_bp.route('/categories')
@login_required
@admin_required
def categories():
    """Menu categories management route."""
    categories = Category.query.all()
    return render_template('menu/categories.html', categories=categories)


@menu_bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_category():
    """Add a new category."""
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(category)
        db.session.commit()
        flash(f'Category "{category.name}" has been added!', 'success')
        return redirect(url_for('menu.categories'))
    
    return render_template('menu/add_category.html', form=form)


@menu_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    """Edit an existing category."""
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        db.session.commit()
        flash(f'Category "{category.name}" has been updated!', 'success')
        return redirect(url_for('menu.categories'))
    
    return render_template('menu/edit_category.html', form=form, category=category)


@menu_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    """Delete a category."""
    category = Category.query.get_or_404(category_id)
    
    # Check if category has menu items
    if category.menu_items.count() > 0:
        flash(f'Cannot delete category "{category.name}" because it has menu items!', 'danger')
        return redirect(url_for('menu.categories'))
    
    db.session.delete(category)
    db.session.commit()
    flash(f'Category "{category.name}" has been deleted!', 'success')
    return redirect(url_for('menu.categories'))


@menu_bp.route('/items')
@login_required
@admin_required
def items():
    """Menu items management route."""
    menu_items = MenuItem.query.all()
    return render_template('menu/items.html', menu_items=menu_items)


@menu_bp.route('/items/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_item():
    """Add a new menu item."""
    form = MenuItemForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    
    if form.validate_on_submit():
        menu_item = MenuItem(
            name=form.name.data,
            description=form.description.data,
            half_price=form.half_price.data,
            full_price=form.full_price.data,
            category_id=form.category_id.data,
            is_available=form.is_available.data,
            image_url=form.image_url.data
        )
        db.session.add(menu_item)
        db.session.commit()
        flash(f'Menu item "{menu_item.name}" has been added!', 'success')
        return redirect(url_for('menu.items'))
    
    return render_template('menu/add_item.html', form=form)


@menu_bp.route('/items/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_item(item_id):
    """Edit an existing menu item."""
    menu_item = MenuItem.query.get_or_404(item_id)
    form = MenuItemForm(obj=menu_item)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    form.has_half_option.data = menu_item.has_half_option
    
    if form.validate_on_submit():
        menu_item.name = form.name.data
        menu_item.description = form.description.data
        menu_item.half_price = form.half_price.data
        menu_item.full_price = form.full_price.data
        menu_item.category_id = form.category_id.data
        menu_item.is_available = form.is_available.data
        menu_item.image_url = form.image_url.data
        db.session.commit()
        flash(f'Menu item "{menu_item.name}" has been updated!', 'success')
        return redirect(url_for('menu.items'))
    
    return render_template('menu/edit_item.html', form=form, menu_item=menu_item)


@menu_bp.route('/items/<int:item_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_item(item_id):
    """Delete a menu item."""
    menu_item = MenuItem.query.get_or_404(item_id)
    
    # Check if menu item is used in orders
    if menu_item.order_items.count() > 0:
        flash(f'Cannot delete menu item "{menu_item.name}" because it is used in orders!', 'danger')
        return redirect(url_for('menu.items'))
    
    db.session.delete(menu_item)
    db.session.commit()
    flash(f'Menu item "{menu_item.name}" has been deleted!', 'success')
    return redirect(url_for('menu.items'))


@menu_bp.route('/api/items', methods=['GET'])
@login_required
def api_items():
    """API endpoint for menu items."""
    category_id = request.args.get('category_id', type=int)
    
    query = MenuItem.query.filter_by(is_available=True)
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    items = query.all()
    
    return jsonify({
        'items': [{
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'half_price': item.half_price,
            'full_price': item.full_price,
            'has_half_option': item.has_half_option,
            'category_id': item.category_id,
            'image_url': item.image_url
        } for item in items]
    }) 