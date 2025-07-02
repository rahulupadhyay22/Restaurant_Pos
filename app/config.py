import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_for_development')
    # Use SQLite by default
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///restaurant_pos.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Restaurant details for receipts
    RESTAURANT_NAME = os.environ.get('RESTAURANT_NAME', 'Restaurant Name')
    RESTAURANT_PHONE = os.environ.get('RESTAURANT_PHONE', '+1234567890')
    RESTAURANT_ADDRESS = os.environ.get('RESTAURANT_ADDRESS', '123 Main St, City, Country')
    
    # Delivery service API keys
    ZOMATO_API_KEY = os.environ.get('ZOMATO_API_KEY', '')
    SWIGGY_API_KEY = os.environ.get('SWIGGY_API_KEY', '')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
    WTF_CSRF_ENABLED = False
