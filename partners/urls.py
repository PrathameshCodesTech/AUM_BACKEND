# partners/urls.py
from django.urls import path
from .views import (
    # Application & Profile
    CPApplicationView,
    CPApplicationStatusView,
    CPProfileView,
    
    # Documents
    CPDocumentUploadView,
    CPDocumentListView,
    
    # Dashboard
    CPDashboardStatsView,
    
    # Properties
    CPAuthorizedPropertiesView,
    CPPropertyReferralLinkView,
    
    # Customers
    CPCustomersView,
    
    # Commissions
    CPCommissionsView,
    
    # Leads
    CPLeadListCreateView,
    CPLeadDetailView,
    CPLeadConvertView,
    
    # Invites
    CPInviteListCreateView,
    CPInviteStatusView,
    
    # Performance
    CPPerformanceView,
)

urlpatterns = [
    # ============================================
    # CP APPLICATION & PROFILE
    # ============================================
    path('apply/', CPApplicationView.as_view(), name='cp-apply'),
    path('application-status/', CPApplicationStatusView.as_view(), name='cp-application-status'),
    path('profile/', CPProfileView.as_view(), name='cp-profile'),
    
    # ============================================
    # DOCUMENTS
    # ============================================
    path('documents/upload/', CPDocumentUploadView.as_view(), name='cp-document-upload'),
    path('documents/', CPDocumentListView.as_view(), name='cp-documents'),
    
    # ============================================
    # DASHBOARD
    # ============================================
    path('dashboard/stats/', CPDashboardStatsView.as_view(), name='cp-dashboard-stats'),
    path('performance/', CPPerformanceView.as_view(), name='cp-performance'),
    
    # ============================================
    # PROPERTIES
    # ============================================
    path('properties/', CPAuthorizedPropertiesView.as_view(), name='cp-authorized-properties'),
    path('properties/<int:property_id>/referral-link/', CPPropertyReferralLinkView.as_view(), name='cp-property-referral-link'),
    
    # ============================================
    # CUSTOMERS
    # ============================================
    path('customers/', CPCustomersView.as_view(), name='cp-customers'),
    
    # ============================================
    # COMMISSIONS
    # ============================================
    path('commissions/', CPCommissionsView.as_view(), name='cp-commissions'),
    
    # ============================================
    # LEAD MANAGEMENT
    # ============================================
    path('leads/', CPLeadListCreateView.as_view(), name='cp-leads'),
    path('leads/<int:lead_id>/', CPLeadDetailView.as_view(), name='cp-lead-detail'),
    path('leads/<int:lead_id>/convert/', CPLeadConvertView.as_view(), name='cp-lead-convert'),
    
    # ============================================
    # INVITE SYSTEM
    # ============================================
    path('invites/', CPInviteListCreateView.as_view(), name='cp-invites'),
    path('invites/<str:code>/status/', CPInviteStatusView.as_view(), name='cp-invite-status'),
]