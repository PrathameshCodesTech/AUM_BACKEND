from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import logging

from ..models import Investment, Wallet, InvestmentUnit
from properties.models import PropertyUnit
from commissions.services.commission_service import CommissionService

logger = logging.getLogger(__name__)


class InvestmentService:
    """Service for investment operations"""

    @staticmethod
    @transaction.atomic
    def create_investment(user, property_obj, amount, units_count, referral_code=None):
        """
        Create investment for user
        
        Args:
            user: Customer user object
            property_obj: Property instance
            amount: Investment amount
            units_count: Number of units
            referral_code: Optional CP referral code (overrides pre-linked CP)
        """
        amount = Decimal(str(amount))
        logger.info(f"📊 Creating investment: amount={amount}, units={units_count}, referral_code={referral_code}")
        # 1. Check KYC
        logger.info(f"🔍 Checking KYC for user: {user.username}")
        logger.info(f"   hasattr(user, 'kyc'): {hasattr(user, 'kyc')}")
        
        if not hasattr(user, "kyc"):
            logger.error(f"❌ User has no 'kyc' attribute!")
            raise ValueError("KYC not found. Please complete KYC first.")
        
        try:
            kyc = user.kyc
            logger.info(f"   user.kyc exists: {kyc}")
            logger.info(f"   user.kyc.status: {kyc.status}")
            logger.info(f"   user.kyc_status: {user.kyc_status}")
            
            if kyc.status != "verified":
                logger.error(f"❌ KYC status is '{kyc.status}', not 'verified'!")
                raise ValueError(f"KYC status is '{kyc.status}'. Please complete KYC verification.")
            
            logger.info(f"✅ KYC verified! Proceeding with investment...")
            
        except Exception as e:
            logger.error(f"❌ Error checking KYC: {str(e)}")
            raise ValueError(f"KYC verification failed: {str(e)}")

        # 2. Check wallet balance (lock row)
        logger.info(f"💰 Checking wallet balance...")
        try:
            wallet = Wallet.objects.select_for_update().get(user=user)
            logger.info(f"   Wallet balance: ₹{wallet.balance}")
            logger.info(f"   Required amount: ₹{amount}")
            
            if wallet.balance < amount:
                logger.error(f"❌ Insufficient balance!")
                raise ValueError(f"Insufficient balance. Available: ₹{wallet.balance}")
            
            logger.info(f"✅ Sufficient balance available")
            
        except Wallet.DoesNotExist:
            logger.error(f"❌ Wallet not found for user!")
            raise ValueError("Wallet not found. Please create a wallet first.")

        # 3. Select available units
        logger.info(f"🏢 Selecting {units_count} available units...")
        try:
            units_qs = (
                PropertyUnit.objects.select_for_update()
                .filter(property=property_obj, status="available")
                .order_by("unit_number")
            )
            units = list(units_qs[:units_count])
            
            logger.info(f"   Found {len(units)} available units")
            
            if len(units) < units_count:
                logger.error(f"❌ Not enough units available!")
                raise ValueError(f"Only {len(units)} units available, but {units_count} requested")
            
            logger.info(f"✅ Units selected successfully")
            
        except Exception as e:
            logger.error(f"❌ Error selecting units: {str(e)}")
            raise ValueError(f"Error selecting units: {str(e)}")

        # 4. Deduct from wallet
        logger.info(f"💸 Deducting ₹{amount} from wallet...")
        try:
            from .wallet_service import WalletService
            
            tx = WalletService.deduct_funds(
                user,
                amount,
                f"Investment in {getattr(property_obj, 'title', property_obj)}",
            )
            logger.info(f"✅ Funds deducted, transaction: {tx.transaction_id if tx else 'None'}")
            
        except Exception as e:
            logger.error(f"❌ Error deducting funds: {str(e)}")
            raise ValueError(f"Payment failed: {str(e)}")

        # 5. Pricing snapshot
        logger.info(f"💵 Calculating pricing...")
        price_per_unit = getattr(property_obj, "price_per_unit", None)
        if price_per_unit is None:
            price_per_unit = amount / Decimal(units_count)
        logger.info(f"   Price per unit: ₹{price_per_unit}")

        # 6. Expected returns
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

        # 7. Determine CP for commission (if any)
        logger.info(f"🤝 Determining CP for commission...")
        referred_by_cp = None
        referral_code_to_save = referral_code or ''
        
        if referral_code:
            # Customer entered referral code at investment time
            logger.info(f"   Validating referral code: {referral_code}")
            try:
                from partners.models import ChannelPartner
                cp = ChannelPartner.objects.get(
                    cp_code=referral_code,
                    is_active=True,
                    is_verified=True
                )
                referred_by_cp = cp
                logger.info(f"✅ Valid referral code, CP: {cp.cp_code} ({cp.user.get_full_name()})")
            except ChannelPartner.DoesNotExist:
                logger.warning(f"⚠️ Invalid referral code: {referral_code}")
                referral_code_to_save = ''  # Clear invalid code
        
        # Check if customer has pre-linked CP relationship
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
                    logger.info(f"✅ Found pre-linked CP: {referred_by_cp.cp_code} ({referred_by_cp.user.get_full_name()})")
                else:
                    logger.info(f"ℹ️ No pre-linked CP found")
            except Exception as e:
                logger.error(f"❌ Error checking CP relationship: {e}")
        
        if not referred_by_cp:
            logger.info(f"ℹ️ No CP linked to this investment")
        
        # 8. Create investment
        logger.info(f"📝 Creating investment record...")
        try:
            investment = Investment.objects.create(
                investment_id=InvestmentService._generate_investment_id(),
                customer=user,
                property=property_obj,
                referred_by_cp=referred_by_cp,  # Pre-linked CP (can be None)
                referral_code_used=referral_code_to_save,  # Code entered at investment time
                amount=amount,
                units_purchased=units_count,
                price_per_unit_at_investment=price_per_unit,
                status="pending",
                expected_return_amount=expected_return_amount,
                transaction=tx if tx else None,
            )
            logger.info(f"✅ Investment created: {investment.investment_id}")
            logger.info(f"   Linked CP: {referred_by_cp.cp_code if referred_by_cp else 'None'}")
            logger.info(f"   Referral code used: {referral_code_to_save or 'None'}")
            
        except Exception as e:
            logger.error(f"❌ Error creating investment: {str(e)}")
            raise ValueError(f"Failed to create investment: {str(e)}")

        # 8. Link units
        logger.info(f"🔗 Linking units to investment...")
        try:
            for unit in units:
                InvestmentUnit.objects.create(investment=investment, unit=unit)
                unit.status = "booked"
                unit.save(update_fields=["status"])
            logger.info(f"✅ Linked {len(units)} units")
            
        except Exception as e:
            logger.error(f"❌ Error linking units: {str(e)}")
            raise ValueError(f"Failed to link units: {str(e)}")

       # 10. Calculate commission (only if CP linked)
        if referred_by_cp:
            logger.info(f"💰 Calculating commission for CP: {referred_by_cp.cp_code}...")
            try:
                commission = CommissionService.calculate_commission(investment)
                if commission:
                    logger.info(f"✅ Commission calculated: ₹{commission.commission_amount}")
                else:
                    logger.warning(f"⚠️ No commission calculated (no matching commission rule)")
            except Exception as e:
                logger.warning(f"⚠️ Commission calculation failed: {str(e)}")
                # Don't fail the investment if commission fails
        else:
            logger.info(f"ℹ️ No CP linked, skipping commission calculation")
            
        logger.info(f"🎉 Investment completed successfully: {investment.investment_id}")
        return investment

    @staticmethod
    def _generate_investment_id():
        """Simple helper to generate a unique investment_id"""
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