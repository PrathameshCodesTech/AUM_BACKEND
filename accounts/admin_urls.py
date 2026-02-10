"""
Admin URLs
Accessed via /api/admin/
"""
from django.urls import path
from .admin_views import (
    AdminDashboardStatsView,
    AdminUserListView,
    AdminUserDetailView,
    AdminUserActionView,
    AdminUserCreateAPIView,
)
from accounts import admin_views

urlpatterns = [
    # Dashboard
    path('dashboard/stats/', AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),
    
    # User Management
    path('users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('users/<int:user_id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('users/<int:user_id>/action/', AdminUserActionView.as_view(), name='admin-user-action'),
    path('users/<int:user_id>/update/', admin_views.update_user, name='update_user'),
    path('users/create/', AdminUserCreateAPIView.as_view(), name='admin-user-create'),
]
