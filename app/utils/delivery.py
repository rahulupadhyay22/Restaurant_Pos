import hmac
import hashlib

def verify_signature(payload, signature, secret):
    """Verify webhook signature.
    
    Args:
        payload (bytes): The raw request body
        signature (str): The signature from the request header
        secret (str): The webhook secret
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Validate inputs
    if not signature:
        logger.warning("Empty signature provided for verification")
        return False
        
    if not secret:
        logger.warning("Empty webhook secret configured")
        return False
    
    if not payload:
        logger.warning("Empty payload received for signature verification")
        return False
        
    try:
        # This is a generic implementation - adjust according to the platform's documentation
        computed_signature = hmac.new(
            key=secret.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Use constant time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(computed_signature, signature)
        
        if not is_valid:
            logger.warning(f"Signature verification failed. Expected: {computed_signature[:10]}..., Received: {signature[:10]}...")
        
        return is_valid
    except Exception as e:
        logger.error(f"Error during signature verification: {str(e)}", exc_info=True)
        return False