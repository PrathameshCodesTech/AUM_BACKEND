import os
from django.http import FileResponse
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Document
from .serializers import DocumentSerializer


class UserDocumentListView(APIView):
    """GET /api/documents/
    Returns for the current user:
      - All COMMON documents
      - INDIVIDUAL documents where user is in shared_with
      - PROPERTY documents where user has an approved investment in that property
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Get property IDs where user has approved investments
        from investments.models import Investment
        invested_property_ids = Investment.objects.filter(
            customer=user, status__in=['approved', 'active', 'completed', 'redeemed']
        ).values_list('property_id', flat=True).distinct()

        qs = Document.objects.filter(
            Q(document_type=Document.COMMON) |
            Q(document_type=Document.INDIVIDUAL, shared_with=user) |
            Q(document_type=Document.PROPERTY, property_id__in=invested_property_ids)
        ).select_related('uploaded_by', 'property').prefetch_related('shared_with').distinct()

        serializer = DocumentSerializer(qs, many=True, context={'request': request})
        return Response({'success': True, 'data': serializer.data})


class UserDocumentDownloadView(APIView):
    """GET /api/documents/<doc_id>/download/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id):
        user = request.user

        from investments.models import Investment
        invested_property_ids = Investment.objects.filter(
            customer=user, status__in=['approved', 'active', 'completed', 'redeemed']
        ).values_list('property_id', flat=True).distinct()

        try:
            doc = Document.objects.get(
                Q(document_type=Document.COMMON) |
                Q(document_type=Document.INDIVIDUAL, shared_with=user) |
                Q(document_type=Document.PROPERTY, property_id__in=invested_property_ids),
                id=doc_id,
            )
        except Document.DoesNotExist:
            return Response({'success': False, 'message': 'Document not found or access denied'}, status=404)

        if not doc.file or not os.path.isfile(doc.file.path):
            return Response({'success': False, 'message': 'File not found on server'}, status=404)

        file_name = doc.file.name.rsplit('/', 1)[-1]
        return FileResponse(open(doc.file.path, 'rb'), as_attachment=True, filename=file_name)
