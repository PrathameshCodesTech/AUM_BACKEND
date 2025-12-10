from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import logging

from ..models import Investment
from commissions.services.commission_service import CommissionService

logger = logging.getLogger(__name__)


class InvestmentService:
    """Service for investment operations"""

    @staticmethod
    @transaction.atomic
    def create_investment(user, property_obj, amount, units_count, referral_code=None, payment_data=None):
        """
        Create investment for user WITH payment details (NO wallet deduction)
        
        Args:
            user: Customer user object
            property_obj: Property instance
            amount: Investment amount
            units_count: Number of units
            referral_code: Optional CP referral code
            payment_data: Dict with payment details (method, date, transaction_no, etc.)
        """
        amount = Decimal(str(amount))
        logger.info(f"📊 Creating investment: amount={amount}, units={units_count}, referral_code={referral_code}")
        
        # ============================================
        # 🆕 NO WALLET CHECK - Direct payment submission
        # ============================================
        logger.info(f"💳 Payment method: {payment_data.get('payment_method') if payment_data else 'None'}")

        # ============================================
        # 🆕 DO NOT DEDUCT UNITS YET (only after admin approves)
        # ============================================
        logger.info(f"🏢 Validating property availability (NOT deducting yet)...")
        try:
            from properties.models import Property
            
            # Just check availability, don't deduct
            property_obj = Property.objects.get(id=property_obj.id)
            
            if units_count > property_obj.available_units:
                logger.error(f"❌ Not enough shares available!")
                raise ValueError(
                    f"Only {property_obj.available_units} shares available, but {units_count} requested"
                )
            
            logger.info(f"✅ Shares available: {property_obj.available_units} (will deduct after approval)")
            
        except Property.DoesNotExist:
            logger.error(f"❌ Property not found!")
            raise ValueError("Property not found")

        # ============================================
        # Pricing snapshot
        # ============================================
        logger.info(f"💵 Calculating pricing...")
        price_per_unit = getattr(property_obj, "price_per_unit", None)
        if price_per_unit is None:
            price_per_unit = amount / Decimal(units_count)
        logger.info(f"   Price per unit: ₹{price_per_unit}")

        # ============================================
        # Expected returns
        # ============================================
        logger.info(f"📈 Calculating expected returns...")
        irr = (
            getattr(property_obj, "expected_return_percentage", None)
            or getattr(property_obj, "target_irr", None)
            or 0
        )
        irr = Decimal(str(irr))
        expected_return_amount = (amount * irr) / Decimal("100")
        logger.info(f"   IRR: {irr}%")
        logger.info(f"   Expected return: ₹{expected_return_amount}")

        # ============================================
        # Determine CP for commission (if any)
        # ============================================
        logger.info(f"🤝 Determining CP for commission...")
        referred_by_cp = None
        referral_code_to_save = referral_code or ''
        cp_relation_created = False

        if referral_code:
            logger.info(f"   Validating referral code: {referral_code}")
            try:
                from partners.models import ChannelPartner, CPCustomerRelation
                normalized_code = referral_code.upper().strip()
                if normalized_code and not normalized_code.startswith('CP'):
                    normalized_code = f'CP{normalized_code}'
                    logger.info(f"   Normalized code: {referral_code} → {normalized_code}")
                
                cp = ChannelPartner.objects.get(
                    cp_code=normalized_code,
                    is_active=True,
                    is_verified=True
                )
                
                logger.info(f"✅ Valid referral code, CP: {cp.cp_code} ({cp.user.get_full_name()})")
                
                # Check if customer already has a CP relationship
                existing_relation = CPCustomerRelation.objects.filter(
                    customer=user,
                    is_active=True,
                    is_expired=False
                ).first()
                
                if existing_relation:
                    if existing_relation.cp.id != cp.id:
                        logger.warning(
                            f"⚠️ Customer already linked to CP {existing_relation.cp.cp_code}. "
                            f"Using existing CP, ignoring code {referral_code}"
                        )
                        referred_by_cp = existing_relation.cp
                        referral_code_to_save = existing_relation.referral_code
                    else:
                        referred_by_cp = cp
                        logger.info(f"✅ Customer already linked to this CP")
                else:
                    try:
                        CPCustomerRelation.objects.create(
                            cp=cp,
                            customer=user,
                            referral_code=normalized_code,
                            is_active=True,
                        )
                        referred_by_cp = cp
                        referral_code_to_save = normalized_code
                        cp_relation_created = True
                        
                        logger.info(f"✅ Created new CPCustomerRelation for CP {cp.cp_code}")
                    except Exception as e:
                        logger.error(f"❌ Failed to create CPCustomerRelation: {e}")
                        referred_by_cp = cp
                
            except ChannelPartner.DoesNotExist:
                logger.warning(f"⚠️ Invalid referral code: {referral_code}")
                referral_code_to_save = ''

        # Check if customer has pre-linked CP relationship (if no code entered)
        if not referred_by_cp:
            logger.info(f"   Checking for pre-linked CP relationship...")
            try:
                from partners.models import CPCustomerRelation
                
                relation = CPCustomerRelation.objects.filter(
                    customer=user,
                    is_active=True,
                    is_expired=False,
                    expiry_date__gte=timezone.now()
                ).select_related('cp').first()
                
                if relation:
                    referred_by_cp = relation.cp
                    referral_code_to_save = relation.referral_code
                    logger.info(f"✅ Found pre-linked CP: {referred_by_cp.cp_code} ({referred_by_cp.user.get_full_name()})")
                else:
                    logger.info(f"ℹ️ No pre-linked CP found")
            except Exception as e:
                logger.error(f"❌ Error checking CP relationship: {e}")

        if not referred_by_cp:
            logger.info(f"ℹ️ No CP linked to this investment")
        
        # ============================================
        # 🆕 PREPARE PAYMENT DATA
        # ============================================
        payment_fields = {}
        if payment_data:
            logger.info(f"💳 Processing payment data...")
            
            # Core payment fields
            payment_fields['payment_method'] = payment_data.get('payment_method', '')
            payment_fields['payment_date'] = payment_data.get('payment_date')
            payment_fields['payment_notes'] = payment_data.get('payment_notes', '')
            payment_fields['payment_status'] = 'PENDING'
            
            # Method-specific fields
            payment_fields['payment_mode'] = payment_data.get('payment_mode', '')
            payment_fields['transaction_no'] = payment_data.get('transaction_no', '')
            payment_fields['pos_slip_image'] = payment_data.get('pos_slip_image')
            
            payment_fields['cheque_number'] = payment_data.get('cheque_number', '')
            payment_fields['cheque_date'] = payment_data.get('cheque_date')
            payment_fields['bank_name'] = payment_data.get('bank_name', '')
            payment_fields['ifsc_code'] = payment_data.get('ifsc_code', '')
            payment_fields['branch_name'] = payment_data.get('branch_name', '')
            payment_fields['cheque_image'] = payment_data.get('cheque_image')
            
            payment_fields['neft_rtgs_ref_no'] = payment_data.get('neft_rtgs_ref_no', '')
            
            logger.info(f"✅ Payment data prepared: {payment_fields['payment_method']}")
        
        # ============================================
        # 🆕 CREATE INVESTMENT (status: pending_payment)
        # ============================================
        logger.info(f"📝 Creating investment record...")
        try:
            investment = Investment.objects.create(
                investment_id=InvestmentService._generate_investment_id(),
                customer=user,
                property=property_obj,
                referred_by_cp=referred_by_cp,
                referral_code_used=referral_code_to_save,
                amount=amount,
                units_purchased=units_count,
                price_per_unit_at_investment=price_per_unit,
                status='pending_payment',  # 🆕 NEW STATUS
                expected_return_amount=expected_return_amount,
                **payment_fields  # 🆕 ADD PAYMENT FIELDS
            )
            logger.info(f"✅ Investment created: {investment.investment_id}")
            logger.info(f"   Status: {investment.status}")
            logger.info(f"   Payment method: {investment.payment_method}")
            logger.info(f"   Linked CP: {referred_by_cp.cp_code if referred_by_cp else 'None'}")
            
        except Exception as e:
            logger.error(f"❌ Error creating investment: {str(e)}")
            raise ValueError(f"Failed to create investment: {str(e)}")

        # ============================================
        # 🆕 DO NOT CALCULATE COMMISSION YET
        # Commission will be calculated when investment is approved
        # ============================================
        logger.info(f"ℹ️ Commission will be calculated after investment approval")
            
        logger.info(f"🎉 Investment created successfully: {investment.investment_id}")
        logger.info(f"⏳ Waiting for admin to approve payment...")
        return investment

    @staticmethod
    def _generate_investment_id():
        """Generate unique investment ID"""
        from uuid import uuid4
        return f"INV-{uuid4().hex[:10].upper()}"

    @staticmethod
    def get_user_investments(user):
        """Get all investments for a user"""
        return Investment.objects.filter(
            customer=user,
            is_deleted=False
        ).select_related('property').order_by('-created_at')

    @staticmethod
    def get_investment_detail(investment_id, user):
        """Get specific investment detail"""
        return Investment.objects.select_related('property').get(
            id=investment_id,
            customer=user,
            is_deleted=False
        )