from app import db
from datetime import datetime
import enum

class OrderStatus(enum.Enum):
    """Enum for order status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OrderType(enum.Enum):
    """Enum for order type."""
    DINE_IN = "dine_in"
    ZOMATO = "zomato"
    SWIGGY = "swiggy"
    


class Order(db.Model):
    """Order model for restaurant orders."""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=True)  # Nullable for delivery orders
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Enum(OrderStatus), default=OrderStatus.ACTIVE)
    order_type = db.Column(db.Enum(OrderType), default=OrderType.DINE_IN)
    delivery_id = db.Column(db.String(100), nullable=True)  # For Zomato/Swiggy order IDs
    customer_name = db.Column(db.String(100), nullable=True)  # For delivery orders
    customer_phone = db.Column(db.String(20), nullable=True)  # For delivery orders
    customer_address = db.Column(db.Text, nullable=True)  # For delivery orders
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order #{self.id}>'
    
    @property
    def total_amount(self):
        """Calculate the total amount for the order."""
        return sum(item.subtotal for item in self.items)
    
    def complete(self):
        """Mark the order as completed."""
        self.status = OrderStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if self.table:
            self.table.is_occupied = False
        db.session.commit()
    
    def cancel(self):
        """Cancel the order."""
        self.status = OrderStatus.CANCELLED
        if self.table:
            self.table.is_occupied = False
        db.session.commit()


class OrderItem(db.Model):
    """OrderItem model for items in an order."""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    is_half = db.Column(db.Boolean, default=False)  # Whether it's half quantity
    price = db.Column(db.Float, nullable=False)  # Price at the time of order
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<OrderItem {self.menu_item_id} x{self.quantity}>'
    
    @property
    def subtotal(self):
        """Calculate the subtotal for this item."""
        return self.price * self.quantity