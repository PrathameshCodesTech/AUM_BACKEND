# investments/serializers.py
from rest_framework import serializers
from .models import Wallet, Transaction, Investment
from properties.models import Property
from accounts.models import User


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for Wallet model"""
    
    available_balance = serializers.SerializerMethodField()
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Wallet
        fields = [
            'id',
            'user',
            'user_name',
            'balance',
            'ledger_balance',
            'available_balance',
            'is_active',
            'is_blocked',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'balance',
            'ledger_balance',
            'created_at',
            'updated_at'
        ]
    
    def get_available_balance(self, obj):
        """Calculate available balance (balance that can be used)"""
        return obj.balance


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display',
        read_only=True
    )
    purpose_display = serializers.CharField(
        source='get_purpose_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_id',
            'wallet',
            'user',
            'user_name',
            'transaction_type',
            'transaction_type_display',
            'purpose',
            'purpose_display',
            'amount',
            'balance_before',
            'balance_after',
            'status',
            'status_display',
            'payment_method',
            'payment_gateway',
            'gateway_transaction_id',
            'gateway_response',
            'reference_type',
            'reference_id',
            'description',
            'internal_notes',
            'processed_at',
            'processed_by',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'transaction_id',
            'balance_before',
            'balance_after',
            'processed_at',
            'created_at',
            'updated_at'
        ]


class InvestmentSerializer(serializers.ModelSerializer):
    """Serializer for Investment model"""
    
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    property_name = serializers.CharField(source='property.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    cp_name = serializers.CharField(
        source='referred_by_cp.user.get_full_name',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = Investment
        fields = [
            'id',
            'investment_id',
            'customer',
            'customer_name',
            'property',
            'property_name',
            'referred_by_cp',
            'cp_name',
            'amount',
            'units_purchased',
            'price_per_unit_at_investment',
            'status',
            'status_display',
            'approved_by',
            'approved_at',
            'rejection_reason',
            'payment_completed',
            'payment_completed_at',
            'transaction',
            'expected_return_amount',
            'actual_return_amount',
            'investment_date',
            'maturity_date',
            'lock_in_end_date',
            'notes',
            'is_deleted',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'investment_id',
            'investment_date',
            'approved_by',
            'approved_at',
            'payment_completed_at',
            'created_at',
            'updated_at'
        ]


class CreateInvestmentSerializer(serializers.Serializer):
    """Serializer for creating new investment"""
    
    property_id = serializers.IntegerField()
    units = serializers.IntegerField(min_value=1)
    referred_by_cp_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_property_id(self, value):
        """Validate property exists and is available"""
        from properties.models import Property
        
        try:
            property_obj = Property.objects.get(id=value)
            
            if property_obj.status not in ['live', 'funding']:
                raise serializers.ValidationError(
                    "Property is not available for investment"
                )
            
            if property_obj.available_units <= 0:
                raise serializers.ValidationError(
                    "No units available in this property"
                )
            
            return value
            
        except Property.DoesNotExist:
            raise serializers.ValidationError("Property not found")
    
    def validate_units(self, value):
        """Validate units"""
        if value <= 0:
            raise serializers.ValidationError("Units must be greater than 0")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        from properties.models import Property
        
        property_obj = Property.objects.get(id=data['property_id'])
        units = data['units']
        
        # Check if enough units available
        if units > property_obj.available_units:
            raise serializers.ValidationError({
                'units': f'Only {property_obj.available_units} units available'
            })
        
        # Calculate total amount
        total_amount = property_obj.price_per_unit * units
        
        # Check minimum investment
        if total_amount < property_obj.minimum_investment:
            raise serializers.ValidationError({
                'units': f'Minimum investment is ₹{property_obj.minimum_investment}'
            })
        
        # Check maximum investment if set
        if property_obj.maximum_investment and total_amount > property_obj.maximum_investment:
            raise serializers.ValidationError({
                'units': f'Maximum investment is ₹{property_obj.maximum_investment}'
            })
        
        data['total_amount'] = total_amount
        data['price_per_unit'] = property_obj.price_per_unit
        
        return data


class TransactionHistorySerializer(serializers.ModelSerializer):
    """Simplified serializer for transaction history"""
    
    type_icon = serializers.SerializerMethodField()
    amount_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_id',
            'transaction_type',
            'type_icon',
            'purpose',
            'amount',
            'amount_display',
            'status',
            'description',
            'created_at'
        ]
    
    def get_type_icon(self, obj):
        """Get icon based on transaction type"""
        if obj.transaction_type == 'credit':
            return '↑'
        return '↓'
    
    def get_amount_display(self, obj):
        """Format amount with sign"""
        sign = '+' if obj.transaction_type == 'credit' else '-'
        return f'{sign}₹{obj.amount:,.2f}'



# investments/serializers.py

class CreateInvestmentSerializer(serializers.Serializer):
    property_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=True)
    units_count = serializers.IntegerField(required=True, min_value=1)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
    
    def validate(self, data):
        from properties.models import Property  # Import here to avoid circular import
        
        # Check if property exists and is available for investment
        try:
            property_obj = Property.objects.get(
                id=data['property_id'],
                status__in=['live', 'funding'],  # ✅ Changed from 'active'
                is_published=True
            )
        except Property.DoesNotExist:
            raise serializers.ValidationError({
                'non_field_errors': ['Property not found or not available for investment']
            })
        
        # Check minimum investment
        if data['amount'] < property_obj.minimum_investment:
            raise serializers.ValidationError({
                'amount': f"Minimum investment is ₹{property_obj.minimum_investment:,.2f}"
            })
        
        # Check maximum investment if set
        if property_obj.maximum_investment and data['amount'] > property_obj.maximum_investment:
            raise serializers.ValidationError({
                'amount': f"Maximum investment is ₹{property_obj.maximum_investment:,.2f}"
            })
        
        # Check units available
        if data['units_count'] > property_obj.available_units:
            raise serializers.ValidationError({
                'units_count': f"Only {property_obj.available_units} units available"
            })
        
        # Calculate expected investment based on units
        expected_amount = property_obj.price_per_unit * data['units_count']
        
        # Allow some tolerance for rounding
        if abs(expected_amount - data['amount']) > 1:  # 1 rupee tolerance
            raise serializers.ValidationError({
                'amount': f"Amount should be ₹{expected_amount:,.2f} for {data['units_count']} units"
            })
        
        # Store property object for later use
        data['property'] = property_obj
        
        return data


class InvestmentSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source='property.title', read_only=True)
    property_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Investment
        fields = [
            'id', 'property', 'property_title', 'property_image',
            'amount', 'units_count', 'status', 'invested_at',
            'expected_return', 'actual_return'
        ]
    
    def get_property_image(self, obj):
        image = obj.property.images.filter(is_primary=True).first()
        if image:
            return self.context['request'].build_absolute_uri(image.image.url)
        return None
    


