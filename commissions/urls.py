# commissions/urls.py
"""
Commission URLs
Accessed via /api/admin/commissions/
"""
from django.urls import path
from .admin_views import (
    AdminCommissionListView,
    AdminCommissionStatsView,
    AdminCommissionDetailView,
    AdminCommissionsByCPView,
    approve_commission,
    process_payout,
    bulk_payout,
)

urlpatterns = [
    # List & Stats
    path('', AdminCommissionListView.as_view(), name='admin-commission-list'),
    path('stats/', AdminCommissionStatsView.as_view(), name='admin-commission-stats'),
    
    # Detail
    path('<int:commission_id>/', AdminCommissionDetailView.as_view(), name='admin-commission-detail'),
    
    # Actions
    path('<int:commission_id>/approve/', approve_commission, name='approve-commission'),
    path('<int:commission_id>/payout/', process_payout, name='process-payout'),
    path('bulk-payout/', bulk_payout, name='bulk-payout'),
    
    # By CP
    path('by-cp/<int:cp_id>/', AdminCommissionsByCPView.as_view(), name='admin-commissions-by-cp'),
]