# accounts/urls.py
from django.urls import path
from accounts import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('auth/send-otp/', views.send_otp, name='send-otp'),
    path('auth/verify-otp/', views.verify_otp, name='verify-otp'),
    path('auth/register/', views.complete_registration, name='register'),
    path('auth/me/', views.get_current_user, name='current-user'),
    path('auth/logout/', views.logout, name='logout'),
]