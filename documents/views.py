import os
from django.http import FileResponse
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Document, DocumentESignRequest
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


class UserESignListView(APIView):
    """
    GET /api/documents/esign/
    Returns all eSign requests directed at the current user, with their status and sign URL.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = DocumentESignRequest.objects.filter(
            target_user=user
        ).select_related('document', 'investment').order_by('-created_at')

        data = []
        for req in qs:
            data.append({
                'id': req.id,
                'document_id': req.document_id,
                'document_title': req.document.title,
                'investment_id': req.investment_id,
                'status': req.status,
                'sign_url': req.surepass_sign_url if req.status == 'initiated' else None,
                'completed_at': req.completed_at,
                'created_at': req.created_at,
            })

        return Response({'success': True, 'data': data})


class UserESignRefreshView(APIView):
    """
    POST /api/documents/esign/<request_id>/refresh/
    User-triggered status check — polls Surepass and stores signed PDF if complete.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        from django.core.files.base import ContentFile
        from django.utils import timezone as tz
        from .services.esign_service import SurepassESign

        try:
            esign_req = DocumentESignRequest.objects.select_related('document').get(
                id=request_id, target_user=request.user
            )
        except DocumentESignRequest.DoesNotExist:
            return Response({'success': False, 'message': 'Not found.'}, status=404)

        if esign_req.status == 'signed':
            return Response({'success': True, 'status': 'signed', 'message': 'Already signed.', 'identity_check_status': esign_req.identity_check_status})

        service = SurepassESign()
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

        # ── Step 1: Fetch signed-document metadata ──────────────────────────
        doc_result = service.get_signed_document(esign_req.surepass_client_id)
        esign_req.raw_signed_doc_payload = doc_result
        esign_req.save(update_fields=['raw_signed_doc_payload'])

        doc_data = doc_result.get('data', {}) if doc_result.get('success') else {}
        signed_pdf_url = (
            doc_data.get('signed_pdf_url') or
            doc_data.get('file_url') or
            doc_data.get('download_url') or
            doc_data.get('url')
        )

        # ── Step 2: Download raw PDF bytes and save to signed_file ──────────
        # We always persist the raw bytes for admin access, but we do NOT
        # create or share the user-visible Document record yet.
        if signed_pdf_url:
            pdf_bytes = service.download_signed_pdf_bytes(signed_pdf_url)
            if pdf_bytes:
                filename = f"signed_{esign_req.surepass_client_id}.pdf"
                esign_req.signed_file.save(filename, ContentFile(pdf_bytes), save=False)

        # ── Step 3: Identity check BEFORE sharing any document ──────────────
        from .services.esign_service import validate_signer_identity
        from compliance.models import KYC as KYCModel
        try:
            kyc = KYCModel.objects.get(user=esign_req.target_user)
            expected_names = [n for n in [kyc.aadhaar_name, esign_req.target_user.legal_full_name] if n]
        except KYCModel.DoesNotExist:
            expected_names = [n for n in [esign_req.target_user.legal_full_name] if n]

        identity = validate_signer_identity(status_data, doc_data, expected_names)
        esign_req.signer_name_returned     = identity['signer_name_returned'] or ''
        esign_req.identity_check_status    = identity['check_status']
        esign_req.identity_mismatch_reason = identity['reason']

        check = identity['check_status']

        if check == 'mismatch':
            # Hard identity mismatch — signed file stored for admin only, NOT shared with user
            esign_req.status = 'identity_mismatch'
            esign_req.completed_at = tz.now()
            esign_req.save(update_fields=[
                'status', 'completed_at', 'signed_file',
                'signer_name_returned', 'identity_check_status', 'identity_mismatch_reason',
            ])
            return Response({
                'success': True,
                'status': 'identity_mismatch',
                'message': (
                    'Your eSign submission has been received but the signer identity '
                    'could not be confirmed. An admin will review this.'
                ),
                'identity_check_status': check,
            })

        if check == 'unverified':
            # Provider returned no signer identity — hold for admin review, do not share
            esign_req.status = 'needs_review'
            esign_req.completed_at = tz.now()
            esign_req.save(update_fields=[
                'status', 'completed_at', 'signed_file',
                'signer_name_returned', 'identity_check_status', 'identity_mismatch_reason',
            ])
            return Response({
                'success': True,
                'status': 'needs_review',
                'message': (
                    'eSign received but identity verification is pending admin review.'
                ),
                'identity_check_status': check,
            })

        # ── Step 4: Identity verified — create and share the Document ────────
        if esign_req.signed_file and not esign_req.signed_document_id:
            from .models import Document as Doc
            signed_doc = Doc.objects.create(
                title=f"Signed: {esign_req.document.title}",
                description='Signed agreement',
                document_type=Doc.INDIVIDUAL,
                file=esign_req.signed_file,
                uploaded_by=request.user,
            )
            signed_doc.shared_with.set([request.user])
            esign_req.signed_document = signed_doc

        esign_req.status = 'signed'
        esign_req.completed_at = tz.now()
        esign_req.save(update_fields=[
            'status', 'completed_at', 'signed_file', 'signed_document',
            'signer_name_returned', 'identity_check_status', 'identity_mismatch_reason',
        ])

        return Response({
            'success': True,
            'status': 'signed',
            'message': 'eSign completed.',
            'identity_check_status': check,
        })


class UserESignDownloadView(APIView):
    """
    GET /api/documents/esign/<request_id>/download/
    Download the signed PDF (only accessible to the target user, only if signed).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, request_id):
        try:
            esign_req = DocumentESignRequest.objects.get(
                id=request_id, target_user=request.user
            )
        except DocumentESignRequest.DoesNotExist:
            return Response({'success': False, 'message': 'Not found.'}, status=404)

        if esign_req.status != 'signed' or not esign_req.signed_file:
            return Response(
                {'success': False, 'message': 'Signed document not available yet.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not os.path.isfile(esign_req.signed_file.path):
            return Response({'success': False, 'message': 'File not found on server.'}, status=404)

        filename = esign_req.signed_file.name.rsplit('/', 1)[-1]
        return FileResponse(
            open(esign_req.signed_file.path, 'rb'),
            as_attachment=True,
            filename=filename,
        )
