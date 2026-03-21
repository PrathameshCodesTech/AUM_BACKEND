"""
eSign Service - Surepass Aadhaar eSign integration.

IMPORTANT — Surepass eSign identity data availability:
  Surepass Aadhaar OTP eSign does NOT currently return a verifiable signer name
  in the status or signed-document API responses in a standardised field.
  We look for every plausible field key, but if none are present the check
  will be 'unverified' rather than mocked as verified.
  Any future API contract change can be wired in by updating _extract_signer_name().

Proven sandbox flow:
  1. initialize(...)                       -> client_id + sign_url
  2. get_upload_link(client_id)           -> S3 form url + fields
  3. upload_pdf_to_s3(url, fields, bytes) -> multipart POST to S3
  4. user signs at sign_url
  5. get_status(client_id)                -> poll until completed
  6. get_signed_document(client_id)       -> signed pdf URL
"""

import logging
import unicodedata

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _log_provider_error(label: str, response: requests.Response, payload_keys: list | None = None):
    """Log full detail for non-2xx Surepass responses."""
    logger.error(
        "Surepass %s failed - HTTP %s\nURL: %s\nPayload keys sent: %s\nResponse body: %s",
        label,
        response.status_code,
        response.url,
        payload_keys or "(unknown)",
        response.text[:2000],
    )


def _normalize_name(name: str) -> str:
    """Lower-case, strip accents, collapse whitespace."""
    if not name:
        return ''
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = nfkd.encode('ascii', 'ignore').decode('ascii')
    return ' '.join(ascii_name.lower().split())


def _extract_signer_name(status_data: dict, doc_data: dict) -> str | None:
    """
    Try to extract signer name from Surepass eSign API response payloads.

    Surepass may embed signer identity in different fields across API versions.
    Returns the first non-empty string found, or None if nothing is available.
    """
    candidate_keys = [
        'signer_name', 'full_name', 'name', 'signed_by',
        'signatory_name', 'aadhaar_name', 'certificate_subject',
        'user_name', 'beneficiary_name',
    ]
    for payload in (status_data or {}, doc_data or {}):
        for key in candidate_keys:
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        # Some APIs nest signer info under 'signer' or 'signatory'
        for parent_key in ('signer', 'signatory', 'user'):
            sub = payload.get(parent_key)
            if isinstance(sub, dict):
                for key in candidate_keys:
                    val = sub.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
    return None


def validate_signer_identity(
    status_data: dict,
    doc_data: dict,
    expected_names: list,
) -> dict:
    """
    Compare the signer name returned by Surepass against expected identity names.

    Args:
        status_data:    Payload from get_status()['data']
        doc_data:       Payload from get_signed_document()['data']
        expected_names: List of acceptable names (e.g. [kyc.aadhaar_name, user.legal_full_name])

    Returns a dict:
        {
            'check_status': 'verified' | 'unverified' | 'mismatch',
            'signer_name_returned': str | None,
            'reason': str,
        }

    Logic:
      - If provider returns no name → 'unverified' (cannot validate, but do not block)
      - If provider returns a name AND it fuzzy-matches an expected name → 'verified'
      - If provider returns a name AND it does NOT match any expected name → 'mismatch'

    Note: We use a simple token-overlap heuristic instead of a full fuzzy library
    so this module has no extra dependencies.
    """
    returned_name = _extract_signer_name(status_data, doc_data)

    if not returned_name:
        # Provider did not return signer identity — cannot validate.
        # Log explicitly so operators know this is a known limitation.
        logger.warning(
            "eSign identity validation: provider returned no signer name. "
            "Document will be marked 'signed' but identity_check_status='unverified'. "
            "This is a known limitation of the Surepass Aadhaar OTP eSign API."
        )
        return {
            'check_status': 'unverified',
            'signer_name_returned': None,
            'reason': (
                "eSign provider did not return signer identity information. "
                "Identity could not be strongly validated."
            ),
        }

    clean_returned = _normalize_name(returned_name)
    clean_expected = [_normalize_name(n) for n in (expected_names or []) if n]

    def _token_overlap(a: str, b: str) -> float:
        """Fraction of tokens in `a` that appear in `b`."""
        ta = set(a.split())
        tb = set(b.split())
        if not ta:
            return 0.0
        return len(ta & tb) / len(ta)

    MATCH_THRESHOLD = 0.6

    for expected in clean_expected:
        if not expected:
            continue
        overlap_fwd = _token_overlap(clean_returned, expected)
        overlap_rev = _token_overlap(expected, clean_returned)
        score = max(overlap_fwd, overlap_rev)
        if score >= MATCH_THRESHOLD:
            logger.info(
                "eSign identity check: VERIFIED — provider='%s', expected='%s', score=%.2f",
                returned_name, expected, score,
            )
            return {
                'check_status': 'verified',
                'signer_name_returned': returned_name,
                'reason': f"Provider name '{returned_name}' matches expected identity (score {score:.0%}).",
            }

    logger.warning(
        "eSign identity check: MISMATCH — provider='%s', expected_names=%s",
        returned_name, clean_expected,
    )
    return {
        'check_status': 'mismatch',
        'signer_name_returned': returned_name,
        'reason': (
            f"Provider returned signer name '{returned_name}' which does not match "
            f"the expected identity names: {', '.join(n for n in expected_names if n)}."
        ),
    }


class SurepassESign:
    """Service for Surepass Aadhaar OTP eSign flow."""

    def __init__(self):
        self.api_token = getattr(settings, "SUREPASS_API_TOKEN", "")
        self.base_url = getattr(settings, "SUREPASS_BASE_URL", "https://sandbox.surepass.io").rstrip("/")
        self.test_mode = getattr(settings, "SUREPASS_TEST_MODE", True)

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _normalize_mobile_number(self, signer_phone: str) -> str:
        digits = "".join(ch for ch in (signer_phone or "") if ch.isdigit())
        if len(digits) == 12 and digits.startswith("91"):
            return digits[-10:]
        if len(digits) >= 10:
            return digits[-10:]
        return digits

    def initialize(self, signer_name: str, signer_phone: str, signer_email: str = "", positions: dict = None) -> dict:
        """
        POST /api/v1/esign/initialize
        Returns: { success, data: { client_id, token, url } }
        """
        if self.test_mode:
            import uuid

            client_id = f"test_esign_{uuid.uuid4().hex[:12]}"
            return {
                "success": True,
                "data": {
                    "client_id": client_id,
                    "token": "test_esign_token",
                    "url": f"https://sandbox.surepass.io/esign/{client_id}",
                },
            }

        payload = {
            "pdf_pre_uploaded": True,
            "sign_type": "aadhaar",
            "config": {
                "auth_mode": "1",
                "reason": "Contract",
                "positions": positions if positions else {"1": [{"x": 10, "y": 20}]},
            },
            "prefill_options": {
                "full_name": signer_name,
                "mobile_number": self._normalize_mobile_number(signer_phone),
                "user_email": signer_email or "",
            },
        }

        try:
            url = f"{self.base_url}/api/v1/esign/initialize"
            response = requests.post(url, json=payload, headers=self._get_headers(), timeout=30)
            if not response.ok:
                _log_provider_error("initialize", response, list(payload.keys()))
                response.raise_for_status()
            result = response.json()
            if result.get("success"):
                return {"success": True, "data": result.get("data", {})}
            logger.error("Surepass initialize returned non-success payload: %s", result)
            return {"success": False, "error": result.get("message", "eSign init failed")}
        except requests.exceptions.RequestException as exc:
            logger.error("Surepass initialize exception: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_upload_link(self, client_id: str) -> dict:
        """
        POST /api/v1/esign/get-upload-link
        Returns: { success, data: { url, fields, link_generated } }
        """
        if self.test_mode:
            return {
                "success": True,
                "data": {
                    "url": "https://example.com/mock-upload",
                    "fields": {"key": "test.pdf"},
                    "link_generated": True,
                },
            }

        payload = {
            "client_id": client_id,
            "file_name": "document.pdf",
            "file_type": "application/pdf",
        }

        try:
            url = f"{self.base_url}/api/v1/esign/get-upload-link"
            response = requests.post(url, json=payload, headers=self._get_headers(), timeout=30)
            if not response.ok:
                _log_provider_error("get_upload_link", response, list(payload.keys()))
                response.raise_for_status()
            result = response.json()
            if result.get("success"):
                return {"success": True, "data": result.get("data", {})}
            logger.error("Surepass get-upload-link returned non-success payload: %s", result)
            return {"success": False, "error": result.get("message", "Upload link failed")}
        except requests.exceptions.RequestException as exc:
            logger.error("Surepass get-upload-link exception: %s", exc)
            return {"success": False, "error": str(exc)}

    def upload_pdf_to_s3(self, upload_url: str, upload_fields: dict, pdf_bytes: bytes) -> bool:
        """
        Upload PDF bytes to the S3 form target returned by Surepass.
        Returns True on success.
        """
        if self.test_mode:
            return True

        form_data = dict(upload_fields or {})
        files = {
            "file": ("document.pdf", pdf_bytes, "application/pdf"),
        }

        try:
            response = requests.post(upload_url, data=form_data, files=files, timeout=60)
            if response.status_code not in (200, 201, 204):
                logger.error(
                    "S3 upload failed - HTTP %s\nURL: %s\nResponse body: %s",
                    response.status_code,
                    upload_url,
                    response.text[:500],
                )
                return False
            return True
        except requests.exceptions.RequestException as exc:
            logger.error("S3 upload exception: %s", exc)
            return False

    def get_status(self, client_id: str) -> dict:
        """
        GET /api/v1/esign/status/{client_id}
        Returns: { success, data: { status, completed, ... } }
        """
        if self.test_mode:
            return {
                "success": True,
                "data": {"status": "esign_completed", "signed": True, "completed": True},
            }

        try:
            url = f"{self.base_url}/api/v1/esign/status/{client_id}"
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            if not response.ok:
                _log_provider_error("get_status", response)
                response.raise_for_status()
            result = response.json()
            if result.get("success"):
                return {"success": True, "data": result.get("data", {})}
            logger.error("Surepass get-status returned non-success payload: %s", result)
            return {"success": False, "error": result.get("message", "Status fetch failed")}
        except requests.exceptions.RequestException as exc:
            logger.error("Surepass get-status exception: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_signed_document(self, client_id: str) -> dict:
        """
        GET /api/v1/esign/get-signed-document/{client_id}
        Returns: { success, data: { signed_pdf_url, ... } }
        """
        if self.test_mode:
            return {
                "success": True,
                "data": {"signed_pdf_url": "https://example.com/mock-signed.pdf"},
            }

        try:
            url = f"{self.base_url}/api/v1/esign/get-signed-document/{client_id}"
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            if not response.ok:
                _log_provider_error("get_signed_document", response)
                response.raise_for_status()
            result = response.json()
            if result.get("success"):
                return {"success": True, "data": result.get("data", {})}
            logger.error("Surepass get-signed-document returned non-success payload: %s", result)
            return {"success": False, "error": result.get("message", "Signed doc fetch failed")}
        except requests.exceptions.RequestException as exc:
            logger.error("Surepass get-signed-document exception: %s", exc)
            return {"success": False, "error": str(exc)}

    def download_signed_pdf_bytes(self, signed_pdf_url: str) -> bytes | None:
        """Download the signed PDF from the given URL."""
        if self.test_mode:
            return b"%PDF-1.4 mock signed pdf content"
        try:
            response = requests.get(signed_pdf_url, timeout=60)
            if response.status_code == 200:
                return response.content
            logger.error("download_signed_pdf_bytes HTTP %s from %s", response.status_code, signed_pdf_url)
        except requests.exceptions.RequestException as exc:
            logger.error("Failed to download signed PDF: %s", exc)
        return None
