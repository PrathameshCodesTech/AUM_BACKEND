"""
KYC Service - Surepass API Integration
Handles PAN and Aadhaar verification via Surepass
"""
import requests
import logging
import random
import base64
from decimal import Decimal
from django.conf import settings  # 👈 THIS LINE MUST BE PRESENT!

logger = logging.getLogger(__name__)

class SurepassKYC:
    """Service for KYC verification via Surepass API"""
    
    def __init__(self):
        self.api_token = getattr(settings, 'SUREPASS_API_TOKEN', '')
        self.test_mode = getattr(settings, 'SUREPASS_TEST_MODE', True)
        
        # 👇 NEW: Different base URLs for different APIs
        self.sandbox_url = 'https://sandbox.surepass.io'  # For Aadhaar & PAN
        self.production_url = 'https://kyc-api.surepass.io'  # For Bank only
        
        if not self.test_mode and not self.api_token:
            logger.warning("⚠️  Surepass API token not configured!")
    
    def _get_headers(self):
        """Get API headers with authorization"""
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
    
    # ============================================
    # AADHAAR VERIFICATION (PDF UPLOAD)
    # ============================================
    
    def verify_aadhaar_pdf(self, pdf_file, yob=None, full_name=None) -> dict:
        """
        Verify Aadhaar using eAadhaar PDF file
        
        Args:
            pdf_file: File object (from request.FILES)
            yob: Year of birth (optional)
            full_name: Full name (optional)
        
        Returns:
            dict with verification result
        """
        logger.info(f"📄 Verifying Aadhaar PDF - Test Mode: {self.test_mode}")
        
        if self.test_mode:
            return self._mock_aadhaar_response()
        
        try:
            # 👇 Always use sandbox for Aadhaar
            url = f"{self.sandbox_url}/api/v1/aadhaar/upload/eaadhaar"
            
            # Read file content and encode to base64
            pdf_content = pdf_file.read()
            base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
            
            # Prepare form data
            files = {
                'file': (pdf_file.name, pdf_content, 'application/pdf')
            }
            
            data = {
                'base64': base64_pdf,
            }
            
            if yob:
                data['yob'] = yob
            if full_name:
                data['full_name'] = full_name
            
            # Remove Content-Type from headers for multipart/form-data
            headers = {'Authorization': f'Bearer {self.api_token}'}
            
            response = requests.post(
                url,
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                logger.info(f"✅ Aadhaar PDF verified successfully")
                return {
                    'success': True,
                    'data': result.get('data', {}),
                    'message': 'Aadhaar verified successfully'
                }
            else:
                error_msg = result.get('message', 'Verification failed')
                logger.error(f"❌ Aadhaar verification failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Aadhaar PDF verification failed: {str(e)}")
            return {
                'success': False,
                'error': f'Aadhaar verification failed: {str(e)}'
            }
    
    def _mock_aadhaar_response(self) -> dict:
        """Return mock Aadhaar response for testing"""
        return {
            'success': True,
            'data': {
                'aadhaar_number': 'XXXX XXXX 7144',
                'name': 'Rajesh Kumar',
                'dob': '15/01/1990',
                'gender': 'M',
                'address': '123, MG Road, Koramangala, Bangalore, Karnataka - 560034',
                'split_address': {
                    'house': '123',
                    'street': 'MG Road',
                    'landmark': 'Near Metro Station',
                    'locality': 'Koramangala',
                    'vtc': 'Bangalore',
                    'district': 'Bangalore Urban',
                    'state': 'Karnataka',
                    'pincode': '560034'
                },
                'phone': '9876543210',
                'email': 'rajesh.kumar@example.com',
                'face_status': False,
                'face': None
            },
            'message': 'Aadhaar verified successfully (TEST MODE)'
        }
    
    # ============================================
    # PAN VERIFICATION
    # ============================================
    
    def verify_pan(self, pan_number: str) -> dict:
        """
        Verify PAN card with Income Tax Department
        
        Args:
            pan_number: 10-character PAN number
        
        Returns:
            dict with verification result
        """
        logger.info(f"🔍 Verifying PAN: {pan_number}")
        
        if self.test_mode:
            return self._mock_pan_response(pan_number)
        
        try:
            # 👇 Always use sandbox for PAN
            url = f"{self.sandbox_url}/api/v1/pan/pan"
            
            payload = {
                'id_number': pan_number.upper()
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                data = result.get('data', {})
                logger.info(f"✅ PAN verified: {data.get('full_name', 'Unknown')}")
                return {
                    'success': True,
                    'data': {
                        'pan_number': pan_number.upper(),
                        'full_name': data.get('full_name', ''),
                        'category': data.get('category', ''),
                        'aadhaar_linked': data.get('aadhaar_seeding_status', False),
                        'status': 'Active'
                    },
                    'message': 'PAN verified successfully'
                }
            else:
                error_msg = result.get('message', 'PAN verification failed')
                logger.error(f"❌ PAN verification failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ PAN verification failed: {str(e)}")
            return {
                'success': False,
                'error': f'PAN verification failed: {str(e)}'
            }
    
    def _mock_pan_response(self, pan_number: str) -> dict:
        """Return mock PAN response for testing"""
        return {
            'success': True,
            'data': {
                'pan_number': pan_number.upper(),
                'full_name': 'RAJESH KUMAR',
                'category': 'Individual',
                'aadhaar_linked': True,
                'status': 'Active'
            },
            'message': 'PAN verified successfully (TEST MODE)'
        }
    
    # ============================================
    # BANK ACCOUNT VERIFICATION
    # ============================================
    
    def verify_bank_account(self, account_number: str, ifsc_code: str) -> dict:
        """
        Verify bank account details
        
        Args:
            account_number: Bank account number
            ifsc_code: Bank IFSC code
        
        Returns:
            dict with verification result
        """
        logger.info(f"🏦 Verifying bank account: ****{account_number[-4:]}")
        
        if self.test_mode:
            return self._mock_bank_response(account_number, ifsc_code)
        
        try:
            # 👇 ALWAYS use production URL for Bank (no sandbox!)
            url = f"{self.production_url}/api/v1/bank-verification/"
            
            payload = {
                'id_number': account_number,
                'ifsc': ifsc_code.upper(),
                'ifsc_details': True
            }
            
            logger.info(f"📡 Calling Surepass Bank API: {url}")
            logger.info(f"📦 Payload: {payload}")
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            
            logger.info(f"📡 Response status: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"📦 Response data: {result}")
            
            if result.get('success'):
                data = result.get('data', {})
                
                # Check account_exists flag
                if not data.get('account_exists'):
                    logger.error(f"❌ Bank account does not exist")
                    return {
                        'success': False,
                        'error': 'Bank account does not exist or is invalid'
                    }
                
                # Extract IFSC details if available
                ifsc_details = data.get('ifsc_details', {})
                
                logger.info(f"✅ Bank account verified: {data.get('full_name', 'Unknown')}")
                
                return {
                    'success': True,
                    'data': {
                        'account_exists': data.get('account_exists', True),
                        'name_at_bank': data.get('full_name', ''),
                        'account_number': account_number[-4:].rjust(len(account_number), '*'),
                        'ifsc': ifsc_code.upper(),
                        'bank_name': ifsc_details.get('bank_name', ''),
                        'branch': ifsc_details.get('branch', ''),
                        'city': ifsc_details.get('city', ''),
                        'state': ifsc_details.get('state', ''),
                        'upi_enabled': ifsc_details.get('upi', False),
                        'imps_enabled': ifsc_details.get('imps', False),
                        'neft_enabled': ifsc_details.get('neft', False),
                        'rtgs_enabled': ifsc_details.get('rtgs', False),
                        'status': data.get('status', 'success')
                    },
                    'message': 'Bank account verified successfully'
                }
            else:
                error_msg = result.get('message', 'Bank verification failed')
                logger.error(f"❌ Bank verification failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Bank verification failed: {str(e)}")
            return {
                'success': False,
                'error': f'Bank verification failed: {str(e)}'
            }
    
    def _mock_bank_response(self, account_number: str, ifsc_code: str) -> dict:
        """Return mock bank response for testing"""
        return {
            'success': True,
            'data': {
                'account_exists': True,
                'name_at_bank': 'RAJESH KUMAR',
                'account_number': account_number[-4:].rjust(len(account_number), '*'),
                'ifsc': ifsc_code.upper(),
                'bank_name': 'HDFC Bank',
                'branch': 'Main Branch',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'upi_enabled': True,
                'imps_enabled': True,
                'neft_enabled': True,
                'rtgs_enabled': True,
                'status': 'success'
            },
            'message': 'Bank account verified successfully (TEST MODE)'
        }