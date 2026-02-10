# partners/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes

from accounts.services.email_service import send_dynamic_email
from django.utils import timezone
from django.conf import settings





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
    Apply to become a Channel Partner - PUBLIC ENDPOINT
    Creates user account automatically
    """
    permission_classes = []  # ✅ PUBLIC - No authentication required
    
    def post(self, request):
        from accounts.models import User, Role
        import random
        import string
        
        data = request.data
        
        # Extract user info
        phone = data.get('phone')
        email = data.get('email')
        name = data.get('name', '')
        
        # Validate required fields
        if not phone or not email or not name:
            return Response(
                {'error': 'Name, email, and phone are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user already exists
        if User.objects.filter(phone=f'+91{phone}').exists():
            return Response(
                {'error': 'Phone number already registered'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Email already registered'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Generate random password (8 characters)
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            
            # Format phone number
            formatted_phone = f'+91{phone}'
            
            # Create user account
            user = User.objects.create(
                username=formatted_phone,
                phone=formatted_phone,
                email=email,
                first_name=name.split()[0] if name else '',
                last_name=' '.join(name.split()[1:]) if len(name.split()) > 1 else '',
                is_active=False,  # Inactive until approved
            )
            user.set_password(temp_password)
            
            # Assign Channel Partner role
            try:
                cp_role = Role.objects.get(slug='channel_partner')
                user.role = cp_role
            except Role.DoesNotExist:
                pass
            
            # Set CP flags
            user.is_cp = True
            user.cp_status = 'pending'
            user.is_active_cp = False   # 👈 NOT ACTIVE YET
            user.save()
            
            # Create CP application using service
            serializer = CPApplicationSerializer(data=data)

            
            if serializer.is_valid():
                application_data = serializer.validated_data.copy()
                application_data.pop('user', None)
                cp = CPService.create_cp_application(
                    user=user,
                    # application_data=serializer.validated_data
                    application_data=application_data

                )
                
                # TODO: Send email with credentials
                # send_cp_application_email(user, temp_password, cp)

                # ✅ Send application received email
                try:
                    send_dynamic_email(
                        email_type='cp_application_submitted',
                        to=user.email,
                        params={
                            'name': user.get_full_name() or name,
                            'email': user.email,
                            'phone': user.phone,
                            'application_id': cp.id,   # ✅ REQUIRED
                            'year': timezone.now().year
                        }
                    )
                except KeyError as e:
                    return Response(
                        {"error": str(e)},
                        status=status.HTTP_400_BAD_REQUEST
                    )


                
                return Response(
                    {
                        'success': True,
                        'message': 'Application submitted successfully. You will receive login credentials via email after approval.',
                        'application_id': cp.id,
                        # Include temp password in response (ONLY FOR TESTING - remove in production)
                        'temp_credentials': {
                            'username': formatted_phone,
                            'password': temp_password
                        }
                    },
                    status=status.HTTP_201_CREATED
                )
            
            else:
                # If application creation fails, delete the user
                user.delete()
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

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
    PATCH /api/cp/profile/  # ✅ ADDED
    Get or update CP profile
    """
    permission_classes = [IsAuthenticated, IsChannelPartner]
    
    def get(self, request):
        cp = request.user.cp_profile
        serializer = CPProfileSerializer(cp)
        return Response(serializer.data)
    
    def put(self, request):
        cp = request.user.cp_profile

    def patch(self, request):  # ✅ ADDED PATCH METHOD
        """Partial update"""
        return self._update_profile(request, partial=True)  

    def _update_profile(self, request, partial=False):
        """Shared update logic"""
        try:
            cp = request.user.cp_profile
        except ChannelPartner.DoesNotExist:
            return Response({
                'success': False,
                'error': 'CP profile not found'
            }, status=status.HTTP_404_NOT_FOUND)  
        
        # Only allow updating certain fields
        allowed_fields = [
            'business_address',
            'bank_name',
            'company_name', 
            'account_number',
            'ifsc_code',
            'account_holder_name',
            'commission_notes',
             'pan_number',  
        ]
        
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

        if not update_data:
            return Response({
                'success': False,
                'error': 'No valid fields to update'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = CPProfileSerializer(cp, data=update_data, partial=True)
        
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
        ).order_by('-created_at')
        
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
        
        # Check if bulk request
        if 'invites' in request.data:
            # BULK CREATION
            serializer = CPInviteCreateSerializer(data=request.data)
            if serializer.is_valid():
                bulk_invites = []
                
                for invite_data in serializer.validated_data['invites']:
                    invite = ReferralService.create_invite(cp, invite_data)
                    invite_link = ReferralService.generate_signup_invite_link(invite.invite_code)
                    bulk_invites.append({
                        'invite_code': invite.invite_code,
                        'invite_link': invite_link,
                        'phone': invite.phone,
                        'email': invite.email,
                        'name': invite.name,
                    })
                
                return Response(
                    {
                        'message': f'Created {len(bulk_invites)} invites successfully',
                        'invites': bulk_invites
                    },
                    status=status.HTTP_201_CREATED
                )
        
        # SINGLE INVITE (existing logic)
        serializer = CPInviteCreateSerializer(data=request.data)
        if serializer.is_valid():
            invite = ReferralService.create_invite(cp, serializer.validated_data)
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

# ============================================
# ADMIN: CP APPLICATION APPROVAL
# ============================================

class AdminCPApprovalView(APIView):
    """
    POST /api/admin/cp/applications/{cp_id}/approve/
    Admin approves CP application and activates account
    """
    permission_classes = [IsAuthenticated]  # Add IsAdminUser permission
    
    def post(self, request, cp_id):
        from accounts.models import User
        
        # Check if user is admin
        if not request.user.is_admin and not request.user.is_staff:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            cp = ChannelPartner.objects.get(id=cp_id)
            user = cp.user
            
            # Get tier from request
            tier = request.data.get('tier', 'bronze')
            notes = request.data.get('notes', '')
            
            # Update CP
            cp.onboarding_status = 'completed'
            cp.partner_tier = tier
            cp.is_verified = True
            cp.is_active = True
            if notes:
                cp.notes = notes
            cp.save()
            
            # Activate user account
            user.is_active = True
            user.is_active_cp = True
            user.cp_status = 'approved'
            user.save()
            
            # TODO: Send approval email with login credentials
            # send_cp_approval_email(user, cp)
            # print("sednig sexyt mai")
            # ✅ Send CP approval email
            try:
                send_dynamic_email(
                    email_type='cp_application_approved',
                    to=user.email,
                    params={
                        'name': user.get_full_name() or user.username,
                        'cp_code': cp.cp_code,
                        'tier': cp.partner_tier,
                        # 'dashboard_url': settings.CP_DASHBOARD_URL,
                        'year': timezone.now().year
                    }
                )
            except Exception as e:
                return Response(
                    {"error": f"Approval email failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response({
                'success': True,
                'message': f'CP application approved. User account activated.',
                'data': {
                    'cp_code': cp.cp_code,
                    'tier': cp.partner_tier,
                    'user_active': user.is_active
                }
            })
        
        except ChannelPartner.DoesNotExist:
            return Response(
                {'error': 'CP application not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsChannelPartner])
def get_permanent_invite(request):
    """
    GET /api/cp/permanent-invite/
    Get CP's permanent invite link and stats
    """
    from partners.models import CPInvite, CPCustomerRelation
    from commissions.models import Commission
    from investments.models import Investment
    from django.db.models import Sum, Count
    
    cp = request.user.cp_profile
    
    # Get or create permanent invite
    invite = CPInvite.objects.filter(
        cp=cp,
        is_permanent=True
    ).first()
    
    if not invite:
        return Response({
            'success': False,
            'error': 'No permanent invite found. Contact admin to create one.',
            'has_invite': False
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Generate invite link
    from partners.services.referral_service import ReferralService
    invite_link = ReferralService.generate_signup_invite_link(invite.invite_code)
    
    # Get stats - all users who signed up via this invite
    relations = CPCustomerRelation.objects.filter(
        cp=cp,
        referral_code=invite.invite_code,
        is_active=True
    )
    
    total_signups = relations.count()
    
    # Get customers who invested
    customer_ids = relations.values_list('customer_id', flat=True)
    
    investments = Investment.objects.filter(
        customer_id__in=customer_ids,
        status__in=['pending', 'approved', 'active', 'completed']
    )
    
    invested_customers = investments.values('customer').distinct().count()
    total_investment = investments.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Commission stats
    commissions = Commission.objects.filter(
        cp=cp,
        investment__customer_id__in=customer_ids
    )
    
    total_commission = commissions.filter(
        status__in=['approved', 'paid']
    ).aggregate(Sum('net_amount'))['net_amount__sum'] or 0
    
    commission_pending = commissions.filter(
        status='pending'
    ).aggregate(Sum('net_amount'))['net_amount__sum'] or 0
    
    commission_paid = commissions.filter(
        status='paid'
    ).aggregate(Sum('net_amount'))['net_amount__sum'] or 0
    
    return Response({
        'success': True,
        'has_invite': True,
        'data': {
            'invite_code': invite.invite_code,
            'invite_link': invite_link,
            'cp_code': cp.cp_code,
            'cp_name': cp.user.get_full_name(),
            'stats': {
                'total_signups': total_signups,
                'invested_customers': invested_customers,
                'conversion_rate': round((invested_customers / total_signups * 100), 2) if total_signups > 0 else 0,
                'total_investment': float(total_investment),
                'total_commission': float(total_commission),
                'commission_pending': float(commission_pending),
                'commission_paid': float(commission_paid),
            }
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsChannelPartner])
def get_invite_signups(request):
    """
    GET /api/cp/invite-signups/
    Get list of users who signed up via CP's permanent invite
    """
    from partners.models import CPInvite, CPCustomerRelation
    from investments.models import Investment
    from commissions.models import Commission
    from django.db.models import Sum, Q
    
    cp = request.user.cp_profile
    
    # Get permanent invite
    invite = CPInvite.objects.filter(
        cp=cp,
        is_permanent=True
    ).first()
    
    if not invite:
        return Response({
            'success': False,
            'error': 'No permanent invite found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Query params
    status_filter = request.query_params.get('status')  # 'signed_up', 'invested'
    search = request.query_params.get('search')
    
    # Get all relations via this invite
    relations = CPCustomerRelation.objects.filter(
        cp=cp,
        referral_code=invite.invite_code,
        is_active=True
    ).select_related('customer').order_by('-referral_date')
    
    # Search filter
    if search:
        relations = relations.filter(
            Q(customer__first_name__icontains=search) |
            Q(customer__last_name__icontains=search) |
            Q(customer__phone__icontains=search) |
            Q(customer__email__icontains=search)
        )
    
    # Build response
    signups = []
    
    for relation in relations:
        customer = relation.customer
        
        # Get investment info
        investments = Investment.objects.filter(
            customer=customer,
            status__in=['pending', 'approved', 'active', 'completed']
        )
        
        has_invested = investments.exists()
        total_invested = investments.aggregate(Sum('amount'))['amount__sum'] or 0
        investment_count = investments.count()
        
        # Determine status
        signup_status = 'invested' if has_invested else 'signed_up'
        
        # Apply status filter
        if status_filter and status_filter != signup_status:
            continue
        
        # Get commission info
        commission_earned = Commission.objects.filter(
            cp=cp,
            investment__customer=customer,
            status__in=['approved', 'paid']
        ).aggregate(Sum('net_amount'))['net_amount__sum'] or 0
        
        signups.append({
            'id': relation.id,
            'customer_id': customer.id,
            'customer_name': customer.get_full_name() or customer.username,
            'customer_phone': customer.phone,
            'customer_email': customer.email,
            'signup_date': relation.referral_date,
            'status': signup_status,
            'has_invested': has_invested,
            'investment_count': investment_count,
            'total_invested': float(total_invested),
            'commission_earned': float(commission_earned),
        })
    
    return Response({
        'success': True,
        'count': len(signups),
        'data': signups
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_invite_email(request):
    """
    POST /api/cp/send-invite-email/
    Body: { "email": "recipient@example.com" }
    
    CP sends invite email to a recipient with their permanent invite link
    """
    # Check if user is CP
    if not hasattr(request.user, 'cp_profile'):
        return Response({
            'success': False,
            'error': 'User is not a Channel Partner'
        }, status=status.HTTP_403_FORBIDDEN)
    
    cp = request.user.cp_profile
    recipient_email = request.data.get('email')
    
    # Validate email
    if not recipient_email:
        return Response({
            'success': False,
            'error': 'Email address is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate email format
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    try:
        validate_email(recipient_email)
    except ValidationError:
        return Response({
            'success': False,
            'error': 'Invalid email address format'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get CP's permanent invite
    invite = CPInvite.objects.filter(
        cp=cp,
        is_permanent=True,
        is_expired=False
    ).first()
    
    if not invite:
        return Response({
            'success': False,
            'error': 'No active permanent invite found. Please contact admin.'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Generate invite link (frontend URL)
    invite_link = f"http://localhost:5173/signup?invite={invite.invite_code}"
    
    # Get CP name
    cp_name = request.user.get_full_name() or request.user.username or f"Channel Partner {cp.cp_code}"
    
    try:
        # Import email service
        from accounts.services.email_service import send_dynamic_email
        
        # Send email
        send_dynamic_email(
            email_type='cp_referral_invite',
            to=recipient_email,
            params={
                'cp_name': cp_name,
                'invite_link': invite_link,
                'website': 'https://assetkart.com',
                'support_email': 'support@assetkart.com'
            }
        )
        
        return Response({
            'success': True,
            'message': f'Invitation successfully sent to {recipient_email}',
            'recipient': recipient_email
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to send email: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

# partners/views.py
# Add this view at the end of your file

# ============================================
# ADMIN: GET CP LEADS
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_get_cp_leads(request, cp_id):
    """
    GET /api/admin/cp/{cp_id}/leads/
    Admin gets all leads added by a specific CP
    """
    # Check if user is admin
    if not request.user.is_admin and not request.user.is_staff:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Get CP
        cp = ChannelPartner.objects.get(id=cp_id)
        
        # Get query params
        lead_status = request.query_params.get('status')
        search = request.query_params.get('search')
        
        # Get leads
        leads = CPLead.objects.filter(cp=cp)
        
        if lead_status:
            leads = leads.filter(lead_status=lead_status)
        
        if search:
            leads = leads.filter(
                Q(customer_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )
        
        leads = leads.select_related('interested_property').order_by('-created_at')
        
        # Serialize leads
        serializer = CPLeadSerializer(leads, many=True)
        
        return Response({
            'success': True,
            'count': leads.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    
    except ChannelPartner.DoesNotExist:
        return Response(
            {'error': 'CP not found'},
            status=status.HTTP_404_NOT_FOUND
        )


