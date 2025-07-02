from app import db
from datetime import datetime

class Category(db.Model):
    """Category model for menu item categories."""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    menu_items = db.relationship('MenuItem', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<Category {self.name}>'


class MenuItem(db.Model):
    """MenuItem model for menu items."""
    __tablename__ = 'menu_items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    half_price = db.Column(db.Float, nullable=True)  # Price for half quantity
    full_price = db.Column(db.Float, nullable=False)  # Price for full quantity
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='menu_item', lazy='dynamic')
    
    def __repr__(self):
        return f'<MenuItem {self.name}>'
    
    @property
    def has_half_option(self):
        """Check if the menu item has a half quantity option."""
        return self.half_price is not None 