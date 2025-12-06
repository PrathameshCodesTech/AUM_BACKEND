# partners/admin_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q

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