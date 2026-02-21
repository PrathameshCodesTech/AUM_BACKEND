"""
Investment Admin URLs
Accessed via /api/admin/investments/
"""
from django.urls import path
from .admin_views import (
    AdminInvestmentStatsView,
    AdminInvestmentListView,
    AdminInvestmentDetailView,
    AdminInvestmentActionView,
    AdminInvestmentsByPropertyView,
    AdminInvestmentsByCustomerView,
    CreateInvestmentView,
    AdminInvestmentReceiptsView,
    AdminDownloadReceiptView,
    # Instalment payment management
    AdminInvestmentPaymentsView,
    AdminApprovePaymentView,
    AdminRejectPaymentView,
    AdminDownloadPaymentReceiptView,
    AdminAddInstalmentPaymentView,
)

urlpatterns = [
    # Investment Statistics
    path('stats/', AdminInvestmentStatsView.as_view(), name='admin-investment-stats'),
    
    # Investment Management
    path('', AdminInvestmentListView.as_view(), name='admin-investment-list'),
    path('<int:investment_id>/', AdminInvestmentDetailView.as_view(), name='admin-investment-detail'),
    path('<int:investment_id>/action/', AdminInvestmentActionView.as_view(), name='admin-investment-action'),
    path('create/', CreateInvestmentView.as_view(), name='create-investment'),
    
    # Filtered Views
    path('by-property/<int:property_id>/', AdminInvestmentsByPropertyView.as_view(), name='admin-investments-by-property'),
    path('by-customer/<int:customer_id>/', AdminInvestmentsByCustomerView.as_view(), name='admin-investments-by-customer'),

    # Receipt Management
    path('receipts/', AdminInvestmentReceiptsView.as_view(), name='admin-receipts-list'),
    path('<int:investment_id>/receipt/download/', AdminDownloadReceiptView.as_view(), name='admin-receipt-download'),

    # Instalment Payment Management
    path('<int:investment_id>/payments/', AdminInvestmentPaymentsView.as_view(), name='admin-investment-payments'),
    path('<int:investment_id>/add-payment/', AdminAddInstalmentPaymentView.as_view(), name='admin-add-payment'),
    path('<int:investment_id>/payments/<int:payment_id>/approve/', AdminApprovePaymentView.as_view(), name='admin-approve-payment'),
    path('<int:investment_id>/payments/<int:payment_id>/reject/', AdminRejectPaymentView.as_view(), name='admin-reject-payment'),
    path('<int:investment_id>/payments/<int:payment_id>/receipt/download/', AdminDownloadPaymentReceiptView.as_view(), name='admin-payment-receipt-download'),
]