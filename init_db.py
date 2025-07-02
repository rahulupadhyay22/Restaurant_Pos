from app import create_app, db
from app.models.user import User
from app.models.menu import Category, MenuItem
from app.models.table import Table
from app.models.settings import Settings
import os

app = create_app()

with app.app_context():
    # Create tables
    db.create_all()
    
    # Check if admin user exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        print("Creating admin user...")
        admin = User(
            username='admin',
            email='admin@restaurant.com',
            role='admin'
        )
        admin.set_password('admin123')  # Set a default password
        db.session.add(admin)
    
    # Check if staff user exists
    staff = User.query.filter_by(username='staff').first()
    if not staff:
        print("Creating staff user...")
        staff = User(
            username='staff',
            email='staff@restaurant.com',
            role='staff'
        )
        staff.set_password('staff123')  # Set a default password
        db.session.add(staff)
    
    # Create default settings if they don't exist
    if not Settings.get('tax_rate'):
        print("Creating default settings...")
        Settings.set('tax_rate', '5')
        Settings.set('restaurant_name', 'Restaurant Name')
        Settings.set('restaurant_phone', '+1234567890')
        Settings.set('restaurant_address', '123 Main St, City, Country')
    
    # Create sample categories if none exist
    if Category.query.count() == 0:
        print("Creating sample categories...")
        categories = [
            Category(name='Starters'),
            Category(name='Main Course'),
            Category(name='Desserts'),
            Category(name='Beverages')
        ]
        db.session.add_all(categories)
        db.session.commit()  # Commit to get IDs
        
        # Create sample menu items
        print("Creating sample menu items...")
        menu_items = [
            # Starters
            MenuItem(name='Vegetable Spring Rolls', description='Crispy spring rolls filled with vegetables', 
                    half_price=5.99, full_price=9.99, category_id=categories[0].id),
            MenuItem(name='Chicken Wings', description='Spicy chicken wings with dipping sauce', 
                    half_price=6.99, full_price=12.99, category_id=categories[0].id),
            
            # Main Course
            MenuItem(name='Butter Chicken', description='Chicken in a rich buttery tomato sauce', 
                    half_price=8.99, full_price=15.99, category_id=categories[1].id),
            MenuItem(name='Paneer Tikka Masala', description='Cottage cheese in a spiced curry sauce', 
                    half_price=7.99, full_price=14.99, category_id=categories[1].id),
            MenuItem(name='Vegetable Biryani', description='Fragrant rice dish with mixed vegetables', 
                    full_price=12.99, category_id=categories[1].id),
            
            # Desserts
            MenuItem(name='Gulab Jamun', description='Sweet milk solids balls soaked in sugar syrup', 
                    full_price=5.99, category_id=categories[2].id),
            MenuItem(name='Ice Cream', description='Vanilla, chocolate, or strawberry', 
                    full_price=4.99, category_id=categories[2].id),
            
            # Beverages
            MenuItem(name='Mango Lassi', description='Sweet yogurt drink with mango', 
                    full_price=3.99, category_id=categories[3].id),
            MenuItem(name='Masala Chai', description='Spiced Indian tea with milk', 
                    full_price=2.99, category_id=categories[3].id),
            MenuItem(name='Soft Drinks', description='Coke, Sprite, Fanta', 
                    full_price=1.99, category_id=categories[3].id)
        ]
        db.session.add_all(menu_items)
    
    # Create sample tables if none exist
    if Table.query.count() == 0:
        print("Creating sample tables...")
        tables = [
            Table(name='Table 1', capacity=2),
            Table(name='Table 2', capacity=2),
            Table(name='Table 3', capacity=4),
            Table(name='Table 4', capacity=4),
            Table(name='Table 5', capacity=6),
            Table(name='Table 6', capacity=8)
        ]
        db.session.add_all(tables)
    
    # Commit all changes
    db.session.commit()
    
    print("Database initialized successfully!") 