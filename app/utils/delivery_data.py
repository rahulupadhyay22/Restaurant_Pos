import json
import logging

logger = logging.getLogger(__name__)

def standardize_delivery_data(platform, data):
    """
    Standardize delivery platform data into a consistent format.
    
    Args:
        platform (str): The delivery platform name ('zomato' or 'swiggy')
        data (dict): The raw data from the delivery platform
        
    Returns:
        dict: Standardized data structure with consistent field names
    """
    try:
        if platform.lower() == 'zomato':
            return {
                'order_id': data.get('order_id'),
                'customer': {
                    'name': data.get('customer', {}).get('name'),
                    'phone': data.get('customer', {}).get('phone'),
                },
                'address': data.get('delivery_address'),
                'items': data.get('items', []),
                'fees': {
                    'delivery_fee': data.get('delivery_fee', 0),
                    'platform_fee': data.get('platform_fee', 0),
                    'total': data.get('total_amount', 0)
                }
            }
        elif platform.lower() == 'swiggy':
            return {
                'order_id': data.get('order_id'),
                'customer': {
                    'name': data.get('customer_details', {}).get('name'),
                    'phone': data.get('customer_details', {}).get('phone'),
                },
                'address': data.get('delivery_address', {}).get('address'),
                'items': data.get('order_items', []),
                'fees': {
                    'delivery_fee': data.get('charges', {}).get('delivery_fee', 0),
                    'platform_fee': data.get('charges', {}).get('platform_fee', 0),
                    'total': data.get('order_total', 0)
                }
            }
        else:
            logger.error(f"Unknown delivery platform: {platform}")
            return {}
    except Exception as e:
        logger.error(f"Error standardizing delivery data: {str(e)}", exc_info=True)
        return {}


def extract_items_data(platform, items):
    """
    Extract and standardize items data from different delivery platforms.
    
    Args:
        platform (str): The delivery platform name ('zomato' or 'swiggy')
        items (list): The items data from the delivery platform
        
    Returns:
        list: Standardized items data with consistent field names
    """
    try:
        standardized_items = []
        
        if not items or not isinstance(items, list):
            logger.warning(f"Invalid items data format from {platform}")
            return []
        
        for item in items:
            if platform.lower() == 'zomato':
                # Extract variations if they exist
                variations = []
                if 'addons' in item and isinstance(item['addons'], list):
                    for addon in item['addons']:
                        variations.append(addon.get('name', ''))
                
                standardized_items.append({
                    'name': item.get('name', ''),
                    'quantity': item.get('quantity', 1),
                    'price': item.get('price', 0),
                    'notes': item.get('special_instructions', ''),
                    'variations': variations
                })
            elif platform.lower() == 'swiggy':
                # Extract variations if they exist
                variations = []
                if 'addons' in item and isinstance(item['addons'], list):
                    for addon in item['addons']:
                        variations.append(addon.get('name', ''))
                elif 'variations' in item and isinstance(item['variations'], list):
                    for variation in item['variations']:
                        variations.append(variation.get('name', ''))
                
                standardized_items.append({
                    'name': item.get('item_name', ''),
                    'quantity': item.get('quantity', 1),
                    'price': item.get('item_price', 0),
                    'notes': item.get('special_instructions', ''),
                    'variations': variations
                })
        
        return standardized_items
    except Exception as e:
        logger.error(f"Error extracting items data: {str(e)}", exc_info=True)
        return []


def validate_delivery_data(data):
    """
    Validate the standardized delivery data.
    
    Args:
        data (dict): The standardized delivery data
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not data.get('order_id'):
        return False, "Missing order ID"
    
    if not data.get('customer', {}).get('name'):
        return False, "Missing customer name"
    
    if not data.get('customer', {}).get('phone'):
        return False, "Missing customer phone"
    
    if not data.get('address'):
        return False, "Missing delivery address"
    
    return True, ""