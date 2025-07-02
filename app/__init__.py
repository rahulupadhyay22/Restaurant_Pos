from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
socketio = SocketIO()
limiter = Limiter(key_func=get_remote_address)

# Add this to your app initialization
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

def create_app(config_class=None):
    import datetime
    import json
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    app = Flask(__name__)
    
    # Load configuration
    if config_class is None:
        app.config.from_object('app.config.Config')
    else:
        app.config.from_object(config_class)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    socketio.init_app(app, async_mode='threading')
    limiter.init_app(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.controllers.auth import auth_bp
    from app.controllers.admin import admin_bp
    from app.controllers.staff import staff_bp
    from app.controllers.menu import menu_bp
    from app.controllers.table import table_bp
    from app.controllers.order import order_bp
    from app.controllers.billing import billing_bp
    from app.controllers.delivery import delivery_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(menu_bp)
    app.register_blueprint(table_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(delivery_bp)
    
    # Add root route
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))
    
    # Add context processor to make settings available to all templates
    @app.context_processor
    def inject_settings():
        from app.models.settings import Settings
        return {'Settings': Settings}
    
    # ✅ Add license info context processor
    @app.context_processor
    def inject_license_info():
        license_days_left = None
        license_expiry_date = None
        license_error = None
        license_path = None

        try:
            # Automatically find license_*.lic file
            for f in os.listdir('.'):
                if f.startswith('license_') and f.endswith('.lic'):
                    license_path = f
                    break

            if not license_path:
                license_error = "License file not found."
            else:
                with open(license_path, 'r') as lic_file:
                    license_data = json.load(lic_file)

                with open('public.pem', 'rb') as key_file:
                    public_key = serialization.load_pem_public_key(key_file.read())

                license_json = json.dumps(license_data["license"], separators=(',', ':')).encode()
                signature = bytes.fromhex(license_data["signature"])

                # Verify signature
                public_key.verify(
                    signature,
                    license_json,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH,
                    ),
                    hashes.SHA256()
                )

                expiry_date = datetime.datetime.strptime(license_data["license"]["expiry_date"], "%Y-%m-%d").date()
                license_expiry_date = expiry_date.strftime("%Y-%m-%d")
                days_left = (expiry_date - datetime.date.today()).days
                license_days_left = days_left

                if days_left < 0:
                    license_error = "License expired."
        except Exception as e:
            license_error = f"License verification failed: {str(e)}"

        return dict(
            license_days_left=license_days_left,
            license_expiry_date=license_expiry_date,
            license_error=license_error
        )

    return app
