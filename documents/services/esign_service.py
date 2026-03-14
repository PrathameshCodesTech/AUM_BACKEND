"""
eSign Service - Surepass Aadhaar eSign integration.

Proven sandbox flow:
  1. initialize(...)                       -> client_id + sign_url
  2. get_upload_link(client_id)           -> S3 form url + fields
  3. upload_pdf_to_s3(url, fields, bytes) -> multipart POST to S3
  4. user signs at sign_url
  5. get_status(client_id)                -> poll until completed
  6. get_signed_document(client_id)       -> signed pdf URL
"""

import logging

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

    def initialize(self, signer_name: str, signer_phone: str, signer_email: str = "") -> dict:
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
                "positions": {
                    "1": [
                        {
                            "x": 10,
                            "y": 20,
                        }
                    ]
                },
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
