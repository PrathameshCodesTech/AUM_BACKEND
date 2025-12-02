"""
URL configuration for aum_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),  # Add this
    path('api/kyc/', include('compliance.urls')),  # ← ADD THIS
    path('api/wallet/', include('investments.urls')),
    path('api/properties/', include('properties.urls')),

    # Admin APIs (new)
    path('api/admin/', include('accounts.admin_urls')),       # 👈 ADD THIS
    path('api/admin/kyc/', include('compliance.admin_urls')), # 👈 ADD THIS
    path('api/admin/properties/', include('properties.admin_urls')), # 👈 ADD THIS
    path('api/admin/investments/', include('investments.admin_urls')), 
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)