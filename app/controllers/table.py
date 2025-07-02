from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.table import Table
from app.utils.decorators import admin_required
from app.forms.table import TableForm

table_bp = Blueprint('table', __name__, url_prefix='/tables')


@table_bp.route('/')
@login_required
@admin_required
def index():
    """Table management route."""
    tables = Table.query.all()
    return render_template('table/index.html', tables=tables)


@table_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_table():
    """Add a new table."""
    form = TableForm()
    if form.validate_on_submit():
        table = Table(
            name=form.name.data,
            capacity=form.capacity.data
        )
        db.session.add(table)
        db.session.commit()
        flash(f'Table "{table.name}" has been added!', 'success')
        return redirect(url_for('table.index'))
    
    return render_template('table/add_table.html', form=form)


@table_bp.route('/<int:table_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_table(table_id):
    """Edit an existing table."""
    table = Table.query.get_or_404(table_id)
    form = TableForm(obj=table)
    
    if form.validate_on_submit():
        table.name = form.name.data
        table.capacity = form.capacity.data
        db.session.commit()
        flash(f'Table "{table.name}" has been updated!', 'success')
        return redirect(url_for('table.index'))
    
    return render_template('table/edit_table.html', form=form, table=table)


@table_bp.route('/<int:table_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_table(table_id):
    """Delete a table."""
    table = Table.query.get_or_404(table_id)
    
    # Check if table is occupied
    if table.is_occupied:
        flash(f'Cannot delete table "{table.name}" because it is currently occupied!', 'danger')
        return redirect(url_for('table.index'))
    
    # Check if table has orders
    if table.orders.count() > 0:
        flash(f'Cannot delete table "{table.name}" because it has orders associated with it!', 'danger')
        return redirect(url_for('table.index'))
    
    db.session.delete(table)
    db.session.commit()
    flash(f'Table "{table.name}" has been deleted!', 'success')
    return redirect(url_for('table.index'))


@table_bp.route('/api/status', methods=['GET'])
@login_required
def api_table_status():
    """API endpoint for table statuses."""
    tables = Table.query.all()
    return jsonify({
        'tables': [{
            'id': table.id,
            'name': table.name,
            'capacity': table.capacity,
            'is_occupied': table.is_occupied,
            'status': table.status
        } for table in tables]
    }) 