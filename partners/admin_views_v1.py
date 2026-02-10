# partners/admin_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from accounts.models import User, Role
from rest_framework.decorators import api_view, permission_classes


from accounts.permissions import IsAdmin
from .models import (
    ChannelPartner,
    CPCustomerRelation,
    CPPropertyAuthorization,
    CPDocument,
    CommissionRule,
    CPCommissionRule
)
from .serializers import (
    CPListSerializer,
    CPProfileSerializer,
    CPApprovalSerializer,
    CPRejectionSerializer,
    CPCustomerRelationSerializer,
    CPPropertyAuthorizationSerializer,
    AuthorizePropertiesSerializer,
    CPDocumentSerializer,
    DocumentVerifySerializer,
    CommissionRuleSerializer,
    CPCommissionRuleSerializer,
    AssignCommissionRuleSerializer,
    AdminCreateCPSerializer
)
from .services.cp_service import CPService
from properties.models import Property


# ============================================
# CP APPLICATIONS
# ============================================

class AdminCPApplicationListView(APIView):
    """
    GET /api/admin/cp/applications/
    List pending CP applications
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        # Get query params
        onboarding_status = request.query_params.get('status', 'pending')
        search = request.query_params.get('search')
        
        # Get applications
        applications = ChannelPartner.objects.select_related('user').all()
        
        if onboarding_status:
            applications = applications.filter(onboarding_status=onboarding_status)
        
        if search:
            applications = applications.filter(
                Q(cp_code__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__phone__icontains=search) |
                Q(company_name__icontains=search)
            )
        
        applications = applications.order_by('-created_at')
        
        serializer = CPListSerializer(applications, many=True)
        
        return Response({
            'count': applications.count(),
            'results': serializer.data
        })


class AdminCPApplicationDetailView(APIView):
    """
    GET /api/admin/cp/applications/{id}/
    View single CP application details
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, cp_id):
        cp = get_object_or_404(ChannelPartner, id=cp_id)
        serializer = CPProfileSerializer(cp)
        return Response(serializer.data)


# ============================================
# CP APPROVAL/REJECTION
# ============================================

class AdminCPApproveView(APIView):
    """
    POST /api/admin/cp/{id}/approve/
    Approve CP application
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, cp_id):
        cp = get_object_or_404(ChannelPartner, id=cp_id)
        
        # Check if already approved
        if cp.is_verified:
            return Response(
                {'error': 'CP already approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CPApprovalSerializer(data=request.data)
        if serializer.is_valid():
            # Approve CP
            cp = CPService.approve_cp(
                cp=cp,
                approved_by=request.user,
                approval_data=serializer.validated_data
            )

             # ✅ ACTIVATE USER ACCOUNT
            user = cp.user
            user.is_active = True
            user.is_active_cp = True
            user.cp_status = 'approved'
            user.save()
            
            response_serializer = CPProfileSerializer(cp)
            return Response({
                'message': 'CP approved successfully',
                'data': response_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminCPRejectView(APIView):
    """
    POST /api/admin/cp/{id}/reject/
    Reject CP application
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, cp_id):
        cp = get_object_or_404(ChannelPartner, id=cp_id)
        
        serializer = CPRejectionSerializer(data=request.data)
        if serializer.is_valid():
            # Reject CP
            cp = CPService.reject_cp(
                cp=cp,
                rejected_by=request.user,
                rejection_reason=serializer.validated_data['rejection_reason']
            )
            
            response_serializer = CPProfileSerializer(cp)
            return Response({
                'message': 'CP rejected',
                'data': response_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# DOCUMENT VERIFICATION
# ============================================

class AdminCPDocumentsView(APIView):
    """
    GET /api/admin/cp/{id}/documents/
    List CP documents
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, cp_id):
        cp = get_object_or_404(ChannelPartner, id=cp_id)
        documents = cp.documents.all()
        serializer = CPDocumentSerializer(documents, many=True)
        return Response(serializer.data)


class AdminCPDocumentVerifyView(APIView):
    """
    POST /api/admin/cp/documents/{doc_id}/verify/
    Verify or reject document
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, doc_id):
        document = get_object_or_404(CPDocument, id=doc_id)
        
        serializer = DocumentVerifySerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data['status'] == 'approved':
                document.approve_document(request.user)
            else:
                document.reject_document(
                    request.user,
                    serializer.validated_data.get('rejection_reason', '')
                )
            
            response_serializer = CPDocumentSerializer(document)
            return Response({
                'message': f"Document {serializer.validated_data['status']}",
                'data': response_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# PROPERTY AUTHORIZATION
# ============================================

class AdminCPAuthorizePropertiesView(APIView):
    """
    POST /api/admin/cp/{id}/authorize-properties/
    Authorize CP for properties
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, cp_id):
        cp = get_object_or_404(ChannelPartner, id=cp_id)
        
        serializer = AuthorizePropertiesSerializer(data=request.data)
        if serializer.is_valid():
            property_ids = serializer.validated_data['property_ids']
            
            # Create authorizations
            authorizations = []
            for property_id in property_ids:
                property_obj = Property.objects.get(id=property_id)
                
                auth, created = CPPropertyAuthorization.objects.get_or_create(
                    cp=cp,
                    property=property_obj,
                    defaults={
                        'is_authorized': True,
                        'approval_status': 'approved',
                        'authorized_by': request.user,
                    }
                )
                
                # Generate referral link
                auth.generate_referral_link()
                
                authorizations.append(auth)
            
            response_serializer = CPPropertyAuthorizationSerializer(
                authorizations, many=True
            )
            
            return Response({
                'message': f'{len(authorizations)} properties authorized',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminCPRevokePropertyView(APIView):
    """
    DELETE /api/admin/cp/{cp_id}/properties/{property_id}/
    Revoke property authorization
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def delete(self, request, cp_id, property_id):
        cp = get_object_or_404(ChannelPartner, id=cp_id)
        
        authorization = get_object_or_404(
            CPPropertyAuthorization,
            cp=cp,
            property_id=property_id
        )
        
        authorization.is_authorized = False
        authorization.approval_status = 'revoked'
        authorization.save()
        
        return Response({
            'message': 'Property authorization revoked'
        })


# ============================================
# COMMISSION RULE ASSIGNMENT
# ============================================

class AdminCPAssignCommissionView(APIView):
    """
    POST /api/admin/cp/{id}/assign-commission/
    Assign commission rule to CP
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, cp_id):
        cp = get_object_or_404(ChannelPartner, id=cp_id)
        
        serializer = AssignCommissionRuleSerializer(data=request.data)
        if serializer.is_valid():
            rule_id = serializer.validated_data['commission_rule_id']
            property_id = serializer.validated_data.get('property_id')
            
            rule = CommissionRule.objects.get(id=rule_id)
            
            # Check if already assigned
            existing = CPCommissionRule.objects.filter(
                cp=cp,
                commission_rule=rule,
                property_id=property_id
            ).first()
            
            if existing:
                return Response(
                    {'error': 'Commission rule already assigned'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create assignment
            assignment = CPCommissionRule.objects.create(
                cp=cp,
                commission_rule=rule,
                property_id=property_id,
                assigned_by=request.user
            )
            
            response_serializer = CPCommissionRuleSerializer(assignment)
            return Response({
                'message': 'Commission rule assigned successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# CP LIST & MANAGEMENT
# ============================================

class AdminCPListView(APIView):
    """
    GET /api/admin/cp/
    List all CPs with filters
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        # Get query params
        is_verified = request.query_params.get('is_verified')
        is_active = request.query_params.get('is_active')
        partner_tier = request.query_params.get('tier')
        search = request.query_params.get('search')
        
        # Get CPs
        cps = ChannelPartner.objects.select_related('user').all()
        
        if is_verified is not None:
            cps = cps.filter(is_verified=is_verified.lower() == 'true')
        
        if is_active is not None:
            cps = cps.filter(is_active=is_active.lower() == 'true')
        
        if partner_tier:
            cps = cps.filter(partner_tier=partner_tier)
        
        if search:
            cps = cps.filter(
                Q(cp_code__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(company_name__icontains=search)
            )
        
        cps = cps.order_by('-created_at')
        
        serializer = CPListSerializer(cps, many=True)
        
        return Response({
            'count': cps.count(),
            'results': serializer.data
        })


class AdminCPDetailView(APIView):
    """
    GET /api/admin/cp/{id}/
    PUT /api/admin/cp/{id}/
    View and update CP details
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, cp_id):
        cp = get_object_or_404(ChannelPartner, id=cp_id)
        serializer = CPProfileSerializer(cp)
        return Response(serializer.data)
    
    def put(self, request, cp_id):
        cp = get_object_or_404(ChannelPartner, id=cp_id)
        
        serializer = CPProfileSerializer(cp, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(last_modified_by=request.user)
            return Response({
                'message': 'CP updated successfully',
                'data': serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminCPActivateView(APIView): 
    """
    POST /api/admin/cp/{id}/activate/
    Activate CP
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, cp_id):
        cp = get_object_or_404(ChannelPartner, id=cp_id)
        cp.is_active = True
        cp.save()

                # ✅ ACTIVATE USER ACCOUNT
        user = cp.user
        user.is_active = True
        user.is_active_cp = True
        user.save()
        
        return Response({
            'message': 'CP activated successfully'
        })


class AdminCPDeactivateView(APIView):
    """
    POST /api/admin/cp/{id}/deactivate/
    Deactivate CP
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, cp_id):
        cp = get_object_or_404(ChannelPartner, id=cp_id)
        cp.is_active = False
        cp.save()

                # ✅ DEACTIVATE USER ACCOUNT
        user = cp.user
        user.is_active = False  # 👈 THIS PREVENTS LOGIN
        user.is_active_cp = False
        user.save()
        
        return Response({
            'message': 'CP deactivated successfully'
        })


# ============================================
# CP-CUSTOMER RELATIONSHIP MANAGEMENT
# ============================================

class AdminCPCustomerRelationsView(APIView):
    """
    GET /api/admin/cp-customer-relations/
    View all CP-customer relationships
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        # Get query params
        is_active = request.query_params.get('is_active')
        is_expired = request.query_params.get('is_expired')
        cp_id = request.query_params.get('cp_id')
        
        # Get relations
        relations = CPCustomerRelation.objects.select_related('cp', 'customer').all()
        
        if is_active is not None:
            relations = relations.filter(is_active=is_active.lower() == 'true')
        
        if is_expired is not None:
            relations = relations.filter(is_expired=is_expired.lower() == 'true')
        
        if cp_id:
            relations = relations.filter(cp_id=cp_id)
        
        relations = relations.order_by('-referral_date')
        
        serializer = CPCustomerRelationSerializer(relations, many=True)
        
        return Response({
            'count': relations.count(),
            'results': serializer.data
        })


class AdminCPCustomerRelationExtendView(APIView):
    """
    POST /api/admin/cp-customer-relations/{id}/extend/
    Extend relationship validity
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, relation_id):
        relation = get_object_or_404(CPCustomerRelation, id=relation_id)
        
        days = request.data.get('days', 90)
        
        try:
            days = int(days)
            relation.extend_validity(days)
            
            serializer = CPCustomerRelationSerializer(relation)
            return Response({
                'message': f'Relationship extended by {days} days',
                'data': serializer.data
            })
        
        except ValueError:
            return Response(
                {'error': 'Invalid days value'},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminCPCustomerRelationDeleteView(APIView):
    """
    DELETE /api/admin/cp-customer-relations/{id}/
    Break CP-customer relationship
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def delete(self, request, relation_id):
        relation = get_object_or_404(CPCustomerRelation, id=relation_id)
        relation.is_active = False
        relation.save()
        
        return Response({
            'message': 'Relationship deactivated'
        })


class AdminCPAuthorizedPropertiesView(APIView):
    """
    GET /api/admin/cp/{id}/properties/
    List authorized properties for a CP
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, cp_id):
        cp = get_object_or_404(ChannelPartner, id=cp_id)
        
        authorizations = CPPropertyAuthorization.objects.filter(
            cp=cp,
            is_authorized=True
        ).select_related('property').order_by('-authorized_at')
        
        serializer = CPPropertyAuthorizationSerializer(authorizations, many=True)
        
        return Response({
            'success': True,
            'results': serializer.data,
            'count': authorizations.count()
        })
    

class AdminCreateCPView(APIView):
    """
    POST /api/admin/cp/create/
    Admin manually creates a CP with complete details
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @transaction.atomic
    def post(self, request):
        serializer = AdminCreateCPSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        
        try:
            # Extract data
            data = serializer.validated_data
            
            # ============================================
            # 0. EXTRACT auto_approve FIRST (MOVE HERE!)
            # ============================================
            auto_approve = data.pop('auto_approve', True)  # 👈 EXTRACT IT FIRST
            property_ids = data.pop('property_ids', [])    # 👈 EXTRACT THESE TOO
            
            # ============================================
            # 1. CREATE USER ACCOUNT
            # ============================================
            import random
            import string
            
            # Generate password
            password = data.pop('password', None)
            if not password:
                password = ''.join(random.choices(
                    string.ascii_letters + string.digits + string.punctuation, 
                    k=12
                ))
            
            # Extract user fields
            first_name = data.pop('first_name')
            last_name = data.pop('last_name')
            email = data.pop('email')
            phone = data.pop('phone')
            
            # Create user
            user = User.objects.create(
                username=phone,
                phone=phone,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=auto_approve,
                phone_verified=True,
            )
            user.set_password(password)
            
            # Assign role
            try:
                cp_role = Role.objects.get(slug='channel_partner')
                user.role = cp_role
            except Role.DoesNotExist:
                pass
            
            # 👇 NOW auto_approve IS AVAILABLE!
            user.is_cp = True
            user.cp_status = 'approved' if auto_approve else 'pending'
            user.is_active_cp = auto_approve
            user.save()
            
            # ============================================
            # 2. CREATE CHANNEL PARTNER PROFILE
            # ============================================
            # (auto_approve and property_ids already extracted above)
        
            
            # ============================================
            # 2. CREATE CHANNEL PARTNER PROFILE
            # ============================================
            
            # Extract property_ids and auto_approve before creating CP
            property_ids = data.pop('property_ids', [])
            auto_approve = data.pop('auto_approve', True)
            
            # Generate CP code
            from partners.services.cp_service import CPService
            cp_code = CPService.generate_cp_code()
            
            # Set default program start date if auto-approve
            if auto_approve and not data.get('program_start_date'):
                data['program_start_date'] = timezone.now().date()
            
            # Create CP profile
            cp = ChannelPartner.objects.create(
                user=user,
                cp_code=cp_code,
                onboarding_status='completed' if auto_approve else 'pending',
                is_verified=auto_approve,
                is_active=auto_approve,
                verified_by=request.user if auto_approve else None,
                verified_at=timezone.now() if auto_approve else None,
                created_by=request.user,
                onboarded_by=request.user,
                **data  # All remaining CP fields
            )
            
            # ============================================
            # 3. AUTHORIZE PROPERTIES (If provided)
            # ============================================
            authorized_properties = []
            if property_ids:
                from properties.models import Property
                
                for property_id in property_ids:
                    try:
                        property_obj = Property.objects.get(id=property_id)
                        
                        auth = CPPropertyAuthorization.objects.create(
                            cp=cp,
                            property=property_obj,
                            is_authorized=True,
                            approval_status='approved',
                            authorized_by=request.user,
                        )
                        
                        # Generate referral link
                        auth.generate_referral_link()
                        authorized_properties.append(auth)
                        
                    except Property.DoesNotExist:
                        continue
            
            # ============================================
            # 4. SEND CREDENTIALS EMAIL (TODO)
            # ============================================
            # TODO: Send email with login credentials
            # send_cp_credentials_email(user, password, cp)
            
            # ============================================
            # 5. RETURN RESPONSE
            # ============================================
            cp_serializer = CPProfileSerializer(cp)
            
            return Response({
                'success': True,
                'message': f'CP created successfully. CP Code: {cp.cp_code}',
                'data': cp_serializer.data,
                'credentials': {
                    'username': phone,
                    'password': password,  # ⚠️ ONLY for immediate display to admin
                    'email': email
                },
                'authorized_properties_count': len(authorized_properties)
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Failed to create CP'
            }, status=status.HTTP_400_BAD_REQUEST)
        


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_create_permanent_invite(request, cp_id):
    """
    POST /api/admin/cp/{cp_id}/create-permanent-invite/
    Admin creates a permanent invite for a CP
    """
    # Check if user is admin
    if not request.user.is_admin and not request.user.is_staff:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        from partners.models import ChannelPartner, CPInvite
        from django.utils import timezone
        
        cp = ChannelPartner.objects.get(id=cp_id)
        
        # Check if CP already has a permanent invite
        existing = CPInvite.objects.filter(
            cp=cp,
            is_permanent=True
        ).first()
        
        if existing:
            return Response({
                'success': False,
                'error': 'CP already has a permanent invite',
                'data': {
                    'invite_code': existing.invite_code,
                    'invite_link': f"http://localhost:5173/signup?invite={existing.invite_code}"
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create permanent invite using CP code
        invite = CPInvite.objects.create(
            cp=cp,
            invite_code=cp.cp_code,  # Use CP code as invite code
            phone='',  # Empty for permanent
            email='',  # Empty for permanent
            name='',   # Empty for permanent
            is_permanent=True,
            is_used=False,
            is_expired=False,
            expiry_date=None  # Never expires
        )
        
        from partners.services.referral_service import ReferralService
        invite_link = ReferralService.generate_signup_invite_link(invite.invite_code)
        
        return Response({
            'success': True,
            'message': 'Permanent invite created successfully',
            'data': {
                'invite_code': invite.invite_code,
                'invite_link': invite_link,
                'cp_code': cp.cp_code,
                'cp_name': cp.user.get_full_name()
            }
        }, status=status.HTTP_201_CREATED)
    
    except ChannelPartner.DoesNotExist:
        return Response(
            {'error': 'CP not found'},
            status=status.HTTP_404_NOT_FOUND
        )
