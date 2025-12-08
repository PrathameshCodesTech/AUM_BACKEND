"""
Quick Database Setup for CP Testing
====================================
Run this in Django shell: python manage.py shell < setup_test_data.py

Creates:
- Admin user
- Customer user
- Required roles
- Test property
"""

from accounts.models import User, Role
from properties.models import Property
from compliance.models import KYC
from decimal import Decimal
from django.utils import timezone

print("\n" + "="*60)
print("Setting up test data for CP Backend Testing")
print("="*60 + "\n")

# ============================================
# 1. CREATE ROLES
# ============================================
print("Creating roles...")

# Admin Role
admin_role, created = Role.objects.get_or_create(
    slug='admin',
    defaults={
        'name': 'admin',
        'display_name': 'Admin',
        'level': 100,
        'is_system': True,
        'is_active': True,
        'color': '#dc3545'
    }
)
if created:
    print("✓ Admin role created")
else:
    print("✓ Admin role already exists")

# Channel Partner Role
cp_role, created = Role.objects.get_or_create(
    slug='channel_partner',
    defaults={
        'name': 'channel_partner',
        'display_name': 'Channel Partner',
        'level': 50,
        'is_system': True,
        'is_active': True,
        'color': '#667eea'
    }
)
if created:
    print("✓ Channel Partner role created")
else:
    print("✓ Channel Partner role already exists")

# Customer Role
customer_role, created = Role.objects.get_or_create(
    slug='customer',
    defaults={
        'name': 'customer',
        'display_name': 'Customer',
        'level': 10,
        'is_system': True,
        'is_active': True,
        'color': '#28a745'
    }
)
if created:
    print("✓ Customer role created")
else:
    print("✓ Customer role already exists")

# Developer Role
dev_role, created = Role.objects.get_or_create(
    slug='developer',
    defaults={
        'name': 'developer',
        'display_name': 'Developer',
        'level': 75,
        'is_system': True,
        'is_active': True,
        'color': '#ffc107'
    }
)
if created:
    print("✓ Developer role created")
else:
    print("✓ Developer role already exists")

# ============================================
# 2. CREATE ADMIN USER
# ============================================
print("\nCreating admin user...")

admin_phone = '+919876543210'
admin_user, created = User.objects.get_or_create(
    phone=admin_phone,
    defaults={
        'username': 'admin_test',
        'email': 'admin@assetkart.com',
        'first_name': 'Admin',
        'last_name': 'User',
        'role': admin_role,
        'phone_verified': True,
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
        'is_admin': True,
        'profile_completed': True,
        'kyc_status': 'verified'
    }
)

if created:
    admin_user.set_password('admin123')
    admin_user.save()
    print(f"✓ Admin user created")
    print(f"  Phone: {admin_phone}")
    print(f"  Password: admin123")
else:
    # Update role if exists
    admin_user.role = admin_role
    admin_user.phone_verified = True
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.is_admin = True
    admin_user.save()
    print(f"✓ Admin user already exists (updated role)")
    print(f"  Phone: {admin_phone}")

# ============================================
# 3. CREATE TEST CUSTOMER USER
# ============================================
print("\nCreating test customer user...")

customer_phone = '+919876543211'
customer_user, created = User.objects.get_or_create(
    phone=customer_phone,
    defaults={
        'username': 'customer_test',
        'email': 'customer@assetkart.com',
        'first_name': 'Test',
        'last_name': 'Customer',
        'role': customer_role,
        'phone_verified': True,
        'is_active': True,
        'profile_completed': True,
        'kyc_status': 'verified'  # IMPORTANT: Must be verified for CP application
    }
)

if created:
    customer_user.set_password('customer123')
    customer_user.save()
    print(f"✓ Customer user created")
    print(f"  Phone: {customer_phone}")
    print(f"  Password: customer123")
    print(f"  KYC Status: verified")
else:
    # Update to ensure KYC verified
    customer_user.role = customer_role
    customer_user.phone_verified = True
    customer_user.kyc_status = 'verified'
    customer_user.profile_completed = True
    customer_user.save()
    print(f"✓ Customer user already exists (updated)")
    print(f"  Phone: {customer_phone}")
    print(f"  KYC Status: {customer_user.kyc_status}")

# ============================================
# 4. CREATE KYC RECORD FOR CUSTOMER
# ============================================
print("\nCreating KYC record for customer...")

kyc, created = KYC.objects.get_or_create(
    user=customer_user,
    defaults={
        'status': 'verified',
        'aadhaar_verified': True,
        'pan_verified': True,
        'bank_verified': True,
        'aadhaar_number': '123456789012',
        'pan_number': 'ABCDE1234F',
        'account_number': '1234567890',
        'ifsc_code': 'TEST0001234',
        'account_holder_name': 'Test Customer',
        'verified_at': timezone.now(),
    }
)

if created:
    print("✓ KYC record created for customer")
else:
    print("✓ KYC record already exists for customer")

# ============================================
# 5. CREATE TEST PROPERTY
# ============================================
# ============================================
# 5. CREATE TEST PROPERTY
# ============================================
print("\nCreating test property...")

# Delete existing property if it exists
Property.objects.filter(slug='test-property-mumbai').delete()

# Create fresh property
test_property = Property.objects.create(
    name='Test Property Mumbai',
    slug='test-property-mumbai',
    description='Test property for CP backend testing',
    property_type='equity',
    price_per_unit=Decimal('1000000.00'),
    total_units=100,
    available_units=100,
    minimum_investment=Decimal('100000.00'),
    expected_return_percentage=Decimal('12.00'),
    gross_yield=Decimal('8.00'),
    status='live',
    is_published=True,  # Must be True
    funding_start_date=timezone.now().date(),
    funding_end_date=timezone.now().date(),
    target_amount=Decimal('100000000.00'),
    project_duration=36,
    city='Mumbai',
    state='Maharashtra',
    country='India',
    pincode='400001',
    address='Andheri, Mumbai',
    total_area=Decimal('10000.00'),
    builder_name='Test Builder',
    developer=admin_user,
)

print(f"✓ Test property created")
print(f"  ID: {test_property.id}")
print(f"  Name: {test_property.name}")
print(f"  Status: {test_property.status}")
print(f"  Published: {test_property.is_published}")


if created:
    print(f"✓ Test property created")
    print(f"  ID: {test_property.id}")
    print(f"  Name: {test_property.name}")
    print(f"  Price per unit: ₹{test_property.price_per_unit}")
else:
    print(f"✓ Test property updated")
    print(f"  ID: {test_property.id}")

# ============================================
# 6. SUMMARY
# ============================================
print("\n" + "="*60)
print("Setup Complete!")
print("="*60)

print("\nTest Credentials:")
print("-" * 40)
print(f"Admin User:")
print(f"  Phone: {admin_phone}")
print(f"  OTP (test mode): 123456")
print(f"  Role: {admin_user.role.display_name if admin_user.role else 'None'}")

print(f"\nCustomer User (will become CP):")
print(f"  Phone: {customer_phone}")
print(f"  OTP (test mode): 123456")
print(f"  Role: {customer_user.role.display_name if customer_user.role else 'None'}")
print(f"  KYC Status: {customer_user.kyc_status}")

print(f"\nTest Property:")
print(f"  ID: {test_property.id}")
print(f"  Slug: {test_property.slug}")
print(f"  Name: {test_property.name}")

print("\nNext Steps:")
print("-" * 40)
print("1. Ensure backend is running: python manage.py runserver")
print("2. Set ROUTE_MOBILE_TEST_MODE = True in settings.py")
print("3. Update phone numbers in test_cp_backend.py")
print("4. Run: python test_cp_backend.py")

print("\n" + "="*60 + "\n")
