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


# ============================================
# INVESTMENT SERIALIZERS
# ============================================

class InvestmentSerializer(serializers.ModelSerializer):
    """Serializer for Investment model - matches UserPortfolio.jsx expectations"""
    
    # User details
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    
    # Property details (nested object for PropertyCard component)
    property = serializers.SerializerMethodField()
    
    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
# CP details (optional)
    cp_name = serializers.CharField(
        source='referred_by_cp.user.get_full_name',
        read_only=True,
        allow_null=True
    )
    cp_code = serializers.CharField(
        source='referred_by_cp.cp_code',
        read_only=True,
        allow_null=True
    )
    referral_code = serializers.CharField(
        source='referral_code_used',
        read_only=True,
        allow_blank=True
    )
    
    # ALIASES - These point to real model fields via 'source'
    
    # ALIASES - These point to real model fields via 'source'
    units_count = serializers.IntegerField(source='units_purchased', read_only=True)
    invested_at = serializers.DateField(source='investment_date', read_only=True)
    expected_return = serializers.DecimalField(
        source='expected_return_amount', 
        max_digits=15, 
        decimal_places=2,
        read_only=True
    )
    actual_return = serializers.DecimalField(
        source='actual_return_amount',
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    property = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # 🆕 ADD PAYMENT DISPLAY FIELDS
    payment_method_display = serializers.CharField(
        source='get_payment_method_display',
        read_only=True
    )
    payment_status_display = serializers.CharField(
        source='get_payment_status_display',
        read_only=True
    )
    
    # 🆕 ADD PAYMENT APPROVAL INFO
    payment_approved_by_name = serializers.CharField(
        source='payment_approved_by.get_full_name',
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
            'referred_by_cp',
            'cp_name',
            'cp_code',
            'referral_code',
            'amount',
            'units_purchased',
            'units_count',
            'price_per_unit_at_investment',
            'status',
            'status_display',
            'expected_return_amount',
            'expected_return',
            'actual_return_amount',
            'actual_return',
            'investment_date',
            'invested_at',
            'maturity_date',
            
            # 🆕 PAYMENT FIELDS
            'payment_method',
            'payment_method_display',
            'payment_status',
            'payment_status_display',
            'payment_date',
            'payment_notes',
            'payment_approved_by',
            'payment_approved_by_name',
            'payment_approved_at',
            'payment_rejection_reason',
            
            # Payment method specific fields
            'payment_mode',
            'transaction_no',
            'pos_slip_image',
            'cheque_number',
            'cheque_date',
            'bank_name',
            'ifsc_code',
            'branch_name',
            'cheque_image',
            'neft_rtgs_ref_no',
            
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'investment_id',
            'investment_date',
            'payment_status',
            'payment_approved_by',
            'payment_approved_at',
            'payment_rejection_reason',
            'created_at',
            'updated_at'
        ]
    
    def get_property(self, obj):
        """Return property details matching PropertyCard expectations"""
        property_obj = obj.property
        
        # Get all images, ordered
        images_list = []
        primary_image = None
        
        try:
            if hasattr(property_obj, 'images'):
                images = property_obj.images.order_by('order').all()
                for img in images:
                    if img.image and self.context.get('request'):
                        img_url = self.context['request'].build_absolute_uri(img.image.url)
                        images_list.append(img_url)
                        if not primary_image:  # First image is primary
                            primary_image = img_url
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ Failed to get property images: {str(e)}")
        
        return {
            'id': property_obj.id,
            'name': getattr(property_obj, 'name', ''),
            'title': getattr(property_obj, 'title', ''),
            'builder_name': getattr(property_obj, 'builder_name', ''),
            'city': getattr(property_obj, 'city', ''),
            'locality': getattr(property_obj, 'locality', ''),
            'state': getattr(property_obj, 'state', ''),
            'price_per_unit': str(getattr(property_obj, 'price_per_unit', 0)),
            'minimum_investment': str(getattr(property_obj, 'minimum_investment', 0)),
            'expected_return_percentage': str(getattr(property_obj, 'expected_return_percentage', 0)),
            'gross_yield': str(getattr(property_obj, 'gross_yield', 0)),
            'potential_gain': str(getattr(property_obj, 'potential_gain', 0)),
            'status': getattr(property_obj, 'status', ''),
            'available_units': getattr(property_obj, 'available_units', 0),
            'total_units': getattr(property_obj, 'total_units', 0),
            'image': primary_image,  # Single primary image
            'images': images_list,   # All images array
            'gallery': images_list   # Alias for PropertyCard compatibility
        }


class CreateInvestmentSerializer(serializers.Serializer):
    """Serializer for creating new investment WITH payment details"""
    
    # Investment details
    property_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=True)
    units_count = serializers.IntegerField(required=True, min_value=1)
    referral_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        help_text="Optional CP referral code"
    )
    
    # 🆕 PAYMENT DETAILS (required)
    payment_method = serializers.ChoiceField(
        choices=['ONLINE', 'POS', 'DRAFT_CHEQUE', 'NEFT_RTGS'],
        required=True,
        help_text="Payment method used"
    )
    
    payment_date = serializers.DateTimeField(
        required=True,
        help_text="When payment was made"
    )
    
    payment_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Additional payment notes"
    )
    
    # 🆕 ONLINE / POS fields (conditional)
    payment_mode = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="UPI, Card, NetBanking, etc."
    )
    
    transaction_no = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Transaction ID / Reference number"
    )
    
    pos_slip_image = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="POS slip image"
    )
    
    # 🆕 CHEQUE fields (conditional)
    cheque_number = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Cheque number"
    )
    
    cheque_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Cheque date"
    )
    
    bank_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Bank name"
    )
    
    ifsc_code = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="IFSC code"
    )
    
    branch_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Branch name"
    )
    
    cheque_image = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Cheque image"
    )
    
    # 🆕 NEFT / RTGS fields (conditional)
    neft_rtgs_ref_no = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="NEFT/RTGS reference number"
    )
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
    
    def validate(self, data):
        """Cross-field validation"""

        from decimal import Decimal

            # ✅ FIX: Convert amount to Decimal properly
        try:
            amount = Decimal(str(data['amount']))
        except (ValueError, TypeError) as e:
            raise serializers.ValidationError({
                'amount': f'Invalid amount format: {str(e)}'
            })
        
        # Check if property exists and is available for investment
        try:
            property_obj = Property.objects.get(
                id=data['property_id'],
                status__in=['live', 'funding'],
                is_published=True
            )
        except Property.DoesNotExist:
            raise serializers.ValidationError({
                'property_id': 'Property not found or not available for investment'
            })
        
            # ✅ FIX: Convert property limits to Decimal for comparison
        # min_investment = Decimal(str(property_obj.minimum_investment))
        
        # Check minimum investment
        # if amount < min_investment:
        #     raise serializers.ValidationError({
        #         'amount': f"Minimum investment is ₹{min_investment:,.2f}"
        #     })
        
        # Check maximum investment if set
        if property_obj.maximum_investment:
            max_investment = Decimal(str(property_obj.maximum_investment))
            if amount > max_investment:
                raise serializers.ValidationError({
                    'amount': f"Maximum investment is ₹{max_investment:,.2f}"
                })
        
        # # Check minimum investment
        # if data['amount'] < property_obj.minimum_investment:
        #     raise serializers.ValidationError({
        #         'amount': f"Minimum investment is ₹{property_obj.minimum_investment:,.2f}"
        #     })
        
        # # Check maximum investment if set
        # if property_obj.maximum_investment and data['amount'] > property_obj.maximum_investment:
        #     raise serializers.ValidationError({
        #         'amount': f"Maximum investment is ₹{property_obj.maximum_investment:,.2f}"
        #     })
        
        # Check units available (don't deduct yet, just validate)
        if data['units_count'] > property_obj.available_units:
            raise serializers.ValidationError({
                'units_count': f"Only {property_obj.available_units} units available"
            })
        
        # Calculate expected investment based on units
        # expected_amount = property_obj.price_per_unit * data['units_count']
        
        # # Allow some tolerance for rounding
        # if abs(expected_amount - data['amount']) > 1:  # 1 rupee tolerance
        #     raise serializers.ValidationError({
        #         'amount': f"Amount should be ₹{expected_amount:,.2f} for {data['units_count']} units"
        #     })

        # ✅ FIX: Calculate expected amount using Decimal
        price_per_unit = Decimal(str(property_obj.price_per_unit))
        expected_amount = price_per_unit * data['units_count']

                # 🔥 NO minimum investment restriction
        data['is_partial_payment'] = amount < expected_amount
        data['expected_amount'] = expected_amount
        
        # Allow some tolerance for rounding
        if abs(expected_amount - amount) > Decimal('1.00'):  # 1 rupee tolerance
            raise serializers.ValidationError({
                'amount': f"Amount should be ₹{expected_amount:,.2f} for {data['units_count']} units"
            })
        
        # ============================================
        # 🆕 PAYMENT METHOD VALIDATION
        # ============================================
        payment_method = data.get('payment_method')
        
        # ONLINE / POS validation
        if payment_method in ['ONLINE', 'POS']:
            if not data.get('transaction_no'):
                raise serializers.ValidationError({
                    'transaction_no': 'Transaction number is required for ONLINE/POS payments'
                })
        
        # DRAFT_CHEQUE validation
        if payment_method == 'DRAFT_CHEQUE':
            missing = []
            if not data.get('cheque_number'):
                missing.append('cheque_number')
            if not data.get('cheque_date'):
                missing.append('cheque_date')
            if not data.get('bank_name'):
                missing.append('bank_name')
            if not data.get('ifsc_code'):
                missing.append('ifsc_code')
            if not data.get('branch_name'):
                missing.append('branch_name')
            
            if missing:
                raise serializers.ValidationError({
                    field: f'{field.replace("_", " ").title()} is required for cheque payment'
                    for field in missing
                })
        
        # NEFT_RTGS validation
        if payment_method == 'NEFT_RTGS':
            if not data.get('neft_rtgs_ref_no'):
                raise serializers.ValidationError({
                    'neft_rtgs_ref_no': 'NEFT/RTGS reference number is required'
                })
        
        # Store property object for later use
        data['property'] = property_obj
        
        return data
