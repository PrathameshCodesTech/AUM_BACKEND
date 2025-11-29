# accounts/services.py
import requests
import urllib.parse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def format_phone_for_route_mobile(phone: str) -> str:
    """
    Format phone number for Route Mobile API.
    Returns phone with +91 prefix for Indian numbers.
    """
    # Remove any existing + or spaces
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Handle Indian mobile numbers
    if len(clean_phone) == 10:
        # 10 digits = Indian mobile number, add +91
        return f"+91{clean_phone}"
    elif len(clean_phone) == 12 and clean_phone.startswith('91'):
        # Already has 91 prefix, add +
        return f"+{clean_phone}"
    elif len(clean_phone) == 13 and clean_phone.startswith('091'):
        # Has 091 prefix, convert to +91
        return f"+91{clean_phone[3:]}"
    else:
        # Unknown format, return as-is with + if not present
        if not phone.startswith('+'):
            return f"+{clean_phone}"
        return phone


class RouteMobileSMS:
    """Route Mobile SMS Gateway Integration - Friend's Working Config"""
    
    def __init__(self):
        self.config = settings.ROUTE_MOBILE_SMS_CONFIG
        self.is_test_mode = getattr(settings, 'ROUTE_MOBILE_TEST_MODE', True)
    
    def send_otp(self, phone, otp):
        """
        Send OTP via Route Mobile SMS Gateway
        Using friend's exact working implementation
        
        Args:
            phone (str): Phone number (will be formatted to +91XXXXXXXXXX)
            otp (str): 6-digit OTP code
            
        Returns:
            dict: {
                'success': bool,
                'message_id': str or None,
                'error': str or None,
                'status': str
            }
        """
        logger.info(f"📱 SMS: Attempting to send OTP to {phone}")
        
        # TEST MODE
        if self.is_test_mode:
            logger.info(f"📱 [TEST MODE] OTP: {otp}")
            logger.info(f"📱 [TEST MODE] Phone: {phone}")
            return {
                'success': True,
                'message_id': f'TEST_{phone}_{otp}',
                'error': None,
                'status': 'TEST_MODE',
                'otp': otp  # Return OTP in test mode for easy testing
            }
        
        # PRODUCTION MODE - Use friend's exact implementation
        try:
            # Format phone number with +91 prefix
            formatted_phone = format_phone_for_route_mobile(phone)
            logger.info(f"📱 Phone formatted: {phone} -> {formatted_phone}")
            
            # EXACT message from friend's working template
            message = f"Dear User, Please complete your registration using the One-Time Password {otp}. Thank You! Powered by DIGIELVES TECH WIZARDS PRIVATE LIMITED"
            
            # EXACT parameters from friend's config
            params = {
                "username": self.config["USERNAME"],
                "password": self.config["PASSWORD"],
                "type": self.config["TYPE"],        # Type 5 (ISO-8859-1)
                "dlr": self.config["DLR"],          # DLR 1 (delivery report)
                "destination": formatted_phone,      # +91XXXXXXXXXX format
                "source": self.config["SOURCE"],    # VBCONN
                "message": message,
                "entityid": self.config["ENTITY_ID"],
                "tempid": self.config["TEMPLATE_ID"],
            }
            
            logger.info(f"📱 SMS params: {params}")
            
            # Build URL with query parameters
            encoded_params = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
            url = f"{self.config['BASE_URL']}?{encoded_params}"
            
            logger.info(f"📱 Making HTTPS request to Route Mobile...")
            
            # Make API call with SSL verification
            response = requests.get(url, timeout=30, verify=True)
            
            logger.info(f"📱 Response - Status: {response.status_code}, Text: {response.text}")
            
            response_text = response.text.strip()
            
            # Success response: 1701|<phone>:<message_id>
            if response_text.startswith('1701'):
                parts = response_text.split('|')
                message_id = 'UNKNOWN'
                
                if len(parts) > 1 and ':' in parts[1]:
                    message_id = parts[1].split(':')[1]
                elif len(parts) > 1:
                    message_id = parts[1]
                
                logger.info(f"✅ SMS sent successfully! Message ID: {message_id}")
                
                return {
                    'success': True,
                    'message_id': message_id,
                    'error': None,
                    'status': 'SENT'
                }
            
            # Error handling
            error_code = response_text.split('|')[0] if '|' in response_text else response_text
            error_message = self._get_error_message(error_code)
            
            logger.error(f"❌ SMS failed: {error_message} (Code: {error_code})")
            
            return {
                'success': False,
                'message_id': None,
                'error': error_message,
                'status': 'FAILED',
                'error_code': error_code
            }
            
        except requests.exceptions.Timeout:
            logger.error("❌ Route Mobile API timeout")
            return {
                'success': False,
                'message_id': None,
                'error': 'SMS gateway timeout',
                'status': 'TIMEOUT'
            }
        
        except Exception as e:
            logger.error(f"❌ SMS error: {str(e)}")
            return {
                'success': False,
                'message_id': None,
                'error': f'Failed to send SMS: {str(e)}',
                'status': 'ERROR'
            }
    
    def _get_error_message(self, error_code):
        """Map Route Mobile error codes to user-friendly messages"""
        error_map = {
            '1702': 'Invalid request parameters',
            '1703': 'Authentication failed - check credentials',
            '1704': 'Invalid message type',
            '1705': 'Invalid message content',
            '1706': 'Invalid phone number',
            '1707': 'Invalid sender ID',
            '1708': 'Delivery report configuration error',
            '1709': 'User validation failed',
            '1710': 'Internal gateway error',
            '1025': 'Insufficient SMS credits',
            '1715': 'Request timeout',
            '1032': 'Number is on DND (Do Not Disturb)',
            '1028': 'Spam message detected',
            '1051': 'Invalid DLT template ID',
            '1052': 'Invalid DLT entity ID',
        }
        
        return error_map.get(error_code, f'SMS failed (Error: {error_code})')