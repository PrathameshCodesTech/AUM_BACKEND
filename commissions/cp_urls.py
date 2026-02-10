# commissions/cp_urls.py
"""
CP Commission URLs - For /api/cp/commissions/
"""
from django.urls import path
from .cp_views import (
    CPCommissionListView,
    CPCommissionStatsView,
    cp_commission_detail,
)

urlpatterns = [
    path('', CPCommissionListView.as_view(), name='cp-commission-list'),
    path('stats/', CPCommissionStatsView.as_view(), name='cp-commission-stats'),
    path('<int:commission_id>/', cp_commission_detail, name='cp-commission-detail'),
]
