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
    AdminAadhaarLockView,
    AdminPANLockView,
)

urlpatterns = [
    # KYC Management
    path('pending/', PendingKYCListView.as_view(), name='admin-pending-kyc'),
    path('all/', AllKYCListView.as_view(), name='admin-all-kyc'),
    path('<int:kyc_id>/', KYCDetailView.as_view(), name='admin-kyc-detail'),
    path('<int:kyc_id>/action/', KYCApprovalView.as_view(), name='admin-kyc-action'),
    path('<int:kyc_id>/aadhaar/lock/', AdminAadhaarLockView.as_view(), name='admin-aadhaar-lock'),
    path('<int:kyc_id>/pan/lock/', AdminPANLockView.as_view(), name='admin-pan-lock'),
]