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
from PyPDF2 import PdfReader, PdfWriter  # 👈 ADD THIS
from io import BytesIO  # 👈 ADD THIS

logger = logging.getLogger(__name__)

class SurepassKYC:
    """Service for KYC verification via Surepass API"""
    
    def __init__(self):
        self.api_token = getattr(settings, 'SUREPASS_API_TOKEN', '')
        self.test_mode = getattr(settings, 'SUREPASS_TEST_MODE', True)
        
        # 👇 NEW: Different base URLs for different APIs
        self.sandbox_url = 'https://sandbox.surepass.io'  # For Aadhaar & PAN
        self.production_url = 'https://kyc-api.surepass.io'  # For Bank only

        self.base_url = getattr(settings, 'SUREPASS_BASE_URL', self.sandbox_url)
        
        if not self.test_mode and not self.api_token:
            logger.warning("⚠️  Surepass API token not configured!")
    
    
    def unlock_pdf(self, pdf_content, password):
        """
        Unlock password-protected PDF with smart password attempts
        
        Args:
            pdf_content: bytes - PDF file content
            password: str - Primary password attempt (YOB, Pincode, etc.)
        
        Returns:
            bytes: Unlocked PDF content
        """
        try:
            # Create file-like object from bytes
            pdf_stream = BytesIO(pdf_content)
            
            # Read PDF
            reader = PdfReader(pdf_stream)
            
            # Check if encrypted
            if not reader.is_encrypted:
                logger.info("ℹ️  PDF is not encrypted")
                return pdf_content  # Return original if not encrypted
            
            logger.info(f"🔒 PDF is encrypted, attempting to unlock...")
            
            # Try to decrypt
            decrypt_result = reader.decrypt(password)
            
            if decrypt_result in [1, 2]:
                logger.info(f"✅ PDF unlocked successfully with primary password")
                
                # Write unlocked PDF
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                
                output = BytesIO()
                writer.write(output)
                output.seek(0)
                
                unlocked_content = output.read()
                logger.info(f"✅ PDF unlocked - Size: {len(unlocked_content)} bytes")
                
                return unlocked_content
            else:
                # Password failed
                raise ValueError("Incorrect password")
            
        except Exception as e:
            logger.error(f"❌ Failed to unlock PDF: {str(e)}")
            raise ValueError(f"Failed to unlock PDF: {str(e)}")
    
    def try_multiple_passwords(self, pdf_content, yob=None, full_name=None, pincode=None):
        """
        Try multiple password combinations to unlock eAadhaar PDF
        
        Common eAadhaar password formats:
        1. YOB (4 digits) - e.g., "2002"
        2. First 4 letters of name + YOB - e.g., "PRAT2002"
        3. Full name (uppercase) + YOB - e.g., "PRATHAMESH2002"
        4. Pincode (6 digits) - e.g., "400001"
        5. DOB in DDMMYYYY - e.g., "15012002"
        
        Args:
            pdf_content: bytes - PDF content
            yob: str - Year of birth
            full_name: str - Full name
            pincode: str - Pincode
        
        Returns:
            bytes: Unlocked PDF content
        """
        passwords_to_try = []
        
        # 1. Try YOB first (most common)
        if yob:
            passwords_to_try.append(yob)
        
        # 2. Try first 4 letters of name + YOB
        if full_name and yob:
            name_upper = full_name.upper().replace(' ', '')
            first_4 = name_upper[:4] if len(name_upper) >= 4 else name_upper
            passwords_to_try.append(f"{first_4}{yob}")
        
        # 3. Try full name + YOB (no spaces)
        if full_name and yob:
            name_upper = full_name.upper().replace(' ', '')
            passwords_to_try.append(f"{name_upper}{yob}")
        
        # 4. Try pincode
        if pincode:
            passwords_to_try.append(pincode)
        
        # 5. Try lowercase versions
        if full_name and yob:
            name_lower = full_name.lower().replace(' ', '')
            first_4_lower = name_lower[:4] if len(name_lower) >= 4 else name_lower
            passwords_to_try.append(f"{first_4_lower}{yob}")
        
        logger.info(f"🔑 Attempting {len(passwords_to_try)} password combinations...")
        
        # Try each password
        for idx, pwd in enumerate(passwords_to_try, 1):
            try:
                logger.info(f"🔓 Attempt {idx}/{len(passwords_to_try)}: Trying password format...")
                unlocked = self.unlock_pdf(pdf_content, pwd)
                logger.info(f"✅ SUCCESS! PDF unlocked with password attempt #{idx}")
                return unlocked
            except ValueError:
                logger.info(f"❌ Attempt {idx} failed")
                continue
        
        # If all attempts failed
        raise ValueError(
            "Could not unlock PDF with any password combination. "
            "Please ensure you entered correct Year of Birth and Name. "
            "You can also try using your Pincode as the password."
        )
    
    def _get_headers(self):
        """Get API headers with authorization"""
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
    
    # ============================================
    # AADHAAR VERIFICATION — DIGILOCKER (NEW)
    # ============================================

    def digilocker_initialize(self) -> dict:
        """
        Initialize a Surepass DigiLocker session.
        Returns: { success, data: { token, client_id, gateway } }
        """
        logger.info("🔗 Initializing DigiLocker session")

        if self.test_mode:
            import uuid
            return {
                'success': True,
                'data': {
                    'client_id': f'test_cl_{uuid.uuid4().hex[:12]}',
                    'token': 'test_digilocker_token',
                    'gateway': f'{self.base_url}/digilocker/gateway',
                },
                'message': 'DigiLocker initialized (TEST MODE)',
            }

        try:
            url = f"{self.base_url}/api/v1/digilocker/initialize"
            response = requests.post(url, json={"data": {}}, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return {
                    'success': True,
                    'data': result.get('data', {}),
                }
            return {'success': False, 'error': result.get('message', 'DigiLocker init failed')}

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ DigiLocker init failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    def digilocker_download_aadhaar(self, client_id: str) -> dict:
        """
        Fetch Aadhaar data from a completed DigiLocker session.
        Returns: { success, data: { full_name, dob, gender, address, ... } }
        """
        logger.info(f"📥 Fetching DigiLocker Aadhaar for client_id={client_id}")

        if self.test_mode:
            return {
                'success': True,
                'data': {
                    'full_name': 'Rajesh Kumar',
                    'dob': '1990-01-15',
                    'gender': 'M',
                    'aadhaar_number': 'XXXX XXXX 7144',
                    'address': {
                        'house': '123',
                        'street': 'MG Road',
                        'vtc': 'Bangalore',
                        'dist': 'Bangalore Urban',
                        'state': 'Karnataka',
                        'zip': '560034',
                    },
                },
                'message': 'Aadhaar fetched (TEST MODE)',
            }

        try:
            url = f"{self.base_url}/api/v1/digilocker/download-aadhaar/{client_id}"
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return {'success': True, 'data': result.get('data', {})}
            return {'success': False, 'error': result.get('message', 'Download failed')}

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ DigiLocker download failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    # ============================================
    # AADHAAR VERIFICATION (PDF UPLOAD) — DEPRECATED
    # No longer called by any active endpoint.
    # Use digilocker_initialize / digilocker_download_aadhaar instead.
    # ============================================

    def verify_aadhaar_pdf(self, pdf_file, yob=None, full_name=None,  pincode=None) -> dict:
        """
        Verify Aadhaar using eAadhaar PDF file (with PDF unlocking)
        
        Args:
            pdf_file: File object (from request.FILES)
            yob: Year of birth (4 digits) - used as PDF password
            full_name: Full name (optional) - for additional validation
        
        Returns:
            dict with verification result
        """
        logger.info(f"📄 Verifying Aadhaar PDF - Test Mode: {self.test_mode}")
        
        if self.test_mode:
            return self._mock_aadhaar_response()
        
        try:
            # 👇 Always use sandbox for Aadhaar
            url = f"{self.sandbox_url}/api/v1/aadhaar/upload/eaadhaar"
            
            # Read file content
            pdf_content = pdf_file.read()
            logger.info(f"📄 Original PDF size: {len(pdf_content)} bytes")
            
            # Try to unlock PDF if YOB provided
            # Try to unlock PDF with multiple password attempts
            if yob or full_name or pincode:
                try:
                    logger.info(f"🔓 Attempting to unlock PDF with multiple password combinations...")
                    unlocked_content = self.try_multiple_passwords(
                        pdf_content, 
                        yob=yob, 
                        full_name=full_name,
                        pincode=pincode    # We don't have pincode yet
                    )
                    pdf_content = unlocked_content
                    logger.info(f"✅ Using unlocked PDF - Size: {len(pdf_content)} bytes")
                except ValueError as ve:
                    # If unlocking failed with all attempts, return clear error
                    logger.error(f"❌ PDF unlock failed after all attempts: {str(ve)}")
                    return {
                        'success': False,
                        'error': str(ve)
                    }
                except Exception as e:
                    # If PDF is not encrypted or other error, continue with original
                    logger.warning(f"⚠️ Could not unlock PDF: {str(e)}")
                    logger.info("ℹ️  Continuing with original PDF content")
            
            # Encode to base64
            base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
            
            # Prepare JSON payload
            payload = {
                'base64': base64_pdf,
            }
            
            # Add optional parameters
            if yob:
                payload['yob'] = yob
            if full_name:
                payload['full_name'] = full_name
            
            # Use JSON headers
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            
            logger.info(f"📡 Sending request to: {url}")
            logger.info(f"📦 Payload keys: {list(payload.keys())}")
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            logger.info(f"📡 Response status: {response.status_code}")
            
            # Try to parse response even on error
            try:
                result = response.json()
                logger.info(f"📦 Response data: {result}")
            except:
                logger.error(f"❌ Failed to parse JSON response: {response.text}")
                return {
                    'success': False,
                    'error': f'Invalid response from API: {response.text[:200]}'
                }
            
            # Check for API-level errors first (before raise_for_status)
            if not result.get('success'):
                error_msg = result.get('message', 'Verification failed')
                
                # Handle specific error messages
                if 'Incorrect PDF or signature' in error_msg:
                    return {
                        'success': False,
                        'error': 'Invalid eAadhaar PDF. Please ensure you uploaded a valid eAadhaar PDF downloaded from UIDAI. The PDF should not be modified.'
                    }
                elif 'password' in error_msg.lower():
                    return {
                        'success': False,
                        'error': 'PDF is password protected. Please enter the correct Year of Birth.'
                    }
                else:
                    return {
                        'success': False,
                        'error': error_msg
                    }
            
            # Check HTTP status
            response.raise_for_status()
            
            # Success case
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
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP Error: {e.response.status_code} - {e.response.text}")
            try:
                error_data = e.response.json()
                error_message = error_data.get('message', 'API request failed')
            except:
                error_message = e.response.text[:200]
            
            return {
                'success': False,
                'error': f'API Error: {error_message}'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Aadhaar PDF verification failed: {str(e)}")
            return {
                'success': False,
                'error': f'Connection error: {str(e)}'
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
    
    def verify_pan(self, pan_number: str, name: str = '', dob: str = '') -> dict:
        """
        Verify PAN using Surepass PAN Advanced V3.

        Args:
            pan_number: 10-character PAN number
            name: Full legal name (preferably from Aadhaar) for name matching
            dob: Date of birth in YYYY-MM-DD format for DOB matching

        Returns:
            dict with verification result
        """
        logger.info(f"🔍 Verifying PAN: {pan_number}")

        if self.test_mode:
            return self._mock_pan_response(pan_number)

        try:
            url = f"{self.base_url}/api/v1/pan/pan-adv-v3"

            payload = {'id_number': pan_number.upper()}
            if name:
                payload['name'] = name
            if dob:
                payload['dob'] = dob

            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            data = result.get('data', {})

            if not result.get('success'):
                error_msg = result.get('message') or result.get('error') or 'PAN verification failed'
                logger.error(f"❌ PAN verification failed: {error_msg}")
                return {'success': False, 'error': error_msg}

            name_status = data.get('name_status', '')
            dob_status = data.get('dob_status', '')
            pan_status = data.get('pan_status', '')

            # Log any mismatches as informational — they do NOT block the flow.
            # Admin reviews the returned PAN data and decides to approve/lock, reject, or retry.
            if name_status and name_status != 'MATCHING':
                logger.warning(f"⚠️  PAN name_status={name_status} for {pan_number} — admin will review")
            if dob_status and dob_status != 'MATCHING':
                logger.warning(f"⚠️  PAN dob_status={dob_status} for {pan_number} — admin will review")

            logger.info(f"✅ PAN data received for review: {data.get('name', 'Unknown')} | name_status={name_status} | dob_status={dob_status}")
            return {
                'success': True,
                'data': {
                    'pan_number': pan_number.upper(),
                    'name': data.get('name', ''),
                    'dob': data.get('dob', ''),
                    'pan_status': pan_status,
                    'name_status': name_status,
                    'dob_status': dob_status,
                    'aadhaar_seeding_status': data.get('aadhaar_seeding_status', ''),
                },
                'message': 'PAN data received for admin review',
            }

        except requests.exceptions.HTTPError as e:
            try:
                err_body = e.response.json()
                error_msg = err_body.get('message') or err_body.get('error') or str(e)
            except Exception:
                error_msg = str(e)
            logger.error(f"❌ PAN verification HTTP error: {error_msg}")
            return {'success': False, 'error': error_msg}
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ PAN verification failed: {str(e)}")
            return {'success': False, 'error': f'PAN verification failed: {str(e)}'}

    def _mock_pan_response(self, pan_number: str) -> dict:
        """Return mock PAN response for testing (pan-adv-v3 shape)"""
        return {
            'success': True,
            'data': {
                'pan_number': pan_number.upper(),
                'name': 'RAJESH KUMAR',
                'dob': '1990-01-15',
                'pan_status': 'VALID',
                'name_status': 'MATCHING',
                'dob_status': 'MATCHING',
                'aadhaar_seeding_status': 'LINKED',
            },
            'message': 'PAN verified successfully (TEST MODE)',
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

        # ✅ Use mock when TEST_MODE = True
        if self.test_mode:
            return self._mock_bank_response(account_number, ifsc_code)

        try:
            # ✅ Use SUREPASS_BASE_URL from settings (sandbox or prod)
            base_url = (self.base_url or self.production_url).rstrip('/')
            url = f"{base_url}/api/v1/bank-verification/"

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
            result = response.json()
            logger.info(f"📦 Response data: {result}")

            if not result.get('success'):
                error_msg = result.get('message', 'Bank verification failed')
                logger.error(f"❌ Bank verification failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

            data = result.get('data', {})

            if not data.get('account_exists'):
                logger.error("❌ Bank account does not exist")
                return {
                    'success': False,
                    'error': 'Bank account does not exist or is invalid'
                }

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