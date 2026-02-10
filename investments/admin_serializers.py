"""
Investment Admin Serializers
For admin dashboard investment management
"""
from rest_framework import serializers
from .models import Investment
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminInvestmentListSerializer(serializers.ModelSerializer):
    """Serializer for listing investments in admin dashboard"""
    customer_name = serializers.CharField(source='customer.username')
    customer_phone = serializers.CharField(source='customer.phone')
    customer_email = serializers.CharField(source='customer.email')
    property_name = serializers.CharField(source='property.name')
    property_address = serializers.CharField(source='property.address')  # 👈 Changed to address

        # 🆕 Add payment summary fields
    paid_amount = serializers.DecimalField(
        source='amount',
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    total_investment_amount = serializers.DecimalField(
        source='minimum_required_amount',
        max_digits=15,
        decimal_places=2,
        read_only=True
    )

    
    class Meta:
        model = Investment
        fields = [
            'id',
            'investment_id',
            'customer',
            'customer_name',
            'customer_phone',
            'customer_email',
            'property',
            'property_name',
            'property_address',
            'amount',
            'units_purchased',
            'price_per_unit_at_investment',
            'status',
            'investment_date',
            'approved_at',
            'payment_completed',
            'payment_completed_at',
            'expected_return_amount',
            'actual_return_amount',
            'lock_in_end_date',
            'maturity_date',
            'created_at',

               # 🆕 Add these
            'is_partial_payment',
            'paid_amount',
            'due_amount',
            'total_investment_amount',
            'payment_due_date',
        ]


class AdminInvestmentDetailSerializer(serializers.ModelSerializer):
    """Detailed investment info for admin"""
    customer_details = serializers.SerializerMethodField()
    property_details = serializers.SerializerMethodField()
    transaction_details = serializers.SerializerMethodField()
    commission_details = serializers.SerializerMethodField()

    payment_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Investment
        fields = '__all__'
    
    def get_customer_details(self, obj):
        """Get customer information"""
        return {
            'id': obj.customer.id,
            'username': obj.customer.username,
            'email': obj.customer.email,
            'phone': obj.customer.phone,
            'kyc_status': obj.customer.kyc_status,
        }
    
    def get_property_details(self, obj):
        """Get property information"""
        total_value = obj.property.price_per_unit * obj.property.total_units  # ✅ Calculate it
        return {
            'id': obj.property.id,
            'name': obj.property.name,
            'address': obj.property.address, 
            'property_type': obj.property.property_type,
            'status': obj.property.status,
            'total_value': str(total_value),  # ✅ Now calculated
            'price_per_unit': str(obj.property.price_per_unit),
            'total_units': obj.property.total_units,
            'available_units': obj.property.available_units,
        }

    
    def get_transaction_details(self, obj):
        """Get transaction information"""
        if not obj.transaction:
            return None
        return {
            'id': obj.transaction.id,
            'transaction_id': obj.transaction.transaction_id,
            'amount': str(obj.transaction.amount),
            'status': obj.transaction.status,
            'payment_method': obj.transaction.payment_method,
            'created_at': obj.transaction.created_at,
        }
    
    def get_commission_details(self, obj):
        comm = obj.commissions.filter(is_override=False).first()
        if not comm:
            return None
        
        return {
            'commission_id': comm.commission_id,
            'channel_partner': comm.cp.user.username if comm.cp else None,  # ← FIXED
            'cp_code': comm.cp.cp_code if comm.cp else None,  # ← BONUS: Add CP code
            'base_amount': float(comm.base_amount),
            'commission_rate': float(comm.commission_rate),
            'commission_amount': float(comm.commission_amount),
            'tds_amount': float(comm.tds_amount),
            'net_amount': float(comm.net_amount),
            'status': comm.status,
            'approved_at': comm.approved_at,
            'paid_at': comm.paid_at,
        }
    
    def get_payment_summary(self, obj):
        """Get payment breakdown"""
        return {
            'is_partial_payment': obj.is_partial_payment,
            'total_investment_amount': str(obj.minimum_required_amount or obj.amount),
            'paid_amount': str(obj.amount),
            'due_amount': str(obj.due_amount),
            'payment_due_date': obj.payment_due_date,
            'payment_status': 'Fully Paid' if obj.due_amount == 0 else 'Partial Payment',
        }
    
    class Meta:
        model = Investment
        fields = '__all__'


class AdminInvestmentActionSerializer(serializers.Serializer):
    """Serializer for investment actions"""
    action = serializers.ChoiceField(
        choices=['approve', 'reject', 'complete', 'cancel','approve_payment',
            'reject_payment',],
        required=True
    )
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Required for reject_payment, reject, and cancel actions"
    )
    
    def validate(self, attrs):
        action = attrs['action']
        reason = attrs.get('rejection_reason', '')
        
        if action in ['reject', 'cancel'] and not reason:
            raise serializers.ValidationError({
                'rejection_reason': f'Reason is required when {action}ing investment'
            })
        
        return attrs


class AdminInvestmentStatsSerializer(serializers.Serializer):
    """Investment statistics"""
    total_investments = serializers.IntegerField()
    pending_investments = serializers.IntegerField()
    approved_investments = serializers.IntegerField()
    rejected_investments = serializers.IntegerField()
    total_investment_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_pending_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_approved_amount = serializers.DecimalField(max_digits=15, decimal_places=2)

from decimal import Decimal
from rest_framework import serializers
from accounts.models import User   # <-- using your local User model
from properties.models import Property

class CreateInvestmentSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(required=True)
    property_id = serializers.IntegerField(required=True)

       # ✅ ADD THIS FIELD
    paid_amount = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2,
        required=True,
        help_text="Actual amount paid by customer"
    )
    # amount = serializers.DecimalField(max_digits=15, decimal_places=2)
        # Keep 'amount' as alias for backward compatibility
    amount = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2,
        required=False
    )
        # ✅ ADD THIS FIELD
    commitment_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Total investment commitment (if different from paid amount)"
    )
    units_count = serializers.IntegerField(min_value=1)
    referral_code = serializers.CharField(required=False, allow_blank=True, max_length=50)

    payment_method = serializers.ChoiceField(
        choices=['ONLINE', 'POS', 'DRAFT_CHEQUE', 'NEFT_RTGS']
    )
    payment_date = serializers.DateTimeField()
    payment_notes = serializers.CharField(required=False, allow_blank=True)
    payment_due_date = serializers.DateField(
        required=False,
        allow_null=True,
        input_formats=['%Y-%m-%d', '%d-%m-%Y'],
        help_text="Due date for remaining payment (accepts YYYY-MM-DD or DD-MM-YYYY)"
    )

    payment_mode = serializers.CharField(required=False, allow_blank=True)
    transaction_no = serializers.CharField(required=False, allow_blank=True)
    pos_slip_image = serializers.ImageField(required=False, allow_null=True)

    cheque_number = serializers.CharField(required=False, allow_blank=True)
    cheque_date = serializers.DateField(required=False, allow_null=True)
    bank_name = serializers.CharField(required=False, allow_blank=True)
    ifsc_code = serializers.CharField(required=False, allow_blank=True)
    branch_name = serializers.CharField(required=False, allow_blank=True)
    cheque_image = serializers.ImageField(required=False, allow_null=True)

    neft_rtgs_ref_no = serializers.CharField(required=False, allow_blank=True)

    def validate_customer_id(self, value):
        print("validate_customer_id called with:", value)
        try:
            return User.objects.get(id=int(value), is_active=True)
        except Exception as e:
            print("Lookup failed:", e)
            return int(value)

    def validate_property_id(self, value):
        try:
            return Property.objects.get(
                id=value,
                status__in=['live', 'funding'],
                is_published=True
            )
        except Property.DoesNotExist:
            raise serializers.ValidationError("Property not available for investment")

    def validate(self, data):
        amount = Decimal(str(data['amount']))
        property_obj = data['property_id']   # already a Property object
        units_count = data['units_count']

        if units_count > property_obj.available_units:
            raise serializers.ValidationError({
                'units_count': f"Only {property_obj.available_units} units available"
            })

        expected_amount = Decimal(str(property_obj.price_per_unit)) * units_count
        if amount > expected_amount:
            raise serializers.ValidationError({
                'amount': f"Amount cannot exceed ₹{expected_amount:,.2f}"
            })

        pm = data['payment_method']
        if pm in ['ONLINE', 'POS'] and not data.get('transaction_no'):
            raise serializers.ValidationError({'transaction_no': 'Transaction number is required'})
        if pm == 'DRAFT_CHEQUE':
            required = ['cheque_number', 'cheque_date', 'bank_name', 'ifsc_code', 'branch_name']
            missing = [f for f in required if not data.get(f)]
            if missing:
                raise serializers.ValidationError({
                    f: f'{f.replace("_", " ").title()} is required' for f in missing
                })
        if pm == 'NEFT_RTGS' and not data.get('neft_rtgs_ref_no'):
            raise serializers.ValidationError({'neft_rtgs_ref_no': 'NEFT/RTGS reference number is required'})

        return data
