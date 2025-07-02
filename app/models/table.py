from app import db
from datetime import datetime

class Table(db.Model):
    """Table model for restaurant tables."""
    __tablename__ = 'tables'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)  # e.g., "Table 1", "Table 2"
    capacity = db.Column(db.Integer, default=4)
    is_occupied = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    orders = db.relationship('Order', backref='table', lazy='dynamic')
    
    def __repr__(self):
        return f'<Table {self.name}>'
    
    @property
    def status(self):
        """Return the status of the table."""
        if self.is_occupied:
            active_order = self.get_active_order()
            if active_order:
                return f"Occupied - Order #{active_order.id}"
            return "Occupied"
        return "Available"
    
    def get_active_order(self):
        """Get the active order for this table, if any."""
        from app.models.order import Order, OrderStatus
        return Order.query.filter_by(
            table_id=self.id, 
            status=OrderStatus.ACTIVE
        ).first() 