"""
Property Admin URLs
Accessed via /api/admin/properties/
"""
from django.urls import path
from .admin_views import (
    # Property CRUD
    AdminPropertyListView,
    AdminPropertyDetailView,
    AdminPropertyCreateView,
    AdminPropertyUpdateView,
    AdminPropertyDeleteView,
    AdminPropertyActionView,
    
    # Image Management
    PropertyImageListView,
    PropertyImageUploadView,
    PropertyImageDeleteView,
    
    # Document Management
    PropertyDocumentListView,
    PropertyDocumentUploadView,
    PropertyDocumentDeleteView,
    
    # Unit Management
    PropertyUnitListView,
    PropertyUnitCreateView,
    PropertyUnitUpdateView,
    PropertyUnitDeleteView,
)

urlpatterns = [
    # Property Management
    path('', AdminPropertyListView.as_view(), name='admin-property-list'),
    path('create/', AdminPropertyCreateView.as_view(), name='admin-property-create'),
    path('<int:property_id>/', AdminPropertyDetailView.as_view(), name='admin-property-detail'),
    path('<int:property_id>/update/', AdminPropertyUpdateView.as_view(), name='admin-property-update'),
    path('<int:property_id>/delete/', AdminPropertyDeleteView.as_view(), name='admin-property-delete'),
    path('<int:property_id>/action/', AdminPropertyActionView.as_view(), name='admin-property-action'),
    
    # Image Management
    path('<int:property_id>/images/', PropertyImageListView.as_view(), name='admin-property-images'),
    path('<int:property_id>/images/upload/', PropertyImageUploadView.as_view(), name='admin-property-image-upload'),
    path('<int:property_id>/images/<int:image_id>/', PropertyImageDeleteView.as_view(), name='admin-property-image-delete'),
    
    # Document Management
    path('<int:property_id>/documents/', PropertyDocumentListView.as_view(), name='admin-property-documents'),
    path('<int:property_id>/documents/upload/', PropertyDocumentUploadView.as_view(), name='admin-property-document-upload'),
    path('<int:property_id>/documents/<int:document_id>/', PropertyDocumentDeleteView.as_view(), name='admin-property-document-delete'),
    
    # Unit Management
    path('<int:property_id>/units/', PropertyUnitListView.as_view(), name='admin-property-units'),
    path('<int:property_id>/units/create/', PropertyUnitCreateView.as_view(), name='admin-property-unit-create'),
    path('<int:property_id>/units/<int:unit_id>/update/', PropertyUnitUpdateView.as_view(), name='admin-property-unit-update'),
    path('<int:property_id>/units/<int:unit_id>/', PropertyUnitDeleteView.as_view(), name='admin-property-unit-delete'),
]