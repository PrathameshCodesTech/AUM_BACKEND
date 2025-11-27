# accounts/services/sms_service.py
import requests
from urllib.parse import urlencode
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class RouteMobileSMS:
    """
    Route Mobile SMS Gateway Integration
    Handles OTP and transactional SMS
    """

    def __init__(self):
        self.username = settings.ROUTE_MOBILE_USERNAME
        self.password = settings.ROUTE_MOBILE_PASSWORD
        self.server_url = settings.ROUTE_MOBILE_SERVER
        self.entity_id = settings.ROUTE_MOBILE_ENTITY_ID
        self.template_id = settings.ROUTE_MOBILE_TEMPLATE_ID
        self.sender_id = settings.ROUTE_MOBILE_SENDER_ID
        self.is_test_mode = settings.ROUTE_MOBILE_TEST_MODE

    def send_otp(self, phone, otp):
        """
        Send OTP via Route Mobile SMS Gateway

        Args:
            phone (str): Phone number with country code (e.g., +919876543210)
            otp (str): 6-digit OTP

        Returns:
            dict: {
                'success': bool,
                'message_id': str or None,
                'error': str or None
            }
        """
        # Format phone number
        if not phone.startswith('+'):
            phone = '+91' + phone.lstrip('0')

        # Create message
        message = f"Your OTP for AssetKart is {otp}. Valid for 5 minutes. Do not share with anyone."

        # TEST MODE - Print to console
        if self.is_test_mode:
            logger.info(f"📱 [TEST MODE] Sending OTP to {phone}")
            logger.info(f"📱 [TEST MODE] OTP: {otp}")
            logger.info(f"📱 [TEST MODE] Message: {message}")

            return {
                'success': True,
                'message_id': f'TEST_{phone}_{otp}',
                'error': None,
                'status': 'TEST_MODE'
            }

        # PRODUCTION MODE - Call Route Mobile API
        try:
            # Build API URL
            params = {
                'username': self.username,
                'password': self.password,
                'type': '5',  # Plain text
                'dlr': '1',   # Enable delivery report
                'destination': phone,
                'source': self.sender_id,
                'message': message,
                'entityid': self.entity_id,
                'tempid': self.template_id,
            }

            # Construct full URL
            api_url = f"{self.server_url}/bulksms/bulksms?{urlencode(params)}"

            logger.info(f"📱 Sending OTP to {phone} via Route Mobile")

            # Make API call
            response = requests.get(api_url, timeout=10)

            # Parse response
            response_text = response.text.strip()

            # Success response: 1701|<phone>:<message_id>
            if response_text.startswith('1701'):
                parts = response_text.split('|')
                if len(parts) > 1:
                    message_id = parts[1].split(
                        ':')[1] if ':' in parts[1] else parts[1]

                    logger.info(
                        f"✅ OTP sent successfully. Message ID: {message_id}")

                    return {
                        'success': True,
                        'message_id': message_id,
                        'error': None,
                        'status': 'SENT'
                    }

            # Error handling
            error_code = response_text.split(
                '|')[0] if '|' in response_text else response_text
            error_message = self._get_error_message(error_code)

            logger.error(
                f"❌ Failed to send OTP: {error_message} (Code: {error_code})")

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
                'error': 'SMS gateway timeout. Please try again.',
                'status': 'TIMEOUT'
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Route Mobile API error: {str(e)}")
            return {
                'success': False,
                'message_id': None,
                'error': 'SMS service temporarily unavailable.',
                'status': 'ERROR'
            }

        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            return {
                'success': False,
                'message_id': None,
                'error': 'Failed to send OTP. Please try again.',
                'status': 'ERROR'
            }

    def _get_error_message(self, error_code):
        """Map Route Mobile error codes to user-friendly messages"""
        error_map = {
            '1702': 'Invalid request parameters',
            '1703': 'Authentication failed',
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

        return error_map.get(error_code, f'Failed to send SMS (Error: {error_code})')

    def send_transactional_sms(self, phone, message, template_id=None):
        """
        Send transactional SMS (non-OTP)

        Args:
            phone (str): Phone number
            message (str): Message content
            template_id (str): Optional template ID (defaults to main template)

        Returns:
            dict: Same as send_otp
        """
        if not phone.startswith('+'):
            phone = '+91' + phone.lstrip('0')

        if self.is_test_mode:
            logger.info(f"📱 [TEST MODE] Sending SMS to {phone}")
            logger.info(f"📱 [TEST MODE] Message: {message}")
            return {
                'success': True,
                'message_id': f'TEST_{phone}',
                'error': None
            }

        try:
            params = {
                'username': self.username,
                'password': self.password,
                'type': '5',
                'dlr': '1',
                'destination': phone,
                'source': self.sender_id,
                'message': message,
                'entityid': self.entity_id,
                'tempid': template_id or self.template_id,
            }

            api_url = f"{self.server_url}/bulksms/bulksms?{urlencode(params)}"
            response = requests.get(api_url, timeout=10)
            response_text = response.text.strip()

            if response_text.startswith('1701'):
                parts = response_text.split('|')
                message_id = parts[1].split(':')[1] if len(
                    parts) > 1 and ':' in parts[1] else 'UNKNOWN'

                return {
                    'success': True,
                    'message_id': message_id,
                    'error': None
                }

            error_code = response_text.split('|')[0]
            return {
                'success': False,
                'message_id': None,
                'error': self._get_error_message(error_code)
            }

        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            return {
                'success': False,
                'message_id': None,
                'error': 'Failed to send SMS'
            }
