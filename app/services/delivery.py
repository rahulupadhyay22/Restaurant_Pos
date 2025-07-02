import requests
import json
from flask import current_app
from app.models.delivery import DeliveryOrder, DeliveryStatus, DeliveryPlatform
from app.models.settings import Settings
from app import db
import logging

# Set up logging
logger = logging.getLogger(__name__)

class DeliveryService:
    """Base class for delivery services."""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
    
    def update_order_status(self, platform_order_id, status):
        """Update the status of an order on the delivery platform."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_order_details(self, platform_order_id):
        """Get the details of an order from the delivery platform."""
        raise NotImplementedError("Subclasses must implement this method")


class ZomatoService(DeliveryService):
    """Service for Zomato integration."""
    
    def __init__(self):
        # Get API key from settings
        api_key = Settings.get('zomato_api_key', '')
        enabled = Settings.get('zomato_enabled', 'false') == 'true'
        super().__init__(api_key)
        
        # Update to the actual Zomato API endpoint
        self.base_url = "https://api.zomato.com/api/v1.1"  # Replace with actual Zomato API URL
        self.enabled = enabled and api_key != ''
    
    def update_order_status(self, platform_order_id, status):
        """Update the status of an order on Zomato."""
        if not self.enabled or not self.api_key:
            logger.warning("Zomato integration is disabled or missing API key")
            return None
            
        # Map internal status to Zomato status codes
        status_mapping = {
            DeliveryStatus.ACCEPTED.value: "accepted",
            DeliveryStatus.PREPARING.value: "preparing",
            DeliveryStatus.READY.value: "ready",
            DeliveryStatus.PICKED_UP.value: "picked_up",
            DeliveryStatus.DELIVERED.value: "delivered",
            DeliveryStatus.CANCELLED.value: "cancelled"
        }
        
        zomato_status = status_mapping.get(status, "accepted")
        
        # Actual Zomato API endpoint for updating order status
        url = f"{self.base_url}/orders/{platform_order_id}/status"
        payload = {
            'status': zomato_status,
            # Add any other required fields for the Zomato API
        }
        
        try:
            response = requests.put(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error updating Zomato order status: {e.response.status_code} - {e.response.text}")
            return {'error': f"HTTP error: {e.response.status_code}", 'details': e.response.text}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error updating Zomato order status: {e}")
            return {'error': "Connection error", 'details': str(e)}
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout updating Zomato order status: {e}")
            return {'error': "Request timed out", 'details': str(e)}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating Zomato order status: {e}")
            return {'error': "Request failed", 'details': str(e)}
        except ValueError as e:
            logger.error(f"JSON parsing error in Zomato response: {e}")
            return {'error': "Invalid response format", 'details': str(e)}
    
    def get_order_details(self, platform_order_id):
        """Get the details of an order from Zomato."""
        if not self.enabled or not self.api_key:
            logger.warning("Zomato integration is disabled or missing API key")
            return None
            
        # Actual Zomato API endpoint for getting order details
        url = f"{self.base_url}/orders/{platform_order_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Process and standardize the response format
            return {
                'order_id': data.get('id') or platform_order_id,
                'customer_name': data.get('customer', {}).get('name', ''),
                'customer_phone': data.get('customer', {}).get('phone', ''),
                'customer_address': data.get('delivery_address', ''),
                'items': data.get('items', []),
                'status': data.get('status', ''),
                'delivery_fee': data.get('delivery_fee', 0),
                'platform_fee': data.get('platform_fee', 0),
                'total': data.get('total', 0)
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error getting Zomato order details: {e.response.status_code} - {e.response.text}")
            return {'error': f"HTTP error: {e.response.status_code}", 'details': e.response.text}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error getting Zomato order details: {e}")
            return {'error': "Connection error", 'details': str(e)}
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout getting Zomato order details: {e}")
            return {'error': "Request timed out", 'details': str(e)}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting Zomato order details: {e}")
            return {'error': "Request failed", 'details': str(e)}
        except ValueError as e:
            logger.error(f"JSON parsing error in Zomato response: {e}")
            return {'error': "Invalid response format", 'details': str(e)}


class SwiggyService(DeliveryService):
    """Service for Swiggy integration."""
    
    def __init__(self):
        # Get API key from settings
        api_key = Settings.get('swiggy_api_key', '')
        enabled = Settings.get('swiggy_enabled', 'false') == 'true'
        super().__init__(api_key)
        
        # Update to the actual Swiggy API endpoint
        self.base_url = "https://partner-api.swiggy.com/v1"  # Replace with actual Swiggy API URL
        self.enabled = enabled and api_key != ''
        
        # Add any additional headers required by Swiggy
        self.headers['Partner-ID'] = Settings.get('swiggy_partner_id', '')  # If Swiggy requires a partner ID
    
    def update_order_status(self, platform_order_id, status):
        """Update the status of an order on Swiggy."""
        if not self.enabled or not self.api_key:
            logger.warning("Swiggy integration is disabled or missing API key")
            return None
            
        # Map internal status to Swiggy status codes
        status_mapping = {
            DeliveryStatus.ACCEPTED.value: "ACCEPTED",
            DeliveryStatus.PREPARING.value: "PREPARING",
            DeliveryStatus.READY.value: "READY_FOR_PICKUP",
            DeliveryStatus.PICKED_UP.value: "PICKED_UP",
            DeliveryStatus.DELIVERED.value: "DELIVERED",
            DeliveryStatus.CANCELLED.value: "CANCELLED"
        }
        
        swiggy_status = status_mapping.get(status, "ACCEPTED")
        
        # Actual Swiggy API endpoint for updating order status
        url = f"{self.base_url}/orders/{platform_order_id}/status"
        payload = {
            'status': swiggy_status,
            'timestamp': int(time.time()),  # Swiggy might require a timestamp
            # Add any other required fields for the Swiggy API
        }
        
        try:
            response = requests.put(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error updating Swiggy order status: {e.response.status_code} - {e.response.text}")
            return {'error': f"HTTP error: {e.response.status_code}", 'details': e.response.text}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error updating Swiggy order status: {e}")
            return {'error': "Connection error", 'details': str(e)}
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout updating Swiggy order status: {e}")
            return {'error': "Request timed out", 'details': str(e)}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating Swiggy order status: {e}")
            return {'error': "Request failed", 'details': str(e)}
        except ValueError as e:
            logger.error(f"JSON parsing error in Swiggy response: {e}")
            return {'error': "Invalid response format", 'details': str(e)}
    
    def get_order_details(self, platform_order_id):
        """Get the details of an order from Swiggy."""
        if not self.enabled or not self.api_key:
            logger.warning("Swiggy integration is disabled or missing API key")
            return None
            
        # Actual Swiggy API endpoint for getting order details
        url = f"{self.base_url}/orders/{platform_order_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Process and standardize the response format
            return {
                'order_id': data.get('id') or platform_order_id,
                'customer_name': data.get('customer_details', {}).get('name', ''),
                'customer_phone': data.get('customer_details', {}).get('phone', ''),
                'customer_address': data.get('delivery_address', {}).get('address', ''),
                'items': data.get('order_items', []),
                'status': data.get('status', ''),
                'delivery_fee': data.get('charges', {}).get('delivery_fee', 0),
                'platform_fee': data.get('charges', {}).get('platform_fee', 0),
                'total': data.get('order_total', 0)
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error getting Swiggy order details: {e.response.status_code} - {e.response.text}")
            return {'error': f"HTTP error: {e.response.status_code}", 'details': e.response.text}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error getting Swiggy order details: {e}")
            return {'error': "Connection error", 'details': str(e)}
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout getting Swiggy order details: {e}")
            return {'error': "Request timed out", 'details': str(e)}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting Swiggy order details: {e}")
            return {'error': "Request failed", 'details': str(e)}
        except ValueError as e:
            logger.error(f"JSON parsing error in Swiggy response: {e}")
            return {'error': "Invalid response format", 'details': str(e)}