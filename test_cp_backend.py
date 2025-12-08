"""
Channel Partner Backend API Test Script
=======================================
Tests all CP endpoints to ensure backend is ready for frontend integration

Requirements:
- Backend server running on http://localhost:8000
- Test users with different roles created
- At least one property in database

Run: python test_cp_backend.py
"""

import requests
import json
from datetime import datetime
import time

# ============================================
# CONFIGURATION
# ============================================

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

# Test credentials (you'll need to create these users first)
TEST_ADMIN = {
    "phone": "+919876543210",  # Change to your test admin phone
}

TEST_CUSTOMER = {
    "phone": "+919876543211",  # Change to your test customer phone
}

TEST_CP = {
    "phone": "+919876543212",  # Change to your test CP phone
}

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

# ============================================
# HELPER FUNCTIONS
# ============================================

def print_test(test_name):
    """Print test name"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}Testing: {test_name}{Colors.END}")
    print("-" * 60)

def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_warning(message):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def print_info(message):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

def send_otp(phone):
    """Send OTP to phone number"""
    url = f"{API_BASE}/auth/send-otp/"
    data = {"phone": phone}
    response = requests.post(url, json=data)
    return response

def verify_otp(phone, otp="123456"):
    """Verify OTP and get tokens"""
    url = f"{API_BASE}/auth/verify-otp/"
    data = {
        "phone": phone,
        "otp": otp
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()
    return None

def get_headers(token):
    """Get authorization headers"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

# ============================================
# TEST FUNCTIONS
# ============================================

def test_authentication():
    """Test 1: Authentication System"""
    print_test("Authentication System")
    
    # Test send OTP
    print_info("Testing send OTP...")
    response = send_otp(TEST_CUSTOMER["phone"])
    if response.status_code == 200:
        print_success("OTP sent successfully")
    else:
        print_error(f"Failed to send OTP: {response.status_code}")
        print(response.text)
        return None
    
    # Test verify OTP
    print_info("Testing verify OTP and login...")
    auth_data = verify_otp(TEST_CUSTOMER["phone"])
    if auth_data:
        print_success("Login successful")
        print_info(f"User role: {auth_data.get('user', {}).get('role', {}).get('slug', 'No role')}")
        return auth_data
    else:
        print_error("Failed to login")
        return None

def test_cp_application(customer_token):
    """Test 2: CP Application"""
    print_test("CP Application")
    
    headers = get_headers(customer_token)
    
    # Check application status first
    print_info("Checking existing CP application status...")
    response = requests.get(f"{API_BASE}/cp/application-status/", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('has_application'):
            print_warning("User already has CP application")
            print_info(f"Status: {data['data']['onboarding_status']}")
            print_info(f"CP Code: {data['data']['cp_code']}")
            return data['data']
    
    # Submit new application
    print_info("Submitting new CP application...")
    application_data = {
        "agent_type": "individual",
        "source": "website",
        "pan_number": "ABCDE1234F",
        "gst_number": "29ABCDE1234F1Z5",
        "rera_number": "RERA12345",
        "business_address": "Test Business Address, Mumbai",
        "bank_name": "Test Bank",
        "account_number": "1234567890",
        "ifsc_code": "TEST0001234",
        "account_holder_name": "Test User",
        "commission_notes": "Standard commission terms"
    }
    
    response = requests.post(
        f"{API_BASE}/cp/apply/",
        headers=headers,
        json=application_data
    )
    
    if response.status_code == 201:
        data = response.json()
        print_success("CP application submitted successfully")
        print_info(f"CP Code: {data['data']['cp_code']}")
        print_info(f"Status: {data['data']['onboarding_status']}")
        return data['data']
    elif response.status_code == 400:
        error = response.json()
        if 'already have a Channel Partner profile' in str(error):
            print_warning("User already has CP profile")
        else:
            print_error(f"Application failed: {error}")
    else:
        print_error(f"Failed to submit application: {response.status_code}")
        print(response.text)
    
    return None

def test_admin_cp_operations(admin_token):
    """Test 3: Admin CP Operations"""
    print_test("Admin CP Operations")
    
    headers = get_headers(admin_token)
    
    # List CP applications
    print_info("Fetching CP applications...")
    response = requests.get(
        f"{API_BASE}/admin/cp/applications/",
        headers=headers,
        params={"status": "pending"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Found {data['count']} pending applications")
        
        if data['count'] > 0:
            # Get first application
            cp_data = data['results'][0]
            cp_id = cp_data['id']
            print_info(f"Testing with CP ID: {cp_id}")
            
            # View application details
            print_info("Viewing application details...")
            response = requests.get(
                f"{API_BASE}/admin/cp/applications/{cp_id}/",
                headers=headers
            )
            
            if response.status_code == 200:
                print_success("Application details retrieved")
                return cp_id
            else:
                print_error(f"Failed to get details: {response.status_code}")
        else:
            print_warning("No pending applications to test with")
    else:
        print_error(f"Failed to list applications: {response.status_code}")
        print(response.text)
    
    return None

def test_cp_approval(admin_token, cp_id):
    """Test 4: CP Approval Process"""
    print_test("CP Approval Process")
    
    headers = get_headers(admin_token)
    
    # Approve CP
    print_info(f"Approving CP ID: {cp_id}...")
    approval_data = {
        "partner_tier": "bronze",
        "program_start_date": datetime.now().strftime("%Y-%m-%d"),
        "notes": "Test approval"
    }
    
    response = requests.post(
        f"{API_BASE}/admin/cp/{cp_id}/approve/",
        headers=headers,
        json=approval_data
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success("CP approved successfully")
        print_info(f"CP Code: {data['data']['cp_code']}")
        print_info(f"Tier: {data['data']['partner_tier']}")
        print_info(f"Active: {data['data']['is_active']}")
        print_info(f"Verified: {data['data']['is_verified']}")
        return data['data']
    elif response.status_code == 400:
        error = response.json()
        if 'already approved' in str(error):
            print_warning("CP already approved")
            # Get CP details
            response = requests.get(
                f"{API_BASE}/admin/cp/{cp_id}/",
                headers=headers
            )
            if response.status_code == 200:
                return response.json()
        else:
            print_error(f"Approval failed: {error}")
    else:
        print_error(f"Failed to approve CP: {response.status_code}")
        print(response.text)
    
    return None

def test_property_authorization(admin_token, cp_id):
    """Test 5: Property Authorization"""
    print_test("Property Authorization")
    
    headers = get_headers(admin_token)
    
    # Get list of properties first
    print_info("Fetching properties...")
    response = requests.get(f"{API_BASE}/properties/", headers=headers)
    
    if response.status_code == 200:
        response_data = response.json()
        properties = response_data.get('data', [])
        if len(properties) > 0:
            property_id = properties[0]['id']
            print_success(f"Found property ID: {property_id}")
            
            # Authorize property for CP
            print_info(f"Authorizing property {property_id} for CP {cp_id}...")
            auth_data = {
                "property_ids": [property_id]
            }
            
            response = requests.post(
                f"{API_BASE}/admin/cp/{cp_id}/authorize-properties/",
                headers=headers,
                json=auth_data
            )
            
            if response.status_code == 201:
                data = response.json()
                print_success("Property authorized successfully")
                print_info(f"Referral link: {data['data'][0]['referral_link']}")
                return data['data'][0]
            elif response.status_code == 200:
                print_warning("Property might already be authorized")
                return response.json()
            else:
                print_error(f"Failed to authorize: {response.status_code}")
                print(response.text)
        else:
            print_warning("No properties found in database")
    else:
        print_error(f"Failed to fetch properties: {response.status_code}")
    
    return None

def test_cp_dashboard(cp_token):
    """Test 6: CP Dashboard"""
    print_test("CP Dashboard")
    
    headers = get_headers(cp_token)
    
    # Get dashboard stats
    print_info("Fetching dashboard statistics...")
    response = requests.get(f"{API_BASE}/cp/dashboard/stats/", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print_success("Dashboard stats retrieved")
        
        # Print key stats
        cp_info = data.get('cp_info', {})
        customers = data.get('customers', {})
        investments = data.get('investments', {})
        commissions = data.get('commissions', {})
        
        print_info(f"CP Code: {cp_info.get('cp_code')}")
        print_info(f"Partner Tier: {cp_info.get('partner_tier')}")
        print_info(f"Total Customers: {customers.get('total', 0)}")
        print_info(f"Active Customers: {customers.get('active', 0)}")
        print_info(f"Total Investments: ₹{investments.get('total_value', '0.00')}")
        print_info(f"Total Commissions: ₹{commissions.get('total_earned', '0.00')}")
        
        return data
    else:
        print_error(f"Failed to fetch dashboard: {response.status_code}")
        print(response.text)
    
    return None

def test_cp_properties(cp_token):
    """Test 7: CP Authorized Properties"""
    print_test("CP Authorized Properties")
    
    headers = get_headers(cp_token)
    
    # Get authorized properties
    print_info("Fetching authorized properties...")
    response = requests.get(f"{API_BASE}/cp/properties/", headers=headers)
    
    if response.status_code == 200:
        properties = response.json()
        print_success(f"Found {len(properties)} authorized properties")
        
        if len(properties) > 0:
            prop = properties[0]
            print_info(f"Property: {prop['property_details']['name']}")
            print_info(f"Referral Link: {prop['referral_link']}")
            
            # Get specific referral link
            property_id = prop['property_details']['id']
            print_info(f"Testing referral link generation for property {property_id}...")
            
            response = requests.get(
                f"{API_BASE}/cp/properties/{property_id}/referral-link/",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success("Referral links generated")
                print_info(f"Property Link: {data['property_referral_link']}")
                print_info(f"General Link: {data['general_referral_link']}")
                return data
            else:
                print_error(f"Failed to get referral link: {response.status_code}")
        else:
            print_warning("No authorized properties found")
    else:
        print_error(f"Failed to fetch properties: {response.status_code}")
        print(response.text)
    
    return None

def test_lead_management(cp_token):
    """Test 8: Lead Management"""
    print_test("Lead Management")
    
    headers = get_headers(cp_token)
    
    # Create a lead
    print_info("Creating a test lead...")
    lead_data = {
        "customer_name": "Test Customer Lead",
        "phone": "+919999999999",
        "email": "testlead@example.com",
        "lead_status": "new",
        "notes": "Test lead from API testing",
        "lead_source": "website"
    }
    
    response = requests.post(
        f"{API_BASE}/cp/leads/",
        headers=headers,
        json=lead_data
    )
    
    if response.status_code == 201:
        data = response.json()
        lead_id = data['data']['id']
        print_success(f"Lead created successfully (ID: {lead_id})")
        
        # List leads
        print_info("Fetching all leads...")
        response = requests.get(f"{API_BASE}/cp/leads/", headers=headers)
        
        if response.status_code == 200:
            leads_data = response.json()
            print_success(f"Found {leads_data['count']} total leads")
            
            # Update lead
            print_info(f"Updating lead {lead_id}...")
            update_data = {
                "lead_status": "contacted",
                "notes": "Updated via API test"
            }
            
            response = requests.put(
                f"{API_BASE}/cp/leads/{lead_id}/",
                headers=headers,
                json=update_data
            )
            
            if response.status_code == 200:
                print_success("Lead updated successfully")
                return data['data']
            else:
                print_error(f"Failed to update lead: {response.status_code}")
        else:
            print_error(f"Failed to list leads: {response.status_code}")
    else:
        print_error(f"Failed to create lead: {response.status_code}")
        print(response.text)
    
    return None

def test_invite_system(cp_token):
    """Test 9: Invite System"""
    print_test("Invite System")
    
    headers = get_headers(cp_token)
    
    # Create an invite
    print_info("Creating a test invite...")
    invite_data = {
        "phone": "+919888888888",
        "email": "testinvite@example.com",
        "name": "Test Invite User",
        "message": "Join AssetKart through my referral!"
    }
    
    response = requests.post(
        f"{API_BASE}/cp/invites/",
        headers=headers,
        json=invite_data
    )
    
    if response.status_code == 201:
        data = response.json()
        invite_code = data['data']['invite_code']
        invite_link = data['invite_link']
        print_success(f"Invite created successfully")
        print_info(f"Invite Code: {invite_code}")
        print_info(f"Invite Link: {invite_link}")
        
        # List invites
        print_info("Fetching all invites...")
        response = requests.get(f"{API_BASE}/cp/invites/", headers=headers)
        
        if response.status_code == 200:
            invites_data = response.json()
            print_success(f"Found {invites_data['count']} total invites")
            return data['data']
        else:
            print_error(f"Failed to list invites: {response.status_code}")
    else:
        print_error(f"Failed to create invite: {response.status_code}")
        print(response.text)
    
    return None

def test_customer_relationship(cp_token):
    """Test 10: CP-Customer Relationship"""
    print_test("CP-Customer Relationship")
    
    headers = get_headers(cp_token)
    
    # Get customers
    print_info("Fetching linked customers...")
    response = requests.get(f"{API_BASE}/cp/customers/", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Found {data['count']} linked customers")
        
        if data['count'] > 0:
            customer = data['results'][0]
            print_info(f"Customer: {customer['customer_details']['full_name']}")
            print_info(f"Referral Date: {customer['referral_date']}")
            print_info(f"Expiry Date: {customer['expiry_date']}")
            print_info(f"Days Remaining: {customer['days_remaining']}")
            print_info(f"Active: {customer['is_active']}")
            print_info(f"Expired: {customer['is_expired']}")
        else:
            print_warning("No customers linked yet")
        
        return data
    else:
        print_error(f"Failed to fetch customers: {response.status_code}")
        print(response.text)
    
    return None

def test_role_detection(token):
    """Test 11: Role Detection"""
    print_test("Role Detection and Permissions")
    
    headers = get_headers(token)
    
    # Get current user
    print_info("Fetching current user details...")
    response = requests.get(f"{API_BASE}/auth/me/", headers=headers)
    
    if response.status_code == 200:
        user = response.json()
        role = user.get('role', {})
        
        print_success("User details retrieved")
        print_info(f"Username: {user.get('username')}")
        print_info(f"Role: {role.get('display_name', 'No role')}")
        print_info(f"Role Slug: {role.get('slug', 'No role')}")
        print_info(f"Is Active: {user.get('is_active')}")
        
        # Check if role matches expected
        if role.get('slug') == 'channel_partner':
            print_success("✓ Role is correctly set to 'channel_partner'")
        else:
            print_warning(f"⚠ Role is '{role.get('slug')}', expected 'channel_partner'")
        
        return user
    else:
        print_error(f"Failed to fetch user: {response.status_code}")
        print(response.text)
    
    return None

# ============================================
# MAIN TEST RUNNER
# ============================================

def run_all_tests():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print("CHANNEL PARTNER BACKEND API TEST SUITE")
    print(f"{'='*60}{Colors.END}\n")
    print(f"Base URL: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "passed": 0,
        "failed": 0,
        "warnings": 0
    }
    
    # Store tokens
    admin_token = None
    customer_token = None
    cp_token = None
    cp_id = None
    
    try:
        # Test 1: Authentication
        print_info("\nPlease ensure OTP test mode is enabled in settings")
        print_info("OTP will be '123456' for all test phone numbers\n")
        time.sleep(2)
        
        auth_data = test_authentication()
        if auth_data:
            customer_token = auth_data['access']
            results["passed"] += 1
        else:
            results["failed"] += 1
            print_error("Authentication failed. Cannot proceed with further tests.")
            return results
        
        # Test 2: CP Application
        cp_data = test_cp_application(customer_token)
        if cp_data:
            cp_id = cp_data['id']
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        # For remaining tests, we need admin and CP tokens
        print_info("\n" + "="*60)
        print_info("ADMIN TESTS - Login with admin account")
        print_info("="*60)
        print_warning("Please login with admin credentials:")
        
        # Get admin token
        print_info("Sending OTP to admin...")
        send_otp(TEST_ADMIN["phone"])
        admin_auth = verify_otp(TEST_ADMIN["phone"])
        
        if admin_auth:
            admin_token = admin_auth['access']
            print_success("Admin logged in successfully")
            results["passed"] += 1
            
            # Test 3: Admin CP Operations
            if cp_id or test_admin_cp_operations(admin_token):
                results["passed"] += 1
                
                # Test 4: CP Approval
                if cp_id:
                    approved_cp = test_cp_approval(admin_token, cp_id)
                    if approved_cp:
                        results["passed"] += 1
                        
                        # Test 5: Property Authorization
                        if test_property_authorization(admin_token, cp_id):
                            results["passed"] += 1
                        else:
                            results["failed"] += 1
                    else:
                        results["failed"] += 1
                else:
                    print_warning("No CP ID available for approval test")
                    results["warnings"] += 1
            else:
                results["failed"] += 1
        else:
            print_error("Admin login failed")
            results["failed"] += 1
        
        # CP-specific tests
        print_info("\n" + "="*60)
        print_info("CP TESTS - Login with CP account")
        print_info("="*60)
        
        # Get CP token (use the same phone that applied)
        print_info("Logging in as CP...")
        send_otp(TEST_CUSTOMER["phone"])  # Send OTP first
        cp_auth = verify_otp(TEST_CUSTOMER["phone"])
        
        if cp_auth:
            cp_token = cp_auth['access']
            
            # Check role
            role_slug = cp_auth.get('user', {}).get('role', {}).get('slug')
            if role_slug == 'channel_partner':
                print_success("CP role verified")
                results["passed"] += 1
                
                # Test 6: CP Dashboard
                if test_cp_dashboard(cp_token):
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                
                # Test 7: CP Properties
                if test_cp_properties(cp_token):
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                
                # Test 8: Lead Management
                if test_lead_management(cp_token):
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                
                # Test 9: Invite System
                if test_invite_system(cp_token):
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                
                # Test 10: Customer Relationship
                if test_customer_relationship(cp_token):
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                
                # Test 11: Role Detection
                if test_role_detection(cp_token):
                    results["passed"] += 1
                else:
                    results["failed"] += 1
            else:
                print_error(f"Role is '{role_slug}', expected 'channel_partner'")
                print_error("CP approval might not have updated role correctly")
                results["failed"] += 1
        else:
            print_error("CP login failed")
            results["failed"] += 1
        
    except Exception as e:
        print_error(f"Test suite error: {str(e)}")
        results["failed"] += 1
    
    # Print summary
    print(f"\n{Colors.BOLD}{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}{Colors.END}\n")
    
    total_tests = results["passed"] + results["failed"]
    print(f"{Colors.GREEN}Passed: {results['passed']}/{total_tests}{Colors.END}")
    print(f"{Colors.RED}Failed: {results['failed']}/{total_tests}{Colors.END}")
    if results["warnings"] > 0:
        print(f"{Colors.YELLOW}Warnings: {results['warnings']}{Colors.END}")
    
    if results["failed"] == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All tests passed! Backend is ready for frontend integration.{Colors.END}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Some tests failed. Please fix backend issues before proceeding.{Colors.END}")
    
    return results

if __name__ == "__main__":
    print(f"\n{Colors.YELLOW}{'='*60}")
    print("IMPORTANT: Before running this script")
    print(f"{'='*60}{Colors.END}")
    print("\n1. Make sure backend server is running on http://localhost:8000")
    print("2. Update TEST_ADMIN, TEST_CUSTOMER phone numbers in the script")
    print("3. Ensure OTP test mode is enabled (OTP will be '123456')")
    print("4. Have at least one property created in the database")
    print("5. Have admin user with proper role assigned")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    
    try:
        input()
        run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test cancelled by user{Colors.END}")
