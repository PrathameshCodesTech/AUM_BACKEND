# partners/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import (
    ChannelPartner,
    CPCustomerRelation,
    CPPropertyAuthorization,
    CPLead,
    CPInvite,
    CPDocument,
    CommissionRule,
    CPCommissionRule
)
from accounts.models import User
from properties.models import Property
from decimal import Decimal

# ============================================
# CHANNEL PARTNER SERIALIZERS
# ============================================

class CPApplicationSerializer(serializers.ModelSerializer):
    """Serializer for CP application form"""
    
    # User fields (from related user)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    
    class Meta:
        model = ChannelPartner
        fields = [
            'id',
            # User fields
            'first_name',
            'last_name',
            'email',
            'phone',
            # CP Identity
            'agent_type',
            'source',
            'company_name',
            'pan_number',
            'gst_number',
            'rera_number',
            'business_address',
            # Bank Details
            'bank_name',
            'account_number',
            'ifsc_code',
            'account_holder_name',
            # Commission
            'commission_notes',
            # Parent CP (optional)
            'parent_cp',
            # Status (read-only)
            'cp_code',
            'onboarding_status',
            'is_verified',
            'is_active',
            'created_at',
        ]
        read_only_fields = [
            'cp_code',
            'onboarding_status',
            'is_verified',
            'is_active',
            'created_at',
            'first_name',
            'last_name',
            'email',
            'phone',
        ]
    
    def validate_pan_number(self, value):
        """Validate PAN format"""
        if value and len(value) != 10:
            raise serializers.ValidationError("PAN must be 10 characters")
        return value.upper() if value else value
    
    def validate_gst_number(self, value):
        """Validate GST format"""
        if value and len(value) != 15:
            raise serializers.ValidationError("GST must be 15 characters")
        return value.upper() if value else value
    
    def validate(self, data):
        """Cross-field validation"""
        # If company, require company_name and GST
        if data.get('agent_type') == 'company':
            if not data.get('company_name'):
                raise serializers.ValidationError({
                    'company_name': 'Company name required for company type'
                })
        
        return data


class CPProfileSerializer(serializers.ModelSerializer):
    """Detailed CP profile serializer"""
    
    user_details = serializers.SerializerMethodField()
    hierarchy_level = serializers.SerializerMethodField()
    total_customers = serializers.SerializerMethodField()
    total_active_customers = serializers.SerializerMethodField()
    program_is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = ChannelPartner
        fields = [
            'id',
            'cp_code',
            'user_details',
            # Identity
            'agent_type',
            'source',
            'company_name',
            'pan_number',
            'gst_number',
            'rera_number',
            'business_address',
            # Bank
            'bank_name',
            'account_number',
            'ifsc_code',
            'account_holder_name',
            # Program
            'partner_tier',
            'program_start_date',
            'program_end_date',
            'program_is_active',
            # Compliance
            'regulatory_compliance_approved',
            'onboarding_status',
            'dedicated_support_contact',
            'technical_setup_notes',
            # Targets
            'monthly_target',
            'quarterly_target',
            'yearly_target',
            'annual_revenue_target',
            'q1_performance',
            'q2_performance',
            'q3_performance',
            'q4_performance',
            # Commission
            'commission_notes',
            # Status
            'is_active',
            'is_verified',
            'verified_at',
            # Hierarchy
            'parent_cp',
            'hierarchy_level',
            # Stats
            'total_customers',
            'total_active_customers',
            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'cp_code',
            'is_verified',
            'verified_at',
            'created_at',
            'updated_at',
        ]
    
    def get_user_details(self, obj):
        """Get user information"""
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'email': obj.user.email,
            'phone': obj.user.phone,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'full_name': obj.user.get_full_name(),
        }
    
    def get_hierarchy_level(self, obj):
        """Get CP hierarchy level"""
        return obj.get_hierarchy_level()
    
    def get_total_customers(self, obj):
        """Total customers count"""
        return obj.customers.count()
    
    def get_total_active_customers(self, obj):
        """Active customers count"""
        return obj.customers.filter(is_active=True, is_expired=False).count()
    
    def get_program_is_active(self, obj):
        """Check if program is active"""
        return obj.is_program_active()
    
class CPListSerializer(serializers.ModelSerializer):
    """Lightweight CP list serializer"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    total_customers = serializers.SerializerMethodField()
    total_invested = serializers.SerializerMethodField()
    total_commission = serializers.SerializerMethodField()
    
    class Meta:
        model = ChannelPartner
        fields = [
            'id',
            'cp_code',
            'user_name',
            'user_email',
            'agent_type',
            'company_name',
            'partner_tier',
            'onboarding_status',
            'is_verified',
            'is_active',
            'total_customers',
            'total_invested',
            'total_commission',
            'created_at',
        ]
    
    def get_total_customers(self, obj):
        return obj.customers.filter(is_active=True, is_expired=False).count()
    
    def get_total_invested(self, obj):
        from investments.models import Investment
        from django.db.models import Sum
        
        total = Investment.objects.filter(
            referred_by_cp=obj,
            status__in=['approved', 'active', 'completed']
        ).aggregate(total=Sum('amount'))['total']
        
        return str(total or Decimal('0.00'))
    
    def get_total_commission(self, obj):
        from commissions.models import Commission
        from django.db.models import Sum
        
        total = Commission.objects.filter(
            cp=obj,
            status__in=['approved', 'paid']
        ).aggregate(total=Sum('commission_amount'))['total']
        
        return str(total or Decimal('0.00'))
# ============================================
# CP CUSTOMER RELATION SERIALIZERS
# ============================================

class CPCustomerRelationSerializer(serializers.ModelSerializer):
    """CP-Customer relationship serializer"""
    
    customer_details = serializers.SerializerMethodField()
    cp_details = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = CPCustomerRelation
        fields = [
            'id',
            'cp',
            'customer',
            'cp_details',
            'customer_details',
            'referral_code',
            'referral_date',
            'validity_days',
            'expiry_date',
            'is_expired',
            'is_active',
            'days_remaining',
            'created_at',
        ]
        read_only_fields = [
            'referral_date',
            'expiry_date',
            'is_expired',
            'created_at',
        ]
    
    def get_customer_details(self, obj):
        """Get customer info"""
        return {
            'id': obj.customer.id,
            'username': obj.customer.username,
            'email': obj.customer.email,
            'phone': obj.customer.phone,
            'full_name': obj.customer.get_full_name(),
        }
    
    def get_cp_details(self, obj):
        """Get CP info"""
        return {
            'id': obj.cp.id,
            'cp_code': obj.cp.cp_code,
            'name': obj.cp.user.get_full_name(),
        }
    
    def get_days_remaining(self, obj):
        """Calculate days remaining"""
        if obj.is_expired:
            return 0
        days = (obj.expiry_date - timezone.now()).days
        return max(0, days)


# ============================================
# PROPERTY AUTHORIZATION SERIALIZERS
# ============================================

class CPPropertyAuthorizationSerializer(serializers.ModelSerializer):
    """Property authorization serializer"""
    
    property_details = serializers.SerializerMethodField()
    cp_details = serializers.SerializerMethodField()
    
    class Meta:
        model = CPPropertyAuthorization
        fields = [
            'id',
            'cp',
            'property',
            'cp_details',
            'property_details',
            'is_authorized',
            'approval_status',
            'referral_link',
            'custom_brochure',
            'notes',
            'authorized_by',
            'authorized_at',
            'created_at',
        ]
        read_only_fields = [
            'referral_link',
            'authorized_by',
            'authorized_at',
            'created_at',
        ]
    
    def get_property_details(self, obj):
        """Get property info"""
        return {
            'id': obj.property.id,
            'name': obj.property.name,
            'slug': obj.property.slug,  # 👈 CHANGED from property_code to slug
            'location': f"{obj.property.city}, {obj.property.state}",  # 👈 FIXED
            'price_per_unit': str(obj.property.price_per_unit),
            'total_units': obj.property.total_units,
            'available_units': obj.property.available_units,
        }
    
    def get_cp_details(self, obj):
        """Get CP info"""
        return {
            'id': obj.cp.id,
            'cp_code': obj.cp.cp_code,
            'name': obj.cp.user.get_full_name(),
        }


class AuthorizePropertiesSerializer(serializers.Serializer):
    """Serializer for bulk property authorization"""
    
    property_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    
    def validate_property_ids(self, value):
        """Validate property IDs exist"""
        valid_ids = Property.objects.filter(id__in=value).values_list('id', flat=True)
        invalid_ids = set(value) - set(valid_ids)
        
        if invalid_ids:
            raise serializers.ValidationError(
                f"Invalid property IDs: {invalid_ids}"
            )
        
        return value


# ============================================
# LEAD MANAGEMENT SERIALIZERS
# ============================================

class CPLeadSerializer(serializers.ModelSerializer):
    """Lead management serializer"""
    
    property_details = serializers.SerializerMethodField()
    converted_customer_details = serializers.SerializerMethodField()
    
    class Meta:
        model = CPLead
        fields = [
            'id',
            'cp',
            'customer_name',
            'phone',
            'email',
            'interested_property',
            'property_details',
            'lead_status',
            'notes',
            'next_follow_up_date',
            'converted_customer',
            'converted_customer_details',
            'converted_at',
            'lead_source',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'cp',
            'converted_customer',
            'converted_at',
            'created_at',
            'updated_at',
        ]
    
    def get_property_details(self, obj):
        """Get property info"""
        if obj.interested_property:
            return {
                'id': obj.interested_property.id,
                'name': obj.interested_property.name,
                'location': obj.interested_property.location,
            }
        return None
    
    def get_converted_customer_details(self, obj):
        """Get converted customer info"""
        if obj.converted_customer:
            return {
                'id': obj.converted_customer.id,
                'username': obj.converted_customer.username,
                'email': obj.converted_customer.email,
            }
        return None


class CPLeadCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating leads"""
    
    class Meta:
        model = CPLead
        fields = [
            'customer_name',
            'phone',
            'email',
            'interested_property',
            'lead_status',
            'notes',
            'next_follow_up_date',
            'lead_source',
        ]
    
    def validate_phone(self, value):
        """Validate phone format"""
        if not value.startswith('+'):
            raise serializers.ValidationError("Phone must start with country code (+91)")
        return value


# ============================================
# INVITE SYSTEM SERIALIZERS
# ============================================

class CPInviteSerializer(serializers.ModelSerializer):
    """CP invite serializer"""
    
    used_by_details = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = CPInvite
        fields = [
            'id',
            'cp',
            'invite_code',
            'phone',
            'email',
            'name',
            'message',
            'is_used',
            'used_by',
            'used_by_details',
            'used_at',
            'expiry_date',
            'is_expired',
            'is_valid',
            'created_at',
        ]
        read_only_fields = [
            'cp',
            'invite_code',
            'is_used',
            'used_by',
            'used_at',
            'is_expired',
            'created_at',
        ]
    
    def get_used_by_details(self, obj):
        """Get user who used invite"""
        if obj.used_by:
            return {
                'id': obj.used_by.id,
                'username': obj.used_by.username,
                'email': obj.used_by.email,
            }
        return None
    
    def get_is_valid(self, obj):
        """Check if invite is still valid"""
        return not obj.is_used and not obj.is_expired and obj.expiry_date > timezone.now()


class CPInviteCreateSerializer(serializers.Serializer):
    """Serializer for creating invites (single or bulk)"""
    
    # For single invite (existing)
    phone = serializers.CharField(max_length=15, required=False)
    email = serializers.EmailField(required=False)
    name = serializers.CharField(max_length=255, required=False)
    message = serializers.CharField(required=False)
    
    # For bulk invites (new)
    invites = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="List of invites for bulk creation"
    )
    
    def validate_invites(self, value):
        """Validate bulk invites format"""
        if not value:
            return value
            
        for invite in value:
            if not invite.get('phone'):
                raise serializers.ValidationError("Each invite must have a phone number")
        
        return value



# ============================================
# DOCUMENT SERIALIZERS
# ============================================

class CPDocumentSerializer(serializers.ModelSerializer):
    """CP document serializer"""
    
    verified_by_details = serializers.SerializerMethodField()
    
    class Meta:
        model = CPDocument
        fields = [
            'id',
            'cp',
            'document_type',
            'description',
            'file',
            'status',
            'verified_by',
            'verified_by_details',
            'verified_at',
            'rejection_reason',
            'created_at',
        ]
        read_only_fields = [
            'cp',
            'status',
            'verified_by',
            'verified_at',
            'rejection_reason',
            'created_at',
        ]
    
    def get_verified_by_details(self, obj):
        """Get verifier info"""
        if obj.verified_by:
            return {
                'id': obj.verified_by.id,
                'username': obj.verified_by.username,
                'full_name': obj.verified_by.get_full_name(),
            }
        return None


class DocumentVerifySerializer(serializers.Serializer):
    """Serializer for document verification"""
    
    status = serializers.ChoiceField(choices=['approved', 'rejected'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate rejection reason"""
        if data['status'] == 'rejected' and not data.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason required when rejecting'
            })
        return data


# ============================================
# COMMISSION SERIALIZERS
# ============================================

class CommissionRuleSerializer(serializers.ModelSerializer):
    """Commission rule serializer"""
    
    class Meta:
        model = CommissionRule
        fields = [
            'id',
            'name',
            'description',
            'commission_type',
            'percentage',
            'tiers',
            'override_percentage',
            'is_default',
            'is_active',
            'effective_from',
            'effective_to',
        ]

class CPCommissionRuleSerializer(serializers.ModelSerializer):
    """CP commission rule assignment serializer"""
    
    commission_rule_details = serializers.SerializerMethodField()
    property_details = serializers.SerializerMethodField()
    
    class Meta:
        model = CPCommissionRule
        fields = [
            'id',
            'cp',
            'commission_rule',
            'commission_rule_details',
            'property',
            'property_details',
            'assigned_by',
            'assigned_at',
        ]
        read_only_fields = [
            'assigned_by',
            'assigned_at',
        ]
    
    def get_commission_rule_details(self, obj):
        """Get commission rule info"""
        return {
            'id': obj.commission_rule.id,
            'name': obj.commission_rule.name,
            'commission_type': obj.commission_rule.commission_type,
            'percentage': str(obj.commission_rule.percentage),
        }
    
    def get_property_details(self, obj):
        """Get property info"""
        if obj.property:
            return {
                'id': obj.property.id,
                'name': obj.property.name,
                'slug': obj.property.slug,  # 👈 CHANGED from property_code to slug
            }
        return None


class AssignCommissionRuleSerializer(serializers.Serializer):
    """Serializer for assigning commission rule"""
    
    commission_rule_id = serializers.IntegerField()
    property_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_commission_rule_id(self, value):
        """Validate commission rule exists"""
        if not CommissionRule.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid or inactive commission rule")
        return value
    
    def validate_property_id(self, value):
        """Validate property exists"""
        if value and not Property.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid property")
        return value


# ============================================
# DASHBOARD SERIALIZERS
# ============================================

class CPDashboardStatsSerializer(serializers.Serializer):
    """CP dashboard statistics"""
    
    cp_info = serializers.DictField()
    customers = serializers.DictField()
    investments = serializers.DictField()
    commissions = serializers.DictField()
    leads = serializers.DictField()
    targets = serializers.DictField()
    performance = serializers.DictField()


# ============================================
# ADMIN APPROVAL SERIALIZERS
# ============================================

class CPApprovalSerializer(serializers.Serializer):
    """Serializer for CP approval"""
    
    partner_tier = serializers.ChoiceField(
        choices=['bronze', 'silver', 'gold', 'platinum'],
        default='bronze'
    )
    program_start_date = serializers.DateField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class CPRejectionSerializer(serializers.Serializer):
    """Serializer for CP rejection"""
    rejection_reason = serializers.CharField(required=True)


# ============================================
# ADMIN CP CREATION SERIALIZER (NEW)
# ============================================

class AdminCreateCPSerializer(serializers.ModelSerializer):
    """
    Admin manually creates CP on behalf
    Uses ChannelPartner model + creates user account
    """
    
    # ============================================
    # NESTED USER FIELDS (Write-Only)
    # ============================================
    first_name = serializers.CharField(max_length=150, write_only=True, required=True)
    last_name = serializers.CharField(max_length=150, write_only=True, required=True)
    email = serializers.EmailField(write_only=True, required=True)
    phone = serializers.CharField(max_length=15, write_only=True, required=True)
    password = serializers.CharField(
        write_only=True, 
        required=False, 
        allow_blank=True,
        help_text="Auto-generated if not provided"
    )
    
    # ============================================
    # PROPERTY AUTHORIZATION (Optional)
    # ============================================
    property_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True,
        help_text="List of property IDs to authorize"
    )
    
    # ============================================
    # AUTO-APPROVE FLAG
    # ============================================
    auto_approve = serializers.BooleanField(
        write_only=True,
        default=True,
        help_text="Auto-approve and activate CP"
    )
    
    class Meta:
        model = ChannelPartner
        fields = [
            # User fields (write-only)
            'first_name', 'last_name', 'email', 'phone', 'password',
            
            # CP Identity
            'agent_type', 'source', 'company_name',
            'pan_number', 'gst_number', 'rera_number',
            'business_address',
            
            # Program Enrolment
            'partner_tier', 'program_start_date', 'program_end_date',
            
            # Compliance
            'regulatory_compliance_approved',
            
            # Operational Setup
            'dedicated_support_contact', 'technical_setup_notes',
            
            # Targets & Performance
            'monthly_target', 'quarterly_target', 'yearly_target',
            
            # Bank Details
            'bank_name', 'account_number', 'ifsc_code', 'account_holder_name',
            
            # Commission
            'commission_notes',
            
            # Property Authorization
            'property_ids',
            
            # Auto-approve
            'auto_approve',
            
            # Read-only (auto-generated)
            'id', 'cp_code', 'user', 'onboarding_status', 
            'is_verified', 'is_active', 'created_at',
        ]
        read_only_fields = [
            'id', 'cp_code', 'user', 'onboarding_status', 
            'is_verified', 'is_active', 'created_at'
        ]
    
    def validate_phone(self, value):
        """Validate and normalize phone number"""
        import re
        
        # Remove any spaces, dashes, or other non-digit characters except +
        phone = re.sub(r'[^\d+]', '', value.strip())
        
        # Remove + temporarily for digit counting
        digits_only = phone.replace('+', '')
        
        # Handle different formats
        if len(digits_only) == 10:
            phone = f'+91{digits_only}'
        elif len(digits_only) == 12 and digits_only.startswith('91'):
            phone = f'+{digits_only}'
        elif len(digits_only) == 11 and digits_only.startswith('0'):
            phone = f'+91{digits_only[1:]}'
        elif not phone.startswith('+91'):
            phone = f'+91{phone}'
        
        # Final validation
        if not re.match(r'^\+91\d{10}$', phone):
            raise serializers.ValidationError(
                "Phone must be in format +91XXXXXXXXXX (10 digits)"
            )
        
        # Check if phone already exists
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError(
                "Phone number already registered"
            )
        
        return phone
    
    def validate_email(self, value):
        """Check if email already exists"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value
    
    def validate_pan_number(self, value):
        """Validate PAN format"""
        if value:
            value = value.strip().upper()
            if len(value) != 10:
                raise serializers.ValidationError("PAN must be 10 characters")
            # Basic PAN format: ABCDE1234F
            import re
            if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', value):
                raise serializers.ValidationError("Invalid PAN format")
        return value
    
    def validate_gst_number(self, value):
        """Validate GST format"""
        if value:
            value = value.strip().upper()
            if len(value) != 15:
                raise serializers.ValidationError("GST must be 15 characters")
        return value
    
    def validate_ifsc_code(self, value):
        """Validate IFSC format"""
        if value:
            value = value.strip().upper()
            if len(value) != 11:
                raise serializers.ValidationError("IFSC must be 11 characters")
            # Basic IFSC format: ABCD0123456
            import re
            if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', value):
                raise serializers.ValidationError("Invalid IFSC format")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # If company type, require company name and GST
        if data.get('agent_type') == 'company':
            if not data.get('company_name'):
                raise serializers.ValidationError({
                    'company_name': 'Company name required for company type'
                })
        
        # If bank details provided, all fields required
        bank_fields = ['bank_name', 'account_number', 'ifsc_code', 'account_holder_name']
        bank_values = [data.get(field) for field in bank_fields]
        
        if any(bank_values):  # If any bank field is filled
            if not all(bank_values):  # All must be filled
                raise serializers.ValidationError({
                    'bank_details': 'All bank details required if providing bank information'
                })
        
        return data