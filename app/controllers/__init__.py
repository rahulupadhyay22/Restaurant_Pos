from app.controllers.auth import auth_bp
from app.controllers.admin import admin_bp
from app.controllers.staff import staff_bp
from app.controllers.menu import menu_bp
from app.controllers.table import table_bp
from app.controllers.order import order_bp
from app.controllers.billing import billing_bp
from app.controllers.delivery import delivery_bp

__all__ = [
    'auth_bp',
    'admin_bp',
    'staff_bp',
    'menu_bp',
    'table_bp',
    'order_bp',
    'billing_bp',
    'delivery_bp'
]
