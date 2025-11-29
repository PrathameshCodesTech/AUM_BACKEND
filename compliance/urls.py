"""
KYC URLs
Routes for KYC verification APIs
"""
from django.urls import path
from .views import (
    # Aadhaar
     
    AadhaarPDFUploadView,
    # PAN
    PANVerifyView,
    
    # Bank
    BankVerifyView,
    # User KYC
    MyKYCView,
    MyKYCStatusView,
    # Admin
    PendingKYCListView,
    KYCApprovalView,
    AllKYCListView,
 
)

app_name = 'compliance'

urlpatterns = [
    # ========================================
    # AADHAAR VERIFICATION
    # ========================================
     path('aadhaar/upload-pdf/',
     AadhaarPDFUploadView.as_view(),
     name='aadhaar-upload-pdf'),

    # ========================================
    # PAN VERIFICATION
    # ========================================
    path('pan/verify/',
         PANVerifyView.as_view(),
         name='pan-verify'),


    # ========================================
    # BANK VERIFICATION
    # ========================================
    path('bank/verify/',
         BankVerifyView.as_view(),
         name='bank-verify'),

    # ========================================
    # USER KYC
    # ========================================
    path('me/',
         MyKYCView.as_view(),
         name='my-kyc'),
    path('status/',
         MyKYCStatusView.as_view(),
         name='my-kyc-status'),

    # ========================================
    # ADMIN
    # ========================================
    path('admin/pending/',
         PendingKYCListView.as_view(),
         name='admin-pending-kyc'),
    path('admin/all/',
         AllKYCListView.as_view(),
         name='admin-all-kyc'),
    path('admin/<int:kyc_id>/action/',
         KYCApprovalView.as_view(),
         name='admin-kyc-action'),
]
