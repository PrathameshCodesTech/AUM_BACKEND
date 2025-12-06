# partners/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Q

from accounts.permissions import IsChannelPartner
from .models import (
    ChannelPartner,
    CPCustomerRelation,
    CPPropertyAuthorization,
    CPLead,
    CPInvite,
    CPDocument
)
from .serializers import (
    CPApplicationSerializer,
    CPProfileSerializer,
    CPCustomerRelationSerializer,
    CPPropertyAuthorizationSerializer,
    CPLeadSerializer,
    CPLeadCreateSerializer,
    CPInviteSerializer,
    CPInviteCreateSerializer,
    CPDocumentSerializer,
    CPDashboardStatsSerializer,
)
from .services.cp_service import CPService
from .services.referral_service import ReferralService


# ============================================
# CP APPLICATION & PROFILE
# ============================================

class CPApplicationView(APIView):
    """
    POST /api/cp/apply/
    Apply to become a Channel Partner
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check if user already has CP profile
        if hasattr(request.user, 'cp_profile'):
            return Response(
                {'error': 'You already have a Channel Partner profile'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check KYC
        if not request.user.kyc_verified:
            return Response(
                {'error': 'KYC verification required before applying'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CPApplicationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                cp = CPService.create_cp_application(
                    user=request.user,
                    application_data=serializer.validated_data
                )
                
                response_serializer = CPProfileSerializer(cp)
                return Response(
                    {
                        'message': 'Application submitted successfully',
                        'data': response_serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )
            
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CPApplicationStatusView(APIView):
    """
    GET /api/cp/application-status/
    Check CP application status
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            cp = request.user.cp_profile
            serializer = CPProfileSerializer(cp)
            return Response({
                'has_application': True,
                'data': serializer.data
            })
        except ChannelPartner.DoesNotExist:
            return Response({
                'has_application': False,
                'message': 'No CP application found'
            })


class CPProfileView(APIView):
    """
    GET /api/cp/profile/
    PUT /api/cp/profile/
    Get or update CP profile
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def get(self, request):
        cp = request.user.cp_profile
        serializer = CPProfileSerializer(cp)
        return Response(serializer.data)
    
    def put(self, request):
        cp = request.user.cp_profile
        
        # Only allow updating certain fields
        allowed_fields = [
            'business_address',
            'bank_name',
            'account_number',
            'ifsc_code',
            'account_holder_name',
            'commission_notes',
        ]
        
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = CPProfileSerializer(cp, data=update_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'data': serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# DOCUMENT UPLOAD
# ============================================

class CPDocumentUploadView(APIView):
    """
    POST /api/cp/documents/upload/
    Upload CP documents
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        cp = request.user.cp_profile
        
        # Add CP to request data
        data = request.data.copy()
        data['cp'] = cp.id
        
        serializer = CPDocumentSerializer(data=data)
        if serializer.is_valid():
            serializer.save(cp=cp)
            return Response(
                {
                    'message': 'Document uploaded successfully',
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CPDocumentListView(APIView):
    """
    GET /api/cp/documents/
    List CP documents
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def get(self, request):
        cp = request.user.cp_profile
        documents = cp.documents.all()
        serializer = CPDocumentSerializer(documents, many=True)
        return Response(serializer.data)


# ============================================
# CP DASHBOARD
# ============================================

class CPDashboardStatsView(APIView):
    """
    GET /api/cp/dashboard/stats/
    Get CP dashboard statistics
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def get(self, request):
        cp = request.user.cp_profile
        
        stats = CPService.get_cp_dashboard_stats(cp)
        serializer = CPDashboardStatsSerializer(stats)
        
        return Response(serializer.data)


# ============================================
# AUTHORIZED PROPERTIES
# ============================================

class CPAuthorizedPropertiesView(APIView):
    """
    GET /api/cp/properties/
    List authorized properties with referral links
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def get(self, request):
        cp = request.user.cp_profile
        
        authorizations = cp.property_authorizations.filter(
            is_authorized=True,
            approval_status='approved'
        ).select_related('property')
        
        serializer = CPPropertyAuthorizationSerializer(authorizations, many=True)
        return Response(serializer.data)


class CPPropertyReferralLinkView(APIView):
    """
    GET /api/cp/properties/{property_id}/referral-link/
    Get referral link for specific property
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def get(self, request, property_id):
        cp = request.user.cp_profile
        
        # Check if CP is authorized for this property
        authorization = get_object_or_404(
            CPPropertyAuthorization,
            cp=cp,
            property_id=property_id,
            is_authorized=True,
            approval_status='approved'
        )
        
        # Generate link if not exists
        if not authorization.referral_link:
            authorization.generate_referral_link()
        
        # Also generate general referral link
        general_link = ReferralService.generate_general_referral_link(cp.cp_code)
        
        return Response({
            'property_referral_link': authorization.referral_link,
            'general_referral_link': general_link,
            'cp_code': cp.cp_code,
            'property_id': property_id,
        })


# ============================================
# CUSTOMERS
# ============================================

class CPCustomersView(APIView):
    """
    GET /api/cp/customers/
    List CP's customers
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def get(self, request):
        cp = request.user.cp_profile
        
        # Get query params
        is_active = request.query_params.get('is_active')
        is_expired = request.query_params.get('is_expired')
        search = request.query_params.get('search')
        
        # Build filters
        filters = {}
        if is_active is not None:
            filters['is_active'] = is_active.lower() == 'true'
        if is_expired is not None:
            filters['is_expired'] = is_expired.lower() == 'true'
        if search:
            filters['search'] = search
        
        # Get customers
        customers = CPService.get_cp_customers(cp, filters)
        serializer = CPCustomerRelationSerializer(customers, many=True)
        
        return Response({
            'count': customers.count(),
            'results': serializer.data
        })


# ============================================
# COMMISSIONS
# ============================================

class CPCommissionsView(APIView):
    """
    GET /api/cp/commissions/
    List CP's commissions
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def get(self, request):
        from commissions.models import Commission
        from commissions.serializers import CommissionSerializer
        
        cp = request.user.cp_profile
        
        # Get query params
        status_filter = request.query_params.get('status')
        
        # Get commissions
        commissions = Commission.objects.filter(cp=cp)
        
        if status_filter:
            commissions = commissions.filter(status=status_filter)
        
        commissions = commissions.select_related(
            'investment',
            'investment__property',
            'investment__customer'
        ).order_by('-calculated_at')
        
        serializer = CommissionSerializer(commissions, many=True)
        
        return Response({
            'count': commissions.count(),
            'results': serializer.data
        })


# ============================================
# LEAD MANAGEMENT
# ============================================

class CPLeadListCreateView(APIView):
    """
    GET /api/cp/leads/
    POST /api/cp/leads/
    List and create leads
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def get(self, request):
        cp = request.user.cp_profile
        
        # Get query params
        lead_status = request.query_params.get('status')
        search = request.query_params.get('search')
        
        # Get leads
        leads = cp.leads.all()
        
        if lead_status:
            leads = leads.filter(lead_status=lead_status)
        
        if search:
            leads = leads.filter(
                Q(customer_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )
        
        leads = leads.select_related('interested_property').order_by('-created_at')
        
        serializer = CPLeadSerializer(leads, many=True)
        
        return Response({
            'count': leads.count(),
            'results': serializer.data
        })
    
    def post(self, request):
        cp = request.user.cp_profile
        
        serializer = CPLeadCreateSerializer(data=request.data)
        if serializer.is_valid():
            lead = serializer.save(cp=cp)
            
            response_serializer = CPLeadSerializer(lead)
            return Response(
                {
                    'message': 'Lead created successfully',
                    'data': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CPLeadDetailView(APIView):
    """
    GET /api/cp/leads/{id}/
    PUT /api/cp/leads/{id}/
    DELETE /api/cp/leads/{id}/
    View, update, delete lead
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def get_object(self, request, lead_id):
        """Get lead and verify ownership"""
        cp = request.user.cp_profile
        return get_object_or_404(CPLead, id=lead_id, cp=cp)
    
    def get(self, request, lead_id):
        lead = self.get_object(request, lead_id)
        serializer = CPLeadSerializer(lead)
        return Response(serializer.data)
    
    def put(self, request, lead_id):
        lead = self.get_object(request, lead_id)
        
        serializer = CPLeadSerializer(lead, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Lead updated successfully',
                'data': serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, lead_id):
        lead = self.get_object(request, lead_id)
        lead.delete()
        return Response(
            {'message': 'Lead deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )


class CPLeadConvertView(APIView):
    """
    POST /api/cp/leads/{id}/convert/
    Mark lead as converted
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def post(self, request, lead_id):
        cp = request.user.cp_profile
        lead = get_object_or_404(CPLead, id=lead_id, cp=cp)
        
        # Get customer user ID from request
        customer_id = request.data.get('customer_id')
        
        if not customer_id:
            return Response(
                {'error': 'customer_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from accounts.models import User
            customer = User.objects.get(id=customer_id)
            
            # Convert lead
            relation = CPService.convert_lead_to_customer(lead, customer)
            
            serializer = CPCustomerRelationSerializer(relation)
            return Response({
                'message': 'Lead converted successfully',
                'data': serializer.data
            })
        
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid customer ID'},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================
# INVITE SYSTEM
# ============================================

class CPInviteListCreateView(APIView):
    """
    GET /api/cp/invites/
    POST /api/cp/invites/send/
    List and send invites
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def get(self, request):
        cp = request.user.cp_profile
        
        invites = cp.invites.select_related('used_by').order_by('-created_at')
        serializer = CPInviteSerializer(invites, many=True)
        
        return Response({
            'count': invites.count(),
            'results': serializer.data
        })
    
    def post(self, request):
        cp = request.user.cp_profile
        
        serializer = CPInviteCreateSerializer(data=request.data)
        if serializer.is_valid():
            invite = ReferralService.create_invite(cp, serializer.validated_data)
            
            # Generate invite link
            invite_link = ReferralService.generate_signup_invite_link(invite.invite_code)
            
            response_serializer = CPInviteSerializer(invite)
            
            return Response(
                {
                    'message': 'Invite created successfully',
                    'data': response_serializer.data,
                    'invite_link': invite_link
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CPInviteStatusView(APIView):
    """
    GET /api/cp/invites/{code}/status/
    Check invite status
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def get(self, request, code):
        cp = request.user.cp_profile
        
        invite = get_object_or_404(CPInvite, invite_code=code, cp=cp)
        serializer = CPInviteSerializer(invite)
        
        return Response(serializer.data)


# ============================================
# PERFORMANCE
# ============================================

class CPPerformanceView(APIView):
    """
    GET /api/cp/performance/
    Get CP performance metrics
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def get(self, request):
        cp = request.user.cp_profile
        
        return Response({
            'quarterly_performance': {
                'q1': str(cp.q1_performance),
                'q2': str(cp.q2_performance),
                'q3': str(cp.q3_performance),
                'q4': str(cp.q4_performance),
            },
            'targets': {
                'monthly': str(cp.monthly_target),
                'quarterly': str(cp.quarterly_target),
                'yearly': str(cp.yearly_target),
                'annual': str(cp.annual_revenue_target),
            },
            'tier': cp.partner_tier,
            'program_dates': {
                'start': cp.program_start_date,
                'end': cp.program_end_date,
            }
        })