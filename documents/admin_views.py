import json
import os
import logging

from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Document
from .serializers import DocumentSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class AdminDocumentListView(APIView):
    """GET /api/admin/documents/?type=COMMON|INDIVIDUAL|PROPERTY"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        doc_type = request.GET.get('type')
        qs = Document.objects.select_related('uploaded_by', 'property').prefetch_related('shared_with')
        if doc_type in (Document.COMMON, Document.INDIVIDUAL, Document.PROPERTY):
            qs = qs.filter(document_type=doc_type)
        serializer = DocumentSerializer(qs, many=True, context={'request': request})
        return Response({'success': True, 'data': serializer.data})


class AdminDocumentUploadView(APIView):
    """POST /api/admin/documents/upload/
    Multipart fields:
      title, description, document_type, files (multiple)
      shared_with  — JSON array of user IDs (INDIVIDUAL only)
      property_id  — int (PROPERTY only)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        title = request.data.get('title', '').strip()
        description = request.data.get('description', '').strip()
        document_type = request.data.get('document_type', Document.COMMON)
        shared_with_raw = request.data.get('shared_with', '[]')
        property_id = request.data.get('property_id')
        files = request.FILES.getlist('files')

        if not title:
            return Response({'success': False, 'message': 'Title is required'}, status=400)
        if not files:
            return Response({'success': False, 'message': 'At least one file is required'}, status=400)
        if document_type not in (Document.COMMON, Document.INDIVIDUAL, Document.PROPERTY):
            return Response({'success': False, 'message': 'Invalid document type'}, status=400)

        try:
            shared_with_ids = json.loads(shared_with_raw) if isinstance(shared_with_raw, str) else shared_with_raw
        except (json.JSONDecodeError, TypeError):
            shared_with_ids = []

        # Resolve property for PROPERTY type
        property_obj = None
        if document_type == Document.PROPERTY and property_id:
            from properties.models import Property
            try:
                property_obj = Property.objects.get(id=property_id)
            except Property.DoesNotExist:
                return Response({'success': False, 'message': 'Property not found'}, status=400)

        created_docs = []
        for f in files:
            if f.size > 25 * 1024 * 1024:
                return Response(
                    {'success': False, 'message': f'File "{f.name}" exceeds 25 MB limit'},
                    status=400
                )
            doc = Document.objects.create(
                title=title,
                description=description,
                document_type=document_type,
                file=f,
                uploaded_by=request.user,
                property=property_obj,
            )
            if document_type == Document.INDIVIDUAL and shared_with_ids:
                users = User.objects.filter(id__in=shared_with_ids)
                doc.shared_with.set(users)
            created_docs.append(doc)

        serializer = DocumentSerializer(created_docs, many=True, context={'request': request})
        return Response({'success': True, 'data': serializer.data}, status=201)


class AdminDocumentDeleteView(APIView):
    """DELETE /api/admin/documents/<doc_id>/"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request, doc_id):
        try:
            doc = Document.objects.get(id=doc_id)
        except Document.DoesNotExist:
            return Response({'success': False, 'message': 'Document not found'}, status=404)

        if doc.file:
            try:
                if os.path.isfile(doc.file.path):
                    os.remove(doc.file.path)
            except Exception:
                pass

        doc.delete()
        return Response({'success': True, 'message': 'Document deleted'})


class AdminUsersDropdownView(APIView):
    """GET /api/admin/documents/users/ — id + name list for INDIVIDUAL user multi-select"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        users = User.objects.filter(is_active=True).exclude(is_staff=True).order_by('first_name', 'last_name', 'username')
        data = []
        for u in users:
            full = u.get_full_name()
            data.append({'id': u.id, 'name': full if full else u.username, 'email': u.email})
        return Response({'success': True, 'data': data})


class AdminPropertiesDropdownView(APIView):
    """GET /api/admin/documents/properties/ — id + name list for PROPERTY type dropdown"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        from properties.models import Property
        properties = Property.objects.order_by('name')
        data = [{'id': p.id, 'name': p.name} for p in properties]
        return Response({'success': True, 'data': data})
