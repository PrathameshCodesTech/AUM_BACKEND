# accounts/urls.py
from django.urls import path
from accounts import views
from accounts.views import CompleteProfileView,PortfolioView,DashboardStatsView,list_all_users
from .mail_view import SendEmailAPI


app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('auth/send-otp/', views.send_otp, name='send-otp'),
    path('auth/verify-otp/', views.verify_otp, name='verify-otp'),
    path('auth/register/', views.complete_registration, name='register'),
    path('auth/me/', views.get_current_user, name='current-user'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/complete-profile/', CompleteProfileView.as_view(), name='complete-profile'),
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('portfolio/<str:portfolio_type>/', PortfolioView.as_view(), name='portfolio'),
    path('auth/users/', views.list_all_users, name='list-users'), 
    path("send/", SendEmailAPI.as_view(), name="send-email"),
]