from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from app import db
from app.models.order import Order, OrderStatus
from app.models.bill import Bill, PaymentMethod
from app.models.settings import Settings
from app.utils.decorators import admin_required
from datetime import datetime
import os
import io
import csv

# Make pdfkit optional but provide fallback options
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
    
    # Configuration for wkhtmltopdf
    import platform
    
    if platform.system() == 'Windows':
        # Common installation paths on Windows
        possible_paths = [
            r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
            r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe'
        ]
        
        # Use the first path that exists
        for path in possible_paths:
            if os.path.exists(path):
                pdfkit_config = pdfkit.configuration(wkhtmltopdf=path)
                break
        else:
            # If no path exists, set flag to False
            print('Warning: wkhtmltopdf executable not found. PDF generation will not work.')
            PDFKIT_AVAILABLE = False
            pdfkit_config = None
    else:
        # On Linux/Mac, it might be in the PATH
        pdfkit_config = pdfkit.configuration()
except ImportError:
    PDFKIT_AVAILABLE = False
    pdfkit_config = None

# Make xlsxwriter optional
try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')


@billing_bp.route('/')
@login_required
@admin_required
def index():
    """Billing management route."""
    # Get recent bills (last 50)
    recent_bills = Bill.query.order_by(Bill.created_at.desc()).limit(50).all()
    return render_template('billing/index.html', recent_bills=recent_bills)


@billing_bp.route('/generate/<int:order_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def generate_bill(order_id):
    """Generate a bill for an order."""
    order = Order.query.get_or_404(order_id)
    
    # Check if order is active
    if order.status != OrderStatus.ACTIVE:
        flash('Cannot generate bill for a completed or cancelled order!', 'warning')
        return redirect(url_for('order.view_order', order_id=order_id))
    
    # Check if bill already exists
    existing_bill = Bill.query.filter_by(order_id=order_id).first()
    if existing_bill:
        return redirect(url_for('billing.view_bill', bill_id=existing_bill.id))
    
    # Get tax rate from settings
    tax_rate_str = Settings.get('tax_rate', '5')
    try:
        tax_rate = float(tax_rate_str) / 100.0
    except ValueError:
        tax_rate = 0.05  # Default to 5% if the value is not a valid number
    
    if request.method == 'POST':
        # Calculate bill amounts
        subtotal = order.total_amount
        tax_amount = subtotal * tax_rate
        discount = float(request.form.get('discount', 0))
        total_amount = subtotal + tax_amount - discount
        
        # Generate bill
        bill = Bill(
            order_id=order_id,
            bill_number=Bill.generate_bill_number(),
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount=discount,
            total_amount=total_amount
        )
        db.session.add(bill)
        
        # Mark order as completed
        order.complete()
        
        db.session.commit()
        flash('Bill has been generated successfully!', 'success')
        return redirect(url_for('billing.view_bill', bill_id=bill.id))
    
    # For GET request, calculate tax amount based on settings
    subtotal = order.total_amount
    tax_amount = subtotal * tax_rate
    total_amount = subtotal + tax_amount
    
    return render_template('billing/generate_bill.html', 
                         order=order,
                         tax_rate=tax_rate * 100,  # Convert to percentage for display
                         tax_amount=tax_amount,
                         total_amount=total_amount)


@billing_bp.route('/view/<int:bill_id>')
@login_required
def view_bill(bill_id):
    """View bill details."""
    bill = Bill.query.get_or_404(bill_id)
    return render_template('billing/view_bill.html', bill=bill)


@billing_bp.route('/pay/<int:bill_id>', methods=['POST'])
@login_required
@admin_required
def pay_bill(bill_id):
    """Mark a bill as paid."""
    bill = Bill.query.get_or_404(bill_id)
    
    if bill.payment_status:
        flash('This bill is already paid!', 'warning')
        return redirect(url_for('billing.view_bill', bill_id=bill_id))
    
    payment_method = request.form.get('payment_method')
    if not payment_method:
        flash('Please select a payment method!', 'danger')
        return redirect(url_for('billing.view_bill', bill_id=bill_id))
    
    bill.mark_as_paid(payment_method)
    flash('Bill has been marked as paid!', 'success')
    return redirect(url_for('billing.view_bill', bill_id=bill_id))


@billing_bp.route('/print/<int:bill_id>')
@login_required
def print_bill(bill_id):
    """Print a bill."""
    bill = Bill.query.get_or_404(bill_id)
    
    # Return HTML by default - most browsers can print HTML directly
    # and this avoids the need for wkhtmltopdf
    return render_template('billing/print_bill.html', 
                         bill=bill, 
                         Settings=Settings,
                         print_mode=True,
                         standalone=True)


@billing_bp.route('/export/pdf')
@login_required
@admin_required
def export_pdf():
    """Export bills as PDF."""
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Build query
    query = Bill.query
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Bill.created_at >= start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Bill.created_at <= end_date)
        except ValueError:
            pass
    
    # Get bills
    bills = query.order_by(Bill.created_at.desc()).all()
    
    # Return the HTML report directly - browsers can print/save as PDF
    return render_template('billing/export_pdf.html', 
                         bills=bills, 
                         start_date=start_date, 
                         end_date=end_date,
                         now=datetime.now,
                         Settings=Settings,
                         standalone=True,
                         print_friendly=True)


@billing_bp.route('/export/excel')
@login_required
@admin_required
def export_excel():
    """Export bills as Excel."""
    if not XLSXWRITER_AVAILABLE:
        flash('Excel export is not available. Please install xlsxwriter.', 'warning')
        return redirect(url_for('billing.index'))
    
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Build query
    query = Bill.query
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Bill.created_at >= start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Bill.created_at <= end_date)
        except ValueError:
            pass
    
    # Get bills
    bills = query.order_by(Bill.created_at.desc()).all()
    
    # Create an in-memory output file
    output = io.BytesIO()
    
    # Create a workbook and add a worksheet
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('Bills')
    
    # Add headers
    headers = ['Bill #', 'Date', 'Customer', 'Subtotal', 'Tax', 'Discount', 'Total', 'Payment Status', 'Payment Method']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)
    
    # Add data
    for row, bill in enumerate(bills, 1):
        worksheet.write(row, 0, bill.bill_number)
        worksheet.write(row, 1, bill.created_at.strftime('%Y-%m-%d %H:%M'))
        worksheet.write(row, 2, bill.order.customer_name if bill.order.customer_name else 'Walk-in Customer')
        worksheet.write(row, 3, bill.subtotal)
        worksheet.write(row, 4, bill.tax_amount)
        worksheet.write(row, 5, bill.discount)
        worksheet.write(row, 6, bill.total_amount)
        worksheet.write(row, 7, 'Paid' if bill.payment_status else 'Unpaid')
        worksheet.write(row, 8, bill.payment_method.value if bill.payment_method else '')
    
    # Close the workbook
    workbook.close()
    
    # Seek to the beginning of the stream
    output.seek(0)
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=bills_report.xlsx'
    
    return response


@billing_bp.route('/export/csv')
@login_required
@admin_required
def export_csv():
    """Export bills as CSV."""
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Build query
    query = Bill.query
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Bill.created_at >= start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Bill.created_at <= end_date)
        except ValueError:
            pass
    
    # Get bills
    bills = query.order_by(Bill.created_at.desc()).all()
    
    # Create an in-memory output file
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    headers = ['Bill #', 'Date', 'Customer', 'Subtotal', 'Tax', 'Discount', 'Total', 'Payment Status', 'Payment Method']
    writer.writerow(headers)
    
    # Write data
    for bill in bills:
        writer.writerow([
            bill.bill_number,
            bill.created_at.strftime('%Y-%m-%d %H:%M'),
            bill.order.customer_name if bill.order.customer_name else 'Walk-in Customer',
            bill.subtotal,
            bill.tax_amount,
            bill.discount,
            bill.total_amount,
            'Paid' if bill.payment_status else 'Unpaid',
            bill.payment_method.value if bill.payment_method else ''
        ])
    
    # Create response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=bills_report.csv'
    
    return response 