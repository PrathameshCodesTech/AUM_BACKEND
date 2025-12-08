# commissions/serializers.py
from rest_framework import serializers
from .models import Commission, CommissionPayout
from decimal import Decimal


class CommissionSerializer(serializers.ModelSerializer):
    """Serializer for Commission model"""
    
    # CP details
    cp_code = serializers.CharField(source='cp.cp_code', read_only=True)
    cp_name = serializers.CharField(source='cp.user.get_full_name', read_only=True)
    cp_phone = serializers.CharField(source='cp.user.phone', read_only=True)
    cp_email = serializers.EmailField(source='cp.user.email', read_only=True)
    
    # Investment details
    investment_id = serializers.CharField(source='investment.investment_id', read_only=True)
    customer_name = serializers.CharField(source='investment.customer.get_full_name', read_only=True)
    property_name = serializers.CharField(source='investment.property.name', read_only=True)
    
    # Display fields
    commission_type_display = serializers.CharField(source='get_commission_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Formatted amounts
    base_amount_formatted = serializers.SerializerMethodField()
    commission_amount_formatted = serializers.SerializerMethodField()
    tds_amount_formatted = serializers.SerializerMethodField()
    net_amount_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Commission
        fields = [
            'id',
            'commission_id',
            
            # CP info
            'cp',
            'cp_code',
            'cp_name',
            'cp_phone',
            'cp_email',
            
            # Investment info
            'investment',
            'investment_id',
            'customer_name',
            'property_name',
            
            # Commission details
            'commission_type',
            'commission_type_display',
            'base_amount',
            'base_amount_formatted',
            'commission_rate',
            'commission_amount',
            'commission_amount_formatted',
            
            # TDS
            'tds_percentage',
            'tds_amount',
            'tds_amount_formatted',
            
            # Net payable
            'net_amount',
            'net_amount_formatted',
            
            # Rule
            'commission_rule',
            
            # Override fields
            'is_override',
            'parent_commission',
            
            # Status
            'status',
            'status_display',
            
            # Approval
            'approved_by',
            'approved_at',
            
            # Payment
            'paid_at',
            'paid_by',
            'payment_reference',
            'transaction',
            
            # Notes
            'notes',
            
            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'commission_id',
            'commission_amount',
            'tds_amount',
            'net_amount',
            'approved_at',
            'paid_at',
            'created_at',
            'updated_at',
        ]
    
    def get_base_amount_formatted(self, obj):
        return f"₹{obj.base_amount:,.2f}"
    
    def get_commission_amount_formatted(self, obj):
        return f"₹{obj.commission_amount:,.2f}"
    
    def get_tds_amount_formatted(self, obj):
        return f"₹{obj.tds_amount:,.2f}"
    
    def get_net_amount_formatted(self, obj):
        return f"₹{obj.net_amount:,.2f}"


class CommissionSummarySerializer(serializers.Serializer):
    """Serializer for commission earnings summary"""
    
    total_pending = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_approved = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_earned = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Formatted versions
    total_pending_formatted = serializers.SerializerMethodField()
    total_approved_formatted = serializers.SerializerMethodField()
    total_paid_formatted = serializers.SerializerMethodField()
    total_earned_formatted = serializers.SerializerMethodField()
    
    def get_total_pending_formatted(self, obj):
        return f"₹{obj['total_pending']:,.2f}"
    
    def get_total_approved_formatted(self, obj):
        return f"₹{obj['total_approved']:,.2f}"
    
    def get_total_paid_formatted(self, obj):
        return f"₹{obj['total_paid']:,.2f}"
    
    def get_total_earned_formatted(self, obj):
        return f"₹{obj['total_earned']:,.2f}"


class CommissionPayoutSerializer(serializers.ModelSerializer):
    """Serializer for CommissionPayout model"""
    
    cp_code = serializers.CharField(source='cp.cp_code', read_only=True)
    cp_name = serializers.CharField(source='cp.user.get_full_name', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    
    commission_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CommissionPayout
        fields = [
            'id',
            'payout_id',
            'cp',
            'cp_code',
            'cp_name',
            'total_amount',
            'tds_amount',
            'net_amount',
            'commissions',
            'commission_count',
            'status',
            'payment_mode',
            'payment_reference',
            'paid_at',
            'processed_by',
            'processed_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'payout_id',
            'paid_at',
            'created_at',
            'updated_at',
        ]
    
    def get_commission_count(self, obj):
        return obj.commissions.count()