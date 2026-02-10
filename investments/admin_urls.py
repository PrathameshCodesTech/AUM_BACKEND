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
    AdminInvestmentReceiptsView,  # 🆕 NEW
    AdminDownloadReceiptView,     # 🆕 NEW
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

     # 🆕 Receipt Management
    path('receipts/', AdminInvestmentReceiptsView.as_view(), name='admin-receipts-list'),
    path('<int:investment_id>/receipt/download/', AdminDownloadReceiptView.as_view(), name='admin-receipt-download'),
]