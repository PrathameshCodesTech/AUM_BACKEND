from django.urls import path
from .admin_views import (
    AdminDocumentListView,
    AdminDocumentUploadView,
    AdminDocumentDeleteView,
    AdminUsersDropdownView,
    AdminPropertiesDropdownView,
    AdminESignRequestView,
    AdminESignListView,
    AdminESignRefreshView,
    AdminESignApproveView,
)

urlpatterns = [
    path('', AdminDocumentListView.as_view(), name='admin-document-list'),
    path('upload/', AdminDocumentUploadView.as_view(), name='admin-document-upload'),
    path('users/', AdminUsersDropdownView.as_view(), name='admin-document-users'),
    path('properties/', AdminPropertiesDropdownView.as_view(), name='admin-document-properties'),
    path('<int:doc_id>/', AdminDocumentDeleteView.as_view(), name='admin-document-delete'),
    # eSign
    path('esign/', AdminESignListView.as_view(), name='admin-esign-list'),
    path('esign/request/', AdminESignRequestView.as_view(), name='admin-esign-request'),
    path('esign/<int:request_id>/refresh/', AdminESignRefreshView.as_view(), name='admin-esign-refresh'),
    path('esign/<int:request_id>/approve/', AdminESignApproveView.as_view(), name='admin-esign-approve'),
]
