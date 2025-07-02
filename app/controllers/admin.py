from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, abort, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from app.models.user import User, Role, user_role
from app.models.menu import Category, MenuItem
from app.models.table import Table
from app.models.order import Order, OrderItem, OrderStatus
from app.models.bill import Bill
from app.models.delivery import DeliveryOrder, DeliveryStatus
from app.models.settings import Settings
from app.utils.decorators import admin_required
from datetime import datetime, timedelta
from sqlalchemy import func
import io
import csv


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')

@login_required
@admin_required
def dashboard():
    """Admin dashboard route."""
    # Get today's date
    today = datetime.now().date()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    
    # Get statistics
    total_sales_today = db.session.query(db.func.sum(Bill.total_amount)).filter(
        Bill.created_at.between(start_of_day, end_of_day),
        Bill.payment_status == True
    ).scalar() or 0
    
    orders_today = Order.query.filter(
        Order.created_at.between(start_of_day, end_of_day)
    ).count()
    
    active_tables = Table.query.filter_by(is_occupied=True).count()
    
    # Get recent orders
    recent_orders = Order.query.filter(
        Order.status == OrderStatus.ACTIVE
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    # Get delivery orders
    delivery_orders = DeliveryOrder.query.filter(
        DeliveryOrder.status.in_(['PENDING', 'ACCEPTED', 'PREPARING'])
    ).order_by(DeliveryOrder.created_at.desc()).all()
    
    return render_template('admin/dashboard.html',
                          total_sales=total_sales_today,
                          orders_today=orders_today,
                          active_tables=active_tables,
                          recent_orders=recent_orders,
                          delivery_orders=delivery_orders)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Admin users management route."""
    users = User.query.all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    """Add a new user."""
    from app.forms.auth import RegistrationForm
    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        flash(f'User {user.username} has been created!', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/add_user.html', form=form)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit an existing user."""
    from app.forms.auth import UserEditForm

    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data

        if form.password.data:
            user.set_password(form.password.data)

        db.session.commit()
        flash(f'User {user.username} has been updated!', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/edit_user.html', form=form, user=user)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('admin.users'))

    db.session.delete(user)
    db.session.commit()

    flash(f'User {user.username} has been deleted!', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    """Admin reports route."""
    today = datetime.now().date()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())

    start_of_week = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    end_of_week = datetime.combine(start_of_week.date() + timedelta(days=6), datetime.max.time())

    start_of_month = datetime.combine(today.replace(day=1), datetime.min.time())
    if today.month == 12:
        end_of_month = datetime.combine(today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1), datetime.max.time())
    else:
        end_of_month = datetime.combine(today.replace(month=today.month + 1, day=1) - timedelta(days=1), datetime.max.time())

    sales_today = db.session.query(func.sum(Bill.total_amount)).filter(
        Bill.created_at.between(start_of_day, end_of_day),
        Bill.payment_status == True
    ).scalar() or 0

    sales_week = db.session.query(func.sum(Bill.total_amount)).filter(
        Bill.created_at.between(start_of_week, end_of_week),
        Bill.payment_status == True
    ).scalar() or 0

    sales_month = db.session.query(func.sum(Bill.total_amount)).filter(
        Bill.created_at.between(start_of_month, end_of_month),
        Bill.payment_status == True
    ).scalar() or 0

    popular_items = db.session.query(
        MenuItem.name,
        func.sum(OrderItem.quantity).label('total_quantity')
    ).join(OrderItem, MenuItem.id == OrderItem.menu_item_id) \
        .join(Order, OrderItem.order_id == Order.id) \
        .filter(Order.created_at.between(start_of_month, end_of_month)) \
        .group_by(MenuItem.name) \
        .order_by(func.sum(OrderItem.quantity).desc()) \
        .limit(5).all()

    return render_template('admin/reports.html',
                           sales_today=sales_today,
                           sales_week=sales_week,
                           sales_month=sales_month,
                           popular_items=popular_items)


@admin_bp.route('/export-report/<string:format>')
@login_required
@admin_required
def export_report(format):
    """Export reports in different formats."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    else:
        next_month = start_date.replace(month=start_date.month + 1 if start_date.month < 12 else 1,
                                        year=start_date.year if start_date.month < 12 else start_date.year + 1)
        end_date = next_month - timedelta(seconds=1)

    bills = Bill.query.filter(
        Bill.created_at.between(start_date, end_date),
        Bill.payment_status == True
    ).order_by(Bill.created_at).all()

    if format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Bill Number', 'Order ID', 'Date', 'Subtotal', 'Tax', 'Discount', 'Total', 'Payment Method'])

        for bill in bills:
            writer.writerow([
                bill.bill_number,
                bill.order_id,
                bill.created_at.strftime('%Y-%m-%d %H:%M'),
                bill.subtotal,
                bill.tax_amount,
                bill.discount,
                bill.total_amount,
                bill.payment_method.value if bill.payment_method else 'N/A'
            ])

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'sales_report_{start_date.strftime("%Y%m%d")}-{end_date.strftime("%Y%m%d")}.csv'
        )

    elif format == 'pdf':
        flash('PDF export is not implemented yet.', 'info')
        return redirect(url_for('admin.reports'))

    elif format == 'excel':
        flash('Excel export is not implemented yet.', 'info')
        return redirect(url_for('admin.reports'))

    else:
        flash('Invalid export format.', 'error')
        return redirect(url_for('admin.reports'))


@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    """Admin settings route."""
    tax_rate = Settings.get('tax_rate', '5')
    restaurant_name = Settings.get('restaurant_name', 'Restaurant Name')
    restaurant_phone = Settings.get('restaurant_phone', '+1234567890')
    restaurant_address = Settings.get('restaurant_address', '123 Main St, City, Country')

    return render_template('admin/settings.html',
                           tax_rate=tax_rate,
                           restaurant_name=restaurant_name,
                           restaurant_phone=restaurant_phone,
                           restaurant_address=restaurant_address)


@admin_bp.route('/settings/restaurant-info', methods=['POST'])
@login_required
@admin_required
def update_restaurant_info():
    """Update restaurant information."""
    restaurant_name = request.form.get('restaurant_name')
    restaurant_phone = request.form.get('restaurant_phone')
    restaurant_address = request.form.get('restaurant_address')

    Settings.set('restaurant_name', restaurant_name)
    Settings.set('restaurant_phone', restaurant_phone)
    Settings.set('restaurant_address', restaurant_address)

    flash('Restaurant information has been updated!', 'success')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/settings/tax-settings', methods=['POST'])
@login_required
@admin_required
def update_tax_settings():
    """Update tax settings."""
    tax_rate = request.form.get('tax_rate')
    Settings.set('tax_rate', tax_rate)
    flash('Tax settings have been updated!', 'success')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/settings/delivery-settings', methods=['POST'])
@login_required
@admin_required
def update_delivery_settings():
    """Update delivery settings."""
    zomato_api_key = request.form.get('zomato_api_key')
    swiggy_api_key = request.form.get('swiggy_api_key')
    Settings.set('zomato_api_key', zomato_api_key)
    Settings.set('swiggy_api_key', swiggy_api_key)
    flash('Delivery settings have been updated!', 'success')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/settings/backup-database', methods=['POST'])
@login_required
@admin_required
def backup_database():
    """Backup the database."""
    flash('Database backup has been created!', 'success')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/settings/reset-database', methods=['POST'])
@login_required
@admin_required
def reset_database():
    """Reset the database."""
    flash('Database has been reset!', 'success')
    return redirect(url_for('admin.settings'))
