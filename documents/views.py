import os
from django.http import FileResponse, Http404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Document
from .serializers import DocumentSerializer


class UserDocumentListView(APIView):
    """GET /api/documents/
    Returns:
      - All COMMON documents
      - PROJECT documents where the current user is in shared_with
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        from django.db.models import Q
        qs = Document.objects.filter(
            Q(document_type=Document.COMMON) |
            Q(document_type=Document.PROJECT, shared_with=user)
        ).select_related('uploaded_by').prefetch_related('shared_with').distinct()

        serializer = DocumentSerializer(qs, many=True, context={'request': request})
        return Response({'success': True, 'data': serializer.data})


class UserDocumentDownloadView(APIView):
    """GET /api/documents/<doc_id>/download/
    Streams the file for download after verifying the user has access.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id):
        user = request.user
        from django.db.models import Q
        try:
            doc = Document.objects.get(
                Q(document_type=Document.COMMON) |
                Q(document_type=Document.PROJECT, shared_with=user),
                id=doc_id,
            )
        except Document.DoesNotExist:
            return Response({'success': False, 'message': 'Document not found or access denied'}, status=404)

        if not doc.file or not os.path.isfile(doc.file.path):
            return Response({'success': False, 'message': 'File not found on server'}, status=404)

        file_name = doc.file.name.rsplit('/', 1)[-1]
        response = FileResponse(open(doc.file.path, 'rb'), as_attachment=True, filename=file_name)
        return response
