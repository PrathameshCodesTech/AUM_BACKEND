from django.urls import path
from .views import UserDocumentListView, UserDocumentDownloadView

urlpatterns = [
    path('', UserDocumentListView.as_view(), name='user-document-list'),
    path('<int:doc_id>/download/', UserDocumentDownloadView.as_view(), name='user-document-download'),
]
