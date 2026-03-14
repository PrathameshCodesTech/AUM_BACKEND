from django.urls import path
from .views import (
    UserDocumentListView,
    UserDocumentDownloadView,
    UserESignListView,
    UserESignRefreshView,
    UserESignDownloadView,
)

urlpatterns = [
    path('', UserDocumentListView.as_view(), name='user-document-list'),
    path('<int:doc_id>/download/', UserDocumentDownloadView.as_view(), name='user-document-download'),
    # eSign
    path('esign/', UserESignListView.as_view(), name='user-esign-list'),
    path('esign/<int:request_id>/refresh/', UserESignRefreshView.as_view(), name='user-esign-refresh'),
    path('esign/<int:request_id>/download/', UserESignDownloadView.as_view(), name='user-esign-download'),
]
