from app import db
from datetime import datetime
import enum

class DeliveryPlatform(enum.Enum):
    """Enum for delivery platforms."""
    ZOMATO = "zomato"
    SWIGGY = "swiggy"


class DeliveryStatus(enum.Enum):
    """Enum for delivery order status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY = "ready"
    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class DeliveryOrder(db.Model):
    """DeliveryOrder model for delivery orders."""
    __tablename__ = 'delivery_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.Enum(DeliveryPlatform), nullable=False)
    platform_order_id = db.Column(db.String(100), unique=True, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    status = db.Column(db.Enum(DeliveryStatus), default=DeliveryStatus.PENDING)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_address = db.Column(db.Text, nullable=False)
    delivery_fee = db.Column(db.Float, default=0.0)
    platform_fee = db.Column(db.Float, default=0.0)
    estimated_delivery_time = db.Column(db.DateTime, nullable=True)
    driver_name = db.Column(db.String(100), nullable=True)
    driver_phone = db.Column(db.String(20), nullable=True)
    items_data = db.Column(db.Text, nullable=True)  # JSON string of order items from delivery platform
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DeliveryOrder {self.platform.value} #{self.platform_order_id}>'
    
    def accept(self):
        """Accept the delivery order."""
        self.status = DeliveryStatus.ACCEPTED
        db.session.commit()
    
    def reject(self):
        """Reject/cancel the delivery order."""
        self.status = DeliveryStatus.CANCELLED
        db.session.commit()
    
    def update_status(self, status):
        """Update the delivery order status."""
        if isinstance(status, str):
            status = DeliveryStatus(status)
        self.status = status
        db.session.commit()