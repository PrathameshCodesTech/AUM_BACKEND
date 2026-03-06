from django.urls import path
from .admin_views import (
    AdminDocumentListView,
    AdminDocumentUploadView,
    AdminDocumentDeleteView,
    AdminUsersDropdownView,
    AdminPropertiesDropdownView,
)

urlpatterns = [
    path('', AdminDocumentListView.as_view(), name='admin-document-list'),
    path('upload/', AdminDocumentUploadView.as_view(), name='admin-document-upload'),
    path('users/', AdminUsersDropdownView.as_view(), name='admin-document-users'),
    path('properties/', AdminPropertiesDropdownView.as_view(), name='admin-document-properties'),
    path('<int:doc_id>/', AdminDocumentDeleteView.as_view(), name='admin-document-delete'),
]
