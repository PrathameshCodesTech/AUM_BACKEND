"""
Admin KYC URLs
Accessed via /api/admin/kyc/
"""
from django.urls import path
from .views import (
    PendingKYCListView,
    KYCDetailView,
    KYCApprovalView,
    AllKYCListView,
)

urlpatterns = [
    # KYC Management
    path('pending/', PendingKYCListView.as_view(), name='admin-pending-kyc'),
    path('all/', AllKYCListView.as_view(), name='admin-all-kyc'),
    path('<int:kyc_id>/', KYCDetailView.as_view(), name='admin-kyc-detail'),  # 👈 NEW
    path('<int:kyc_id>/action/', KYCApprovalView.as_view(), name='admin-kyc-action'),
]