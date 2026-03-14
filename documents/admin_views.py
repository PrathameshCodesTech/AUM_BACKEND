import json
import os
import logging

from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Document, DocumentESignRequest
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


# ============================================================
# eSign Admin Endpoints
# ============================================================

class AdminESignRequestView(APIView):
    """
    POST /api/admin/documents/esign/request/
    Admin sends a document for eSign to one or more users.
    Body: { document_id, target_user_ids: [int, ...], investment_id (optional) }
          OR legacy: { document_id, target_user_id: int, investment_id }
    Returns: { success, created, skipped, results: [{user_id, status, ...}] }
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        from .services.esign_service import SurepassESign

        document_id = request.data.get('document_id')
        investment_id = request.data.get('investment_id')

        # Accept both single target_user_id (legacy) and target_user_ids array
        raw_ids = request.data.get('target_user_ids') or request.data.get('target_user_id')
        if raw_ids is None:
            return Response(
                {'success': False, 'message': 'document_id and target_user_ids are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(raw_ids, list):
            raw_ids = [raw_ids]
        if not document_id or not raw_ids:
            return Response(
                {'success': False, 'message': 'document_id and target_user_ids are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            doc = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return Response({'success': False, 'message': 'Document not found.'}, status=404)

        if doc.document_type != Document.INDIVIDUAL:
            return Response(
                {'success': False, 'message': 'Only INDIVIDUAL documents can be sent for eSign.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        investment = None
        if investment_id:
            from investments.models import Investment
            try:
                investment = Investment.objects.get(id=investment_id)
            except Investment.DoesNotExist:
                return Response({'success': False, 'message': 'Investment not found.'}, status=404)

        # Read document bytes once — reused for all signers
        try:
            doc.file.open('rb')
            pdf_bytes = doc.file.read()
            doc.file.close()
        except Exception as e:
            logger.error(f"Could not read document file for eSign: {e}")
            return Response(
                {'success': False, 'message': 'Could not read document file.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        service = SurepassESign()
        results = []
        created_count = 0
        skipped_count = 0

        for uid in raw_ids:
            entry = {'user_id': uid}
            try:
                target_user = User.objects.get(id=uid)
            except User.DoesNotExist:
                entry.update({'status': 'error', 'message': 'User not found.'})
                results.append(entry)
                skipped_count += 1
                continue

            entry['user_name'] = target_user.legal_full_name or target_user.get_full_name() or target_user.username

            if not doc.shared_with.filter(id=target_user.id).exists():
                entry.update({'status': 'error', 'message': 'Document not shared with this user.'})
                results.append(entry)
                skipped_count += 1
                continue

            existing = DocumentESignRequest.objects.filter(
                document=doc,
                target_user=target_user,
                status__in=['pending', 'initiated', 'signed'],
            ).first()
            if existing:
                entry.update({
                    'status': 'duplicate',
                    'message': (
                        'This document has already been signed by this user.'
                        if existing.status == 'signed'
                        else 'An active eSign request already exists for this user.'
                    ),
                    'esign_request_id': existing.id,
                    'sign_url': existing.surepass_sign_url,
                })
                results.append(entry)
                skipped_count += 1
                continue

            signer_name = target_user.legal_full_name or target_user.get_full_name() or target_user.username
            signer_phone = getattr(target_user, 'phone', '') or ''
            signer_email = target_user.email or ''

            init_result = service.initialize(signer_name, signer_phone, signer_email)
            if not init_result.get('success'):
                entry.update({'status': 'error', 'message': f"eSign init failed: {init_result.get('error')}"})
                results.append(entry)
                skipped_count += 1
                continue

            client_id = init_result['data'].get('client_id', '')
            sign_url = init_result['data'].get('url', '')

            upload_result = service.get_upload_link(client_id)
            if not upload_result.get('success'):
                entry.update({'status': 'error', 'message': f"Upload link failed: {upload_result.get('error')}"})
                results.append(entry)
                skipped_count += 1
                continue

            upload_url = upload_result['data'].get('url', '')
            upload_fields = upload_result['data'].get('fields', {})
            if not upload_url or not upload_fields:
                entry.update({'status': 'error', 'message': 'Upload-link response missing url/fields.'})
                results.append(entry)
                skipped_count += 1
                continue

            uploaded = service.upload_pdf_to_s3(upload_url, upload_fields, pdf_bytes)
            if not uploaded:
                entry.update({'status': 'error', 'message': 'Failed to upload document to eSign storage.'})
                results.append(entry)
                skipped_count += 1
                continue

            esign_req = DocumentESignRequest.objects.create(
                document=doc,
                target_user=target_user,
                requested_by=request.user,
                investment=investment,
                surepass_client_id=client_id,
                surepass_sign_url=sign_url,
                status='initiated',
                raw_init_payload=init_result,
            )
            entry.update({
                'status': 'created',
                'esign_request_id': esign_req.id,
                'client_id': client_id,
                'sign_url': sign_url,
            })
            results.append(entry)
            created_count += 1

        return Response({
            'success': True,
            'message': f'{created_count} eSign request(s) created, {skipped_count} skipped.',
            'created': created_count,
            'skipped': skipped_count,
            'results': results,
        }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_200_OK)


class AdminESignListView(APIView):
    """
    GET /api/admin/documents/esign/
    List eSign requests. Filter: ?document_id=&user_id=&status=
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        qs = DocumentESignRequest.objects.select_related(
            'document', 'target_user', 'requested_by', 'investment'
        ).order_by('-created_at')

        doc_id = request.query_params.get('document_id')
        user_id = request.query_params.get('user_id')
        status_filter = request.query_params.get('status')

        if doc_id:
            qs = qs.filter(document_id=doc_id)
        if user_id:
            qs = qs.filter(target_user_id=user_id)
        if status_filter:
            qs = qs.filter(status=status_filter)

        data = []
        for req in qs:
            tu = req.target_user
            data.append({
                'id': req.id,
                'document_id': req.document_id,
                'document_title': req.document.title,
                'target_user_id': req.target_user_id,
                'target_user_name': tu.legal_full_name or tu.get_full_name() or tu.username,
                'investment_id': req.investment_id,
                'status': req.status,
                'sign_url': req.surepass_sign_url,
                'client_id': req.surepass_client_id,
                'completed_at': req.completed_at,
                'created_at': req.created_at,
                'signed_file_url': (
                    request.build_absolute_uri(req.signed_file.url)
                    if req.signed_file and req.signed_file.name
                    else None
                ),
            })

        return Response({'success': True, 'data': data})


class AdminESignRefreshView(APIView):
    """
    POST /api/admin/documents/esign/<request_id>/refresh/
    Fetch latest status from Surepass; download + store signed PDF if complete.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, request_id):
        from django.core.files.base import ContentFile
        from django.utils import timezone
        from .services.esign_service import SurepassESign

        try:
            esign_req = DocumentESignRequest.objects.select_related('document', 'target_user').get(id=request_id)
        except DocumentESignRequest.DoesNotExist:
            return Response({'success': False, 'message': 'eSign request not found.'}, status=404)

        if esign_req.status == 'signed':
            return Response({'success': True, 'status': 'signed', 'message': 'Already signed.'})

        service = SurepassESign()

        # Poll status
        status_result = service.get_status(esign_req.surepass_client_id)
        esign_req.raw_status_payload = status_result
        esign_req.save(update_fields=['raw_status_payload'])

        if not status_result.get('success'):
            return Response({'success': False, 'message': 'Could not fetch eSign status.'}, status=502)

        status_data = status_result.get('data', {})
        api_status = status_data.get('status', '')
        signed = (
            status_data.get('signed') or
            status_data.get('completed') or
            api_status in ('signed', 'esigned', 'esign_completed')
        )

        if not signed:
            return Response({'success': True, 'status': esign_req.status, 'message': 'Not yet signed.'})

        # Fetch signed document
        doc_result = service.get_signed_document(esign_req.surepass_client_id)
        esign_req.raw_signed_doc_payload = doc_result
        esign_req.save(update_fields=['raw_signed_doc_payload'])

        doc_data = doc_result.get('data', {}) if doc_result.get('success') else {}
        # Surepass may return signed PDF at different keys depending on API version
        signed_pdf_url = (
            doc_data.get('signed_pdf_url') or
            doc_data.get('file_url') or
            doc_data.get('download_url') or
            doc_data.get('url')
        )
        if signed_pdf_url:
            pdf_bytes = service.download_signed_pdf_bytes(signed_pdf_url)
            if pdf_bytes:
                filename = f"signed_{esign_req.surepass_client_id}.pdf"
                esign_req.signed_file.save(filename, ContentFile(pdf_bytes), save=False)

                # Create a Document record for the signed file so it surfaces in
                # the user's /api/documents/ list as an INDIVIDUAL document
                if not esign_req.signed_document_id:
                    signed_doc = Document.objects.create(
                        title=f"Signed: {esign_req.document.title}",
                        description=f"Signed agreement for {esign_req.target_user.get_full_name() or esign_req.target_user.username}",
                        document_type=Document.INDIVIDUAL,
                        file=esign_req.signed_file,
                        uploaded_by=request.user,
                    )
                    signed_doc.shared_with.set([esign_req.target_user])
                    esign_req.signed_document = signed_doc

        esign_req.status = 'signed'
        esign_req.completed_at = timezone.now()
        esign_req.save(update_fields=['status', 'completed_at', 'signed_file', 'signed_document'])

        return Response({
            'success': True,
            'status': 'signed',
            'message': 'eSign completed and signed document stored.',
            'esign_request_id': esign_req.id,
        })
