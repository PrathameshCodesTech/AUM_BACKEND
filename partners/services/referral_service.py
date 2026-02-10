# partners/services/referral_service.py
from django.conf import settings
from ..models import CPPropertyAuthorization, CPInvite
from django.utils import timezone
import uuid


class ReferralService:
    """Service for handling referral links and invites"""
    
    @staticmethod
    def generate_property_referral_link(cp, property_obj):
        """
        Generate referral link for CP + Property combination
        
        Args:
            cp: ChannelPartner instance
            property_obj: Property instance
        
        Returns:
            str: Referral link
        """
        # Base URL from settings or default
        base_url = getattr(settings, 'FRONTEND_BASE_URL', 'https://assetkart.com')
        
        # Format: /property/{property_id}?ref={cp_code}
        link = f"{base_url}/property/{property_obj.id}?ref={cp.cp_code}"
        
        return link
    
    @staticmethod
    def generate_signup_invite_link(invite_code):
        """
        Generate signup invite link
        
        Args:
            invite_code: CPInvite code
        
        Returns:
            str: Invite link
        """
        base_url = getattr(settings, 'FRONTEND_BASE_URL', 'https://assetkart.com')
        
        # Format: /signup?invite={invite_code}
        link = f"{base_url}/signup?invite={invite_code}"
        
        return link
    
    @staticmethod
    def generate_general_referral_link(cp_code):
        """
        Generate general CP referral link (not property-specific)
        
        Args:
            cp_code: CP code
        
        Returns:
            str: Referral link
        """
        base_url = 'https://app.assetkart.com'
        
        # Format: /signup?ref={cp_code}
        link = f"{base_url}/signup?ref={cp_code}"
        
        return link
    
    @staticmethod
    def create_invite(cp, invite_data):
        """
        Create invite for CP
        
        Args:
            cp: ChannelPartner instance
            invite_data: Dict with phone, email, name, message
        
        Returns:
            CPInvite instance
        """
        # Generate unique invite code
        invite_code = f"INV{uuid.uuid4().hex[:8].upper()}"
        
        # Create invite
        invite = CPInvite.objects.create(
            cp=cp,
            invite_code=invite_code,
            **invite_data
        )
        
        return invite
    
    @staticmethod
    def validate_and_use_invite(invite_code, user):
        """
        Validate invite and mark as used
        
        Args:
            invite_code: Invite code string
            user: User who is using the invite
        
        Returns:
            CPInvite instance or None
        """
        try:
            invite = CPInvite.objects.get(invite_code=invite_code)
            
            # Check if valid
            if invite.is_used:
                return None  # Already used
            
            if invite.is_expired or invite.expiry_date < timezone.now():
                return None  # Expired
            
            # Mark as used
            invite.mark_as_used(user)
            
            return invite
        
        except CPInvite.DoesNotExist:
            return None
    
    @staticmethod
    def get_cp_from_referral_code(referral_code):
        """
        Get CP from referral code
        
        Args:
            referral_code: CP code or invite code
        
        Returns:
            ChannelPartner instance or None
        """
        from ..models import ChannelPartner
        
        # Try CP code first
        try:
            cp = ChannelPartner.objects.get(
                cp_code=referral_code,
                is_active=True,
                is_verified=True
            )
            return cp
        except ChannelPartner.DoesNotExist:
            pass
        
        # Try invite code
        try:
            invite = CPInvite.objects.get(
                invite_code=referral_code,
                is_used=False,
                is_expired=False
            )
            # Check expiry
            if invite.expiry_date >= timezone.now():
                return invite.cp
        except CPInvite.DoesNotExist:
            pass
        
        return None
    
    @staticmethod
    def track_referral_click(cp_code, property_id=None):
        """
        Track referral link clicks (for analytics)
        
        Args:
            cp_code: CP code
            property_id: Optional property ID
        
        Returns:
            bool: Success
        """
        # TODO: Implement click tracking in a separate ClickTracking model
        # For now, just return True
        return True
