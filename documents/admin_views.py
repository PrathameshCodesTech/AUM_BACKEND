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


def _parse_coord(val, field_name):
    """
    Parse a coordinate value in integer PDF-space units (points).

    Surepass config.positions expects integer x/y coordinates in PDF point space
    (origin at bottom-left per PDF standard, 72 DPI baseline).
    The frontend converts editor preview percentages to PDF integers before sending.

    Validates: must be a non-negative number. No upper bound — valid values depend
    on actual page dimensions (e.g. 595 for A4 width, 842 for A4 height).
    Returns an integer.
    """
    try:
        fval = float(val)
    except (TypeError, ValueError):
        raise ValueError(f"'{field_name}' must be a number, got: {val!r}")
    if fval < 0:
        raise ValueError(f"'{field_name}' must be non-negative, got: {fval}")
    return int(round(fval))


def _parse_page(val, safe_page_count, context=''):
    """
    Parse and validate a page number. Raises ValueError if out of range.
    """
    try:
        pg = int(val)
    except (TypeError, ValueError):
        raise ValueError(f"Page number must be an integer{' in ' + context if context else ''}, got: {val!r}")
    if not (1 <= pg <= safe_page_count):
        raise ValueError(
            f"Page {pg} is out of range{' in ' + context if context else ''} "
            f"(document has {safe_page_count} page{'s' if safe_page_count != 1 else ''})."
        )
    return pg


def _parse_box_list(positions_input, context):
    """
    Parse a multi-box positions payload into a list of clean {x, y} dicts.

    Accepts either:
      - single-box legacy: the positions_input dict itself contains 'x' and 'y'
      - multi-box extended: positions_input contains 'positions': [{x, y}, ...]

    Raises ValueError on invalid data.
    """
    raw_list = positions_input.get('positions')
    if raw_list is not None:
        # Multi-box path: {"positions": [{x, y}, ...]}
        if not isinstance(raw_list, list) or not raw_list:
            raise ValueError(f"{context}: 'positions' must be a non-empty list.")
        result = []
        for i, c in enumerate(raw_list):
            if not isinstance(c, dict):
                raise ValueError(f"{context}: positions[{i}] must be a dict with 'x' and 'y'.")
            result.append({
                "x": _parse_coord(c.get('x', 10), f'{context} positions[{i}].x'),
                "y": _parse_coord(c.get('y', 20), f'{context} positions[{i}].y'),
            })
        return result
    else:
        # Single-box legacy path: {"x": int, "y": int}
        return [{
            "x": _parse_coord(positions_input.get('x', 10), f'{context} x'),
            "y": _parse_coord(positions_input.get('y', 20), f'{context} y'),
        }]


def _build_positions(mode, positions_input, page_count):
    """
    Build the Surepass config.positions dict from placement config.

    Coordinate system: x/y are INTEGER PDF-space coordinates (points).
    The frontend (ESignPlacementModal) converts admin drag positions from
    editor preview percentages to integer PDF points before sending, using
    actual PDF page dimensions captured from react-pdf's page.view.
    Origin is bottom-left (PDF standard). This backend is validation +
    forwarding only — it does NOT re-interpret or re-convert coordinates.

    positions_input format (single-box legacy — backward-compatible):
      single:          {"page": int, "x": int, "y": int}
      all_pages:       {"x": int, "y": int}
      selected_pages:  {"pages": [int, ...], "x": int, "y": int}
      manual:          {page_str: [{"x": int, "y": int}, ...]}

    positions_input format (multi-box extended):
      single:          {"page": int, "positions": [{"x": int, "y": int}, ...]}
      all_pages:       {"positions": [{"x": int, "y": int}, ...]}
      selected_pages:  {"pages": [int, ...], "positions": [{"x": int, "y": int}, ...]}
      manual:          {page_str: [{"x": int, "y": int}, ...]}  (unchanged)

    Raises ValueError for any invalid configuration: wrong types, negative
    coordinates, out-of-range page numbers, or empty page lists.
    """
    safe_page_count = max(1, int(page_count or 1))

    if mode == 'all_pages':
        boxes = _parse_box_list(positions_input, context='all_pages')
        return {str(p): boxes for p in range(1, safe_page_count + 1)}

    elif mode == 'selected_pages':
        pages = positions_input.get('pages', [])
        if not pages:
            raise ValueError("selected_pages mode requires at least one page number.")
        parsed = [_parse_page(p, safe_page_count, context='selected_pages') for p in pages]
        boxes = _parse_box_list(positions_input, context='selected_pages')
        return {str(p): boxes for p in parsed}

    elif mode == 'manual':
        if not isinstance(positions_input, dict) or not positions_input:
            raise ValueError("manual mode requires at least one page placement.")
        result = {}
        for pg_str, coords in positions_input.items():
            pg = _parse_page(pg_str, safe_page_count, context='manual')
            if not isinstance(coords, list) or not coords:
                raise ValueError(f"manual mode: page {pg} must have a non-empty list of coordinate objects.")
            clean = []
            for i, c in enumerate(coords):
                if not isinstance(c, dict):
                    raise ValueError(f"manual mode: page {pg} position {i} must be a dict with 'x' and 'y'.")
                clean.append({
                    "x": _parse_coord(c.get('x', 10), f'page {pg} x'),
                    "y": _parse_coord(c.get('y', 20), f'page {pg} y'),
                })
            result[str(pg)] = clean
        return result

    else:  # single (default)
        page = _parse_page(positions_input.get('page', 1), safe_page_count, context='single')
        boxes = _parse_box_list(positions_input, context='single')
        return {str(page): boxes}


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

        placement_mode = request.data.get('placement_mode', 'single')
        signature_positions_input = request.data.get('signature_positions', {})

        # Validate placement_mode
        valid_modes = ('single', 'all_pages', 'selected_pages', 'manual')
        if placement_mode not in valid_modes:
            return Response(
                {'success': False, 'message': f"Invalid placement_mode '{placement_mode}'. Must be one of: {', '.join(valid_modes)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate signature_positions shape matches placement_mode
        if not isinstance(signature_positions_input, dict):
            return Response(
                {'success': False, 'message': 'signature_positions must be a JSON object.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if placement_mode == 'selected_pages' and not isinstance(signature_positions_input.get('pages'), list):
            return Response(
                {'success': False, 'message': 'selected_pages mode requires signature_positions.pages to be a list of page numbers.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if placement_mode == 'manual' and not signature_positions_input:
            return Response(
                {'success': False, 'message': 'manual mode requires at least one entry in signature_positions.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        # Detect page count for placement config
        pdf_page_count = None
        try:
            import PyPDF2
            import io
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            pdf_page_count = len(reader.pages)
        except Exception:
            pdf_page_count = 1

        try:
            positions = _build_positions(placement_mode, signature_positions_input, pdf_page_count)
        except ValueError as exc:
            return Response({'success': False, 'message': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

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

            # Display name for UI — use legal identity, never username
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

            # eSign legal name: Aadhaar-verified name is most accurate; fallback to
            # legal_full_name. Never use username — it is a display name only.
            try:
                from compliance.models import KYC as _KYC
                _kyc = _KYC.objects.get(user=target_user)
                signer_name = _kyc.aadhaar_name or target_user.legal_full_name or ''
            except Exception:
                signer_name = target_user.legal_full_name or ''
            if not signer_name:
                entry.update({'status': 'error', 'message': 'User has no verified legal name. Ask them to complete their profile (first/last name as per Aadhaar).'})
                results.append(entry)
                skipped_count += 1
                continue
            signer_phone = getattr(target_user, 'phone', '') or ''
            signer_email = target_user.email or ''

            init_result = service.initialize(signer_name, signer_phone, signer_email, positions=positions)
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
                placement_mode=placement_mode,
                signature_positions=positions,
                pdf_page_count=pdf_page_count,
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
                'target_user_name': tu.legal_full_name or tu.get_full_name() or tu.username,  # username last-resort for display only

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
                'identity_check_status': req.identity_check_status,
                'signer_name_returned': req.signer_name_returned or None,
                'identity_mismatch_reason': req.identity_mismatch_reason or None,
                'placement_mode': req.placement_mode,
                'signature_positions': req.signature_positions,
                'pdf_page_count': req.pdf_page_count,
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
            return Response({'success': True, 'status': 'signed', 'message': 'Already signed.', 'identity_check_status': esign_req.identity_check_status})

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

        # ── Step 1: Fetch signed-document metadata ──────────────────────────
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

        # ── Step 2: Download raw PDF bytes and save to signed_file ──────────
        # Always persist the bytes for admin access.  The user-visible Document
        # record is NOT created here — only after identity check passes.
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
            # Hard mismatch — signed file stored for admin review only, NOT shared with user
            logger.warning(
                "eSign identity MISMATCH on request %s: provider='%s', expected=%s",
                esign_req.id, identity['signer_name_returned'], expected_names,
            )
            esign_req.status = 'identity_mismatch'
            esign_req.completed_at = timezone.now()
            esign_req.save(update_fields=[
                'status', 'completed_at', 'signed_file',
                'signer_name_returned', 'identity_check_status', 'identity_mismatch_reason',
            ])
            return Response({
                'success': True,
                'status': 'identity_mismatch',
                'message': 'eSign completed but signer identity does not match KYC. Marked identity_mismatch — admin review required.',
                'esign_request_id': esign_req.id,
                'identity_check_status': check,
                'identity_mismatch_reason': identity['reason'],
            })

        if check == 'unverified':
            # Provider returned no identity info — hold for admin review, do not share with user
            logger.warning(
                "eSign identity UNVERIFIED on request %s — provider returned no signer name.",
                esign_req.id,
            )
            esign_req.status = 'needs_review'
            esign_req.completed_at = timezone.now()
            esign_req.save(update_fields=[
                'status', 'completed_at', 'signed_file',
                'signer_name_returned', 'identity_check_status', 'identity_mismatch_reason',
            ])
            return Response({
                'success': True,
                'status': 'needs_review',
                'message': 'eSign received but signer identity could not be confirmed by provider. Needs admin review.',
                'esign_request_id': esign_req.id,
                'identity_check_status': check,
            })

        # ── Step 4: Identity verified — mark as signed ────────────────────────
        esign_req.status = 'signed'
        esign_req.completed_at = timezone.now()
        esign_req.save(update_fields=[
            'status', 'completed_at', 'signed_file',
            'signer_name_returned', 'identity_check_status', 'identity_mismatch_reason',
        ])

        return Response({
            'success': True,
            'status': 'signed',
            'message': 'eSign completed and signed document stored.',
            'esign_request_id': esign_req.id,
            'identity_check_status': check,
        })


class AdminESignApproveView(APIView):
    """
    POST /api/admin/documents/esign/<id>/approve/
    Admin manually approves a needs_review or identity_mismatch eSign request,
    marks it as signed and shares the signed document with the user.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, request_id):
        from django.utils import timezone
        try:
            esign_req = DocumentESignRequest.objects.select_related(
                'document', 'target_user'
            ).get(id=request_id)
        except DocumentESignRequest.DoesNotExist:
            return Response({'success': False, 'message': 'eSign request not found.'}, status=404)

        if esign_req.status not in ('needs_review', 'identity_mismatch'):
            return Response(
                {'success': False, 'message': f'Cannot approve a request with status "{esign_req.status}".'},
                status=400,
            )

        esign_req.status = 'signed'
        esign_req.identity_check_status = 'verified'
        esign_req.identity_mismatch_reason = 'Manually verified and approved by admin.'
        if not esign_req.completed_at:
            esign_req.completed_at = timezone.now()
        esign_req.save(update_fields=[
            'status', 'completed_at',
            'identity_check_status', 'identity_mismatch_reason',
        ])

        return Response({
            'success': True,
            'status': 'signed',
            'message': 'eSign request approved and marked as signed.',
            'esign_request_id': esign_req.id,
        })


class AdminDocumentPageCountView(APIView):
    """
    GET /api/admin/documents/<doc_id>/page-count/
    Returns the number of pages in the document PDF.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, doc_id):
        try:
            doc = Document.objects.get(id=doc_id)
        except Document.DoesNotExist:
            return Response({'success': False, 'message': 'Document not found.'}, status=404)

        try:
            import PyPDF2
            with doc.file.open('rb') as f:
                reader = PyPDF2.PdfReader(f)
                page_count = len(reader.pages)
            return Response({'success': True, 'page_count': page_count})
        except Exception as e:
            logger.error("Page count error for doc %s: %s", doc_id, e)
            # Return 1 as safe fallback — placement can still be configured
            return Response({'success': True, 'page_count': 1, 'warning': 'Could not detect page count; defaulting to 1.'})
