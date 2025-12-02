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
        ]


class AdminInvestmentDetailSerializer(serializers.ModelSerializer):
    """Detailed investment info for admin"""
    customer_details = serializers.SerializerMethodField()
    property_details = serializers.SerializerMethodField()
    transaction_details = serializers.SerializerMethodField()
    commission_details = serializers.SerializerMethodField()
    
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
        """Get commission information"""
        from commissions.models import Commission
        commissions = Commission.objects.filter(investment=obj)
        return [{
            'id': comm.id,
            'channel_partner': comm.channel_partner.username if comm.channel_partner else None,
            'amount': str(comm.amount),
            'status': comm.status,
            'created_at': comm.created_at,
        } for comm in commissions]


class AdminInvestmentActionSerializer(serializers.Serializer):
    """Serializer for investment actions"""
    action = serializers.ChoiceField(
        choices=['approve', 'reject', 'complete', 'cancel'],
        required=True
    )
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Required if action is 'reject' or 'cancel'"
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