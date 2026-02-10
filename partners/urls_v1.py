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
  
    AdminCPApprovalView,
    get_permanent_invite,
    get_invite_signups,
    send_invite_email
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
    path('admin/applications/<int:cp_id>/approve/', AdminCPApprovalView.as_view(), name='admin-cp-approve'),

    path('permanent-invite/', get_permanent_invite, name='cp-permanent-invite'),
    path('invite-signups/', get_invite_signups, name='cp-invite-signups'),
    path('send-invite-email/', send_invite_email, name='send_invite_email'),
]