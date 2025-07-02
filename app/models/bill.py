from app import db
from datetime import datetime
import enum

class PaymentMethod(enum.Enum):
    """Enum for payment methods."""
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    UPI = "upi"
    ONLINE = "online"


class Bill(db.Model):
    """Bill model for restaurant bills."""
    __tablename__ = 'bills'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), unique=True, nullable=False)
    bill_number = db.Column(db.String(20), unique=True, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.Enum(PaymentMethod), nullable=True)
    payment_status = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    order = db.relationship('Order', backref=db.backref('bill', uselist=False))
    
    def __repr__(self):
        return f'<Bill #{self.bill_number}>'
    
    @classmethod
    def generate_bill_number(cls):
        """Generate a unique bill number."""
        last_bill = cls.query.order_by(cls.id.desc()).first()
        if last_bill:
            last_number = int(last_bill.bill_number[4:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"BILL{new_number:06d}"
    
    def mark_as_paid(self, payment_method):
        """Mark the bill as paid."""
        if isinstance(payment_method, str):
            payment_method = PaymentMethod(payment_method)
        
        self.payment_method = payment_method
        self.payment_status = True
        self.paid_at = datetime.utcnow()
        db.session.commit() 