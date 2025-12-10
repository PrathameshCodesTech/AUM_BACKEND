# aum_backend/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path('api/', include('accounts.urls')),
    
    # KYC
    path('api/kyc/', include('compliance.urls')),
    
    # Wallet & Investments
    path('api/wallet/', include('investments.urls')),
    
    # Properties
    path('api/properties/', include('properties.urls')),
    
    # ============================================
    # CHANNEL PARTNER ROUTES (NEW)
    # ============================================
    path('api/cp/', include('partners.urls')),  # CP-facing APIs
    path('api/admin/cp/', include('partners.admin_urls')),  # Admin CP management
    
    # ============================================
    # ADMIN ROUTES (EXISTING)
    # ============================================
    path('api/admin/', include('accounts.admin_urls')),
    path('api/admin/kyc/', include('compliance.admin_urls')),
    path('api/admin/properties/', include('properties.admin_urls')),
    path('api/admin/investments/', include('investments.admin_urls')),
    path('api/', include('commissions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)