# partners/admin_urls.py
from django.urls import path
from .admin_views import (
    # Applications
    AdminCPApplicationListView,
    AdminCPApplicationDetailView,
    
    # Approval/Rejection
    AdminCPApproveView,
    AdminCPRejectView,
    
    # Documents
    AdminCPDocumentsView,
    AdminCPDocumentVerifyView,
    
    # Property Authorization
    AdminCPAuthorizePropertiesView,
    AdminCPRevokePropertyView,
    
    # Commission Rules
    AdminCPAssignCommissionView,
    
    # CP Management
    AdminCPListView,
    AdminCPDetailView,
    AdminCPActivateView,
    AdminCPDeactivateView,
    
    # CP-Customer Relationships
    AdminCPCustomerRelationsView,
    AdminCPCustomerRelationExtendView,
    AdminCPCustomerRelationDeleteView,
)

urlpatterns = [
    # ============================================
    # CP APPLICATIONS
    # ============================================
    path('applications/', AdminCPApplicationListView.as_view(), name='admin-cp-applications'),
    path('applications/<int:cp_id>/', AdminCPApplicationDetailView.as_view(), name='admin-cp-application-detail'),
    
    # ============================================
    # APPROVAL/REJECTION
    # ============================================
    path('<int:cp_id>/approve/', AdminCPApproveView.as_view(), name='admin-cp-approve'),
    path('<int:cp_id>/reject/', AdminCPRejectView.as_view(), name='admin-cp-reject'),
    
    # ============================================
    # DOCUMENTS
    # ============================================
    path('<int:cp_id>/documents/', AdminCPDocumentsView.as_view(), name='admin-cp-documents'),
    path('documents/<int:doc_id>/verify/', AdminCPDocumentVerifyView.as_view(), name='admin-cp-document-verify'),
    
    # ============================================
    # PROPERTY AUTHORIZATION
    # ============================================
    path('<int:cp_id>/authorize-properties/', AdminCPAuthorizePropertiesView.as_view(), name='admin-cp-authorize-properties'),
    path('<int:cp_id>/properties/<int:property_id>/', AdminCPRevokePropertyView.as_view(), name='admin-cp-revoke-property'),
    
    # ============================================
    # COMMISSION RULES
    # ============================================
    path('<int:cp_id>/assign-commission/', AdminCPAssignCommissionView.as_view(), name='admin-cp-assign-commission'),
    
    # ============================================
    # CP LIST & MANAGEMENT
    # ============================================
    path('', AdminCPListView.as_view(), name='admin-cp-list'),
    path('<int:cp_id>/', AdminCPDetailView.as_view(), name='admin-cp-detail'),
    path('<int:cp_id>/activate/', AdminCPActivateView.as_view(), name='admin-cp-activate'),
    path('<int:cp_id>/deactivate/', AdminCPDeactivateView.as_view(), name='admin-cp-deactivate'),
    
    # ============================================
    # CP-CUSTOMER RELATIONSHIPS
    # ============================================
    path('customer-relations/', AdminCPCustomerRelationsView.as_view(), name='admin-cp-customer-relations'),
    path('customer-relations/<int:relation_id>/extend/', AdminCPCustomerRelationExtendView.as_view(), name='admin-cp-relation-extend'),
    path('customer-relations/<int:relation_id>/', AdminCPCustomerRelationDeleteView.as_view(), name='admin-cp-relation-delete'),
]