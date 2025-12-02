# compliance/admin.py
from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.forms import widgets
from django.db import models
from django.db.models import Q
import json

from .models import KYC, Document, AuditLog


# ============================================
# CUSTOM WIDGETS
# ============================================

class PrettyJSONWidget(widgets.Textarea):
    """
    Widget for displaying formatted JSON in admin.
    """

    def format_value(self, value):
        try:
            if isinstance(value, str):
                value = json.loads(value)
            pretty = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
            self.attrs["rows"] = min(pretty.count("\n") + 2, 20)
            return pretty
        except (ValueError, TypeError):
            return super().format_value(value)


# ============================================
# CUSTOM FILTERS
# ============================================

class KYCStatusFilter(admin.SimpleListFilter):
    """Filter KYC by overall status."""
    title = "KYC status"
    parameter_name = "kyc_status"

    def lookups(self, request, model_admin):
        return (
            ("pending", "Pending"),
            ("under_review", "Under Review"),
            ("verified", "Verified"),
            ("rejected", "Rejected"),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class AadhaarVerificationFilter(admin.SimpleListFilter):
    """Filter KYC by Aadhaar verification status."""
    title = "Aadhaar verification"
    parameter_name = "aadhaar_verified"

    def lookups(self, request, model_admin):
        return (
            ("verified", "Verified"),
            ("unverified", "Not Verified"),
        )

    def queryset(self, request, queryset):
        if self.value() == "verified":
            return queryset.filter(aadhaar_verified=True)
        if self.value() == "unverified":
            return queryset.filter(aadhaar_verified=False)
        return queryset


class PANVerificationFilter(admin.SimpleListFilter):
    """Filter KYC by PAN verification status."""
    title = "PAN verification"
    parameter_name = "pan_verified"

    def lookups(self, request, model_admin):
        return (
            ("verified", "Verified"),
            ("unverified", "Not Verified"),
            ("linked", "PAN-Aadhaar Linked"),
        )

    def queryset(self, request, queryset):
        if self.value() == "verified":
            return queryset.filter(pan_verified=True)
        if self.value() == "unverified":
            return queryset.filter(pan_verified=False)
        if self.value() == "linked":
            return queryset.filter(pan_aadhaar_linked=True)
        return queryset


class BankVerificationFilter(admin.SimpleListFilter):
    """Filter KYC by bank verification status."""
    title = "Bank verification"
    parameter_name = "bank_verified"

    def lookups(self, request, model_admin):
        return (
            ("verified", "Verified"),
            ("unverified", "Not Verified"),
        )

    def queryset(self, request, queryset):
        if self.value() == "verified":
            return queryset.filter(bank_verified=True)
        if self.value() == "unverified":
            return queryset.filter(bank_verified=False)
        return queryset


class CompletionFilter(admin.SimpleListFilter):
    """Filter KYC by completion (all three verified or not)."""
    title = "KYC completion"
    parameter_name = "completion"

    def lookups(self, request, model_admin):
        return (
            ("complete", "Complete (Aadhaar + PAN + Bank verified)"),
            ("incomplete", "Incomplete"),
        )

    def queryset(self, request, queryset):
        if self.value() == "complete":
            return queryset.filter(
                aadhaar_verified=True,
                pan_verified=True,
                bank_verified=True,
            )
        if self.value() == "incomplete":
            return queryset.filter(
                Q(aadhaar_verified=False)
                | Q(pan_verified=False)
                | Q(bank_verified=False)
            )
        return queryset


class SoftDeleteFilter(admin.SimpleListFilter):
    """Generic soft delete filter for models with is_deleted."""
    title = "deletion status"
    parameter_name = "deleted"

    def lookups(self, request, model_admin):
        return (
            ("active", "Active only"),
            ("deleted", "Deleted only"),
        )

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(is_deleted=False)
        if self.value() == "deleted":
            return queryset.filter(is_deleted=True)
        return queryset


class DocumentTypeFilter(admin.SimpleListFilter):
    """Filter documents by type."""
    title = "document type"
    parameter_name = "doc_type"

    def lookups(self, request, model_admin):
        return (
            ("aadhaar", "Aadhaar Card"),
            ("pan", "PAN Card"),
            ("bank", "Bank Proof"),
            ("address", "Address Proof"),
            ("photo", "Photograph"),
            ("signature", "Signature"),
            ("other", "Other"),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(document_type=self.value())
        return queryset


class AuditActionFilter(admin.SimpleListFilter):
    """Filter audit logs by action type."""
    title = "action type"
    parameter_name = "action"

    def lookups(self, request, model_admin):
        return (
            ("kyc_submit", "KYC Submitted"),
            ("kyc_approve", "KYC Approved"),
            ("kyc_reject", "KYC Rejected"),
            ("document_upload", "Document Uploaded"),
            ("document_delete", "Document Deleted"),
            ("profile_update", "Profile Updated"),
            ("login", "User Login"),
            ("logout", "User Logout"),
            ("password_change", "Password Changed"),
            ("other", "Other Action"),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(action=self.value())
        return queryset


# ============================================
# KYC ADMIN
# ============================================

@admin.register(KYC)
class KYCAdmin(admin.ModelAdmin):
    """Admin for KYC management (Aadhaar, PAN, Bank, Address, Validation)."""

    list_display = [
        "user_link",
        "verification_summary",
        "aadhaar_status",
        "pan_status",
        "bank_status",
        "name_dob_validation_badge",
        "completion_progress",
        "status_badge",
        "created_at",
    ]

    list_filter = [
        KYCStatusFilter,
        AadhaarVerificationFilter,
        PANVerificationFilter,
        BankVerificationFilter,
        CompletionFilter,
        "name_validation_status",
        "dob_validation_status",
        SoftDeleteFilter,
        "created_at",
        "verified_at",
    ]

    search_fields = [
        "user__username",
        "user__email",
        "user__phone",
        "aadhaar_number",
        "aadhaar_name",
        "pan_number",
        "pan_name",
        "account_number",
        "bank_name",
    ]

    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    readonly_fields = [
        # Timestamps & meta
        "created_at",
        "updated_at",
        "verified_at",
        "verified_by",
        "aadhaar_verified_at",
        "pan_verified_at",
        "bank_verified_at",
        "deleted_at",
        "deleted_by",
        # Previews
        "aadhaar_front_preview",
        "aadhaar_back_preview",
        "pan_document_preview",
        "bank_proof_preview",
        "address_proof_preview",
        # JSON displays
        "aadhaar_api_response_display",
        "pan_api_response_display",
        "bank_api_response_display",
        "validation_errors_display",
        # Extra info
        "completion_percentage",
    ]

    fieldsets = (
        (
            "User & KYC Status",
            {
                "fields": (
                    "user",
                    "status",
                    "verified_at",
                    "verified_by",
                    "rejection_reason",
                )
            },
        ),
        (
            "Name & DOB Validation",
            {
                "fields": (
                    "name_validation_status",
                    "dob_validation_status",
                    "name_match_score",
                    "validation_errors",
                    "validation_errors_display",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Aadhaar Details",
            {
                "fields": (
                    "aadhaar_number",
                    "aadhaar_name",
                    "aadhaar_dob",
                    "aadhaar_gender",
                    "aadhaar_address",
                    "aadhaar_verified",
                    "aadhaar_verified_at",
                    "aadhaar_retry_count",
                    "aadhaar_last_retry_at",
                    "aadhaar_front",
                    "aadhaar_front_preview",
                    "aadhaar_back",
                    "aadhaar_back_preview",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Aadhaar API Response",
            {
                "fields": ("aadhaar_api_response", "aadhaar_api_response_display"),
                "classes": ("collapse",),
            },
        ),
        (
            "PAN Details",
            {
                "fields": (
                    "pan_number",
                    "pan_name",
                    "pan_father_name",
                    "pan_dob",
                    "pan_verified",
                    "pan_verified_at",
                    "pan_aadhaar_linked",
                    "pan_retry_count",
                    "pan_last_retry_at",
                    "pan_document",
                    "pan_document_preview",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "PAN API Response",
            {
                "fields": ("pan_api_response", "pan_api_response_display"),
                "classes": ("collapse",),
            },
        ),
        (
            "Bank Details",
            {
                "fields": (
                    "bank_name",
                    "account_number",
                    "ifsc_code",
                    "account_holder_name",
                    "account_type",
                    "bank_verified",
                    "bank_verified_at",
                    "bank_proof",
                    "bank_proof_preview",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Bank API Response",
            {
                "fields": ("bank_api_response", "bank_api_response_display"),
                "classes": ("collapse",),
            },
        ),
        (
            "Address Details",
            {
                "fields": (
                    "address_line1",
                    "address_line2",
                    "city",
                    "state",
                    "pincode",
                    "address_proof",
                    "address_proof_preview",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Completion & Soft Delete",
            {
                "fields": (
                    "completion_percentage",
                    "is_deleted",
                    "deleted_at",
                    "deleted_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    autocomplete_fields = ["user", "verified_by", "deleted_by"]

    # Use pretty JSON for all JSONField form inputs
    formfield_overrides = {
        models.JSONField: {"widget": PrettyJSONWidget},
    }

    # ---------- List display helpers ----------

    def user_link(self, obj):
        """Clickable link to User admin."""
        url = reverse("admin:accounts_user_change", args=[obj.user.id])
        label = obj.user.get_full_name() or obj.user.username
        sub = obj.user.phone or obj.user.email or ""
        return format_html(
            '<a href="{}">{}</a><br><small style="color:#666;">{}</small>',
            url,
            label,
            sub,
        )

    user_link.short_description = "User"

    def verification_summary(self, obj):
        """Compact emoji summary of Aadhaar/PAN/Bank verification."""
        aadhaar_icon = "✅" if obj.aadhaar_verified else "❌"
        pan_icon = "✅" if obj.pan_verified else "❌"
        bank_icon = "✅" if obj.bank_verified else "❌"

        return format_html(
            '<div style="font-size:18px;">'
            '<span title="Aadhaar">{}</span> '
            '<span title="PAN">{}</span> '
            '<span title="Bank">{}</span>'
            "</div>",
            aadhaar_icon,
            pan_icon,
            bank_icon,
        )

    verification_summary.short_description = "Verified"

    def aadhaar_status(self, obj):
        """Display Aadhaar status with color + number."""
        if obj.aadhaar_verified:
            return format_html(
                '<span style="color:#28a745;font-weight:bold;">✓ Verified</span><br>'
                "<small>{}</small>",
                obj.aadhaar_number or "—",
            )
        if obj.aadhaar_number:
            return format_html(
                '<span style="color:#ffc107;">⏳ Unverified</span><br>'
                "<small>{}</small>",
                obj.aadhaar_number,
            )
        return format_html('<span style="color:#999;">— Not Provided</span>')

    aadhaar_status.short_description = "Aadhaar"

    def pan_status(self, obj):
        """Display PAN status with color + linked badge."""
        if obj.pan_verified:
            linked_badge = ""
            if obj.pan_aadhaar_linked:
                linked_badge = (
                    '<br><span style="background:#28a745;color:white;'
                    "padding:1px 4px;border-radius:2px;font-size:9px;"
                    '">🔗 Linked</span>'
                )

            return format_html(
                '<span style="color:#28a745;font-weight:bold;">✓ Verified</span><br>'
                "<small>{}</small>{}",
                obj.pan_number or "—",
                linked_badge,
            )
        if obj.pan_number:
            return format_html(
                '<span style="color:#ffc107;">⏳ Unverified</span><br>'
                "<small>{}</small>",
                obj.pan_number,
            )
        return format_html('<span style="color:#999;">— Not Provided</span>')

    pan_status.short_description = "PAN"

    def bank_status(self, obj):
        """Display Bank status with masked account."""
        if obj.bank_verified:
            if obj.account_number:
                last4 = obj.account_number[-4:]
                masked = last4.rjust(len(obj.account_number), "*")
            else:
                masked = "—"

            return format_html(
                '<span style="color:#28a745;font-weight:bold;">✓ Verified</span><br>'
                "<small>{}</small><br>"
                '<small style="color:#6c757d;">{}</small>',
                obj.bank_name or "—",
                masked,
            )
        if obj.account_number:
            return format_html(
                '<span style="color:#ffc107;">⏳ Unverified</span><br>'
                "<small>{}</small>",
                obj.bank_name or "—",
            )
        return format_html('<span style="color:#999;">— Not Provided</span>')

    bank_status.short_description = "Bank"

    def name_dob_validation_badge(self, obj):
        """Combined badge for name + DOB validation + match score."""
        name_colors = {
            "pending": "#6c757d",
            "passed": "#28a745",
            "failed": "#dc3545",
            "needs_review": "#ffc107",
        }
        dob_colors = {
            "pending": "#6c757d",
            "passed": "#28a745",
            "failed": "#dc3545",
        }

        name_status = obj.name_validation_status or "pending"
        dob_status = obj.dob_validation_status or "pending"

        name_label = getattr(
            obj, "get_name_validation_status_display", lambda: name_status
        )()
        dob_label = getattr(obj, "get_dob_validation_status_display", lambda: dob_status)()

        if obj.name_match_score is not None:
            score_str = f"{obj.name_match_score:.2f}"
            score_html = f"<br><small>Match score: {score_str}</small>"
        else:
            score_html = ""

        return format_html(
            '<span style="background-color:{};color:white;padding:3px 6px;'
            'border-radius:3px;font-size:10px;margin-right:4px;">Name: {}</span>'
            '<span style="background-color:{};color:white;padding:3px 6px;'
            'border-radius:3px;font-size:10px;">DOB: {}</span>'
            "{}",
            name_colors.get(name_status, "#6c757d"),
            name_label,
            dob_colors.get(dob_status, "#6c757d"),
            dob_label,
            score_html,
        )

    name_dob_validation_badge.short_description = "Name / DOB Validation"

    def completion_progress(self, obj):
        """Small horizontal progress bar for completion."""
        total_steps = 3
        completed = sum(
            [
                bool(obj.aadhaar_verified),
                bool(obj.pan_verified),
                bool(obj.bank_verified),
            ]
        )
        percentage = (completed / total_steps * 100) if total_steps else 0
        percentage_display = f"{percentage:.0f}"

        if percentage == 100:
            color = "#28a745"
        elif percentage >= 66:
            color = "#17a2b8"
        elif percentage >= 33:
            color = "#ffc107"
        else:
            color = "#dc3545"

        return format_html(
            '<div style="width:100px;background:#f0f0f0;border-radius:10px;'
            'overflow:hidden;height:18px;">'
            '<div style="width:{}%;background-color:{};height:100%;'
            'display:flex;align-items:center;justify-content:center;">'
            '<small style="color:white;font-weight:bold;font-size:10px;">{}%</small>'
            "</div></div>"
            "<small>{}/3 verified</small>",
            percentage,
            color,
            percentage_display,
            completed,
        )

    completion_progress.short_description = "Progress"

    def status_badge(self, obj):
        """Big badge for overall KYC status (and deleted state)."""
        colors = {
            "pending": "#ffc107",
            "under_review": "#17a2b8",
            "verified": "#28a745",
            "rejected": "#dc3545",
        }

        if getattr(obj, "is_deleted", False):
            return format_html(
                "<span style=\"background-color:#000;color:white;padding:3px 8px;"
                'border-radius:3px;font-size:10px;">🗑️ DELETED</span>'
            )

        status = obj.status or "pending"
        status_label = obj.get_status_display() if hasattr(obj, "get_status_display") else status

        return format_html(
            "<span style=\"background-color:{};color:white;padding:4px 10px;"
            'border-radius:3px;font-size:11px;font-weight:bold;">{}</span>',
            colors.get(status, "#6c757d"),
            status_label.upper(),
        )

    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    def completion_percentage(self, obj):
        """Detailed completion block shown in detail view."""
        total_steps = 3
        completed = sum(
            [
                bool(obj.aadhaar_verified),
                bool(obj.pan_verified),
                bool(obj.bank_verified),
            ]
        )
        percentage = (completed / total_steps * 100) if total_steps else 0
        percentage_display = f"{percentage:.0f}"

        color = "#28a745" if percentage == 100 else "#ffc107"

        return format_html(
            '<div style="font-size:24px;font-weight:bold;color:{};">{}%</div>'
            '<div style="margin-top:10px;">'
            "<div>Aadhaar: {}</div>"
            "<div>PAN: {}</div>"
            "<div>Bank: {}</div>"
            "</div>",
            color,
            percentage_display,
            "✅ Verified" if obj.aadhaar_verified else "❌ Not Verified",
            "✅ Verified" if obj.pan_verified else "❌ Not Verified",
            "✅ Verified" if obj.bank_verified else "❌ Not Verified",
        )

    completion_percentage.short_description = "Completion Status"

    # ---------- Document preview helpers ----------

    def aadhaar_front_preview(self, obj):
        if obj.aadhaar_front:
            url = obj.aadhaar_front.url
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width:300px;max-height:200px;border:1px solid #ddd;" />'
                "</a><br>"
                '<a href="{}" target="_blank" class="button">View Full Size</a>',
                url,
                url,
                url,
            )
        return format_html('<span style="color:#999;">No document uploaded</span>')

    aadhaar_front_preview.short_description = "Aadhaar Front Preview"

    def aadhaar_back_preview(self, obj):
        if obj.aadhaar_back:
            url = obj.aadhaar_back.url
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width:300px;max-height:200px;border:1px solid #ddd;" />'
                "</a><br>"
                '<a href="{}" target="_blank" class="button">View Full Size</a>',
                url,
                url,
                url,
            )
        return format_html('<span style="color:#999;">No document uploaded</span>')

    aadhaar_back_preview.short_description = "Aadhaar Back Preview"

    def pan_document_preview(self, obj):
        if obj.pan_document:
            url = obj.pan_document.url
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width:300px;max-height:200px;border:1px solid #ddd;" />'
                "</a><br>"
                '<a href="{}" target="_blank" class="button">View Full Size</a>',
                url,
                url,
                url,
            )
        return format_html('<span style="color:#999;">No document uploaded</span>')

    pan_document_preview.short_description = "PAN Document Preview"

    def bank_proof_preview(self, obj):
        if obj.bank_proof:
            url = obj.bank_proof.url
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width:300px;max-height:200px;border:1px solid #ddd;" />'
                "</a><br>"
                '<a href="{}" target="_blank" class="button">View Full Size</a>',
                url,
                url,
                url,
            )
        return format_html('<span style="color:#999;">No document uploaded</span>')

    bank_proof_preview.short_description = "Bank Proof Preview"

    def address_proof_preview(self, obj):
        if obj.address_proof:
            url = obj.address_proof.url
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width:300px;max-height:200px;border:1px solid #ddd;" />'
                "</a><br>"
                '<a href="{}" target="_blank" class="button">View Full Size</a>',
                url,
                url,
                url,
            )
        return format_html('<span style="color:#999;">No document uploaded</span>')

    address_proof_preview.short_description = "Address Proof Preview"

    # ---------- API JSON displays ----------

    def _json_pretty_block(self, data):
        if not data:
            return format_html('<span style="color:#999;">No data</span>')
        try:
            pretty = json.dumps(data, indent=2, ensure_ascii=False)
        except TypeError:
            pretty = str(data)
        return format_html(
            '<pre style="background:#f5f5f5;padding:10px;border-radius:5px;'
            "max-height:400px;overflow:auto;white-space:pre-wrap;\">{}</pre>",
            pretty,
        )

    def aadhaar_api_response_display(self, obj):
        return self._json_pretty_block(obj.aadhaar_api_response)

    aadhaar_api_response_display.short_description = "Aadhaar API Response (Formatted)"

    def pan_api_response_display(self, obj):
        return self._json_prety_block(obj.pan_api_response)

    pan_api_response_display.short_description = "PAN API Response (Formatted)"

    def bank_api_response_display(self, obj):
        return self._json_pretty_block(obj.bank_api_response)

    bank_api_response_display.short_description = "Bank API Response (Formatted)"

    def validation_errors_display(self, obj):
        return self._json_pretty_block(obj.validation_errors)

    validation_errors_display.short_description = "Validation Errors (Formatted)"

    # ---------- Bulk actions ----------

    actions = [
        "mark_under_review",
        "verify_kyc",
        "reject_kyc",
        "verify_aadhaar",
        "verify_pan",
        "verify_bank",
        "soft_delete_kyc",
        "restore_kyc",
    ]

    def mark_under_review(self, request, queryset):
        """Mark selected KYC as under review (from pending)."""
        updated = 0
        for kyc in queryset.filter(status="pending"):
            kyc.status = "under_review"
            kyc.save()
            updated += 1
        self.message_user(
            request,
            f"{updated} KYC record(s) marked under review.",
            level=messages.SUCCESS,
        )

    mark_under_review.short_description = "🔍 Mark Under Review"

    def verify_kyc(self, request, queryset):
        """Mark selected KYC as verified (only if complete)."""
        count = 0
        for kyc in queryset:
            if kyc.is_complete():
                kyc.status = "verified"
                if not kyc.verified_at:
                    kyc.verified_at = timezone.now()
                if not kyc.verified_by:
                    kyc.verified_by = request.user
                kyc.save()
                # Optionally sync user fields (if present on User)
                user = kyc.user
                if hasattr(user, "kyc_status"):
                    user.kyc_status = "verified"
                if hasattr(user, "kyc_verified_at"):
                    user.kyc_verified_at = timezone.now()
                try:
                    user.save()
                except Exception:
                    pass
                count += 1

        if count:
            self.message_user(
                request,
                f"{count} KYC record(s) verified successfully.",
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                "No KYC selected is fully complete. Nothing was verified.",
                level=messages.WARNING,
            )

    verify_kyc.short_description = "✓ Verify Complete KYC"

    def reject_kyc(self, request, queryset):
        """Reject selected KYC entries."""
        count = 0
        for kyc in queryset:
            kyc.status = "rejected"
            kyc.verified_by = request.user
            kyc.verified_at = timezone.now()
            kyc.save()
            # sync user status if field exists
            user = kyc.user
            if hasattr(user, "kyc_status"):
                user.kyc_status = "rejected"
            try:
                user.save()
            except Exception:
                pass
            count += 1

        self.message_user(
            request,
            f"{count} KYC record(s) rejected.",
            level=messages.WARNING,
        )

    reject_kyc.short_description = "❌ Reject KYC"

    def verify_aadhaar(self, request, queryset):
        """Mark Aadhaar as verified (only sets flags)."""
        updated = queryset.update(
            aadhaar_verified=True,
            aadhaar_verified_at=timezone.now(),
        )
        self.message_user(
            request,
            f"{updated} Aadhaar verification(s) marked.",
            level=messages.SUCCESS,
        )

    verify_aadhaar.short_description = "✓ Verify Aadhaar"

    def verify_pan(self, request, queryset):
        """Mark PAN as verified."""
        updated = queryset.update(
            pan_verified=True,
            pan_verified_at=timezone.now(),
        )
        self.message_user(
            request,
            f"{updated} PAN verification(s) marked.",
            level=messages.SUCCESS,
        )

    verify_pan.short_description = "✓ Verify PAN"

    def verify_bank(self, request, queryset):
        """Mark Bank as verified."""
        updated = queryset.update(
            bank_verified=True,
            bank_verified_at=timezone.now(),
        )
        self.message_user(
            request,
            f"{updated} bank verification(s) marked.",
            level=messages.SUCCESS,
        )

    verify_bank.short_description = "✓ Verify Bank"

    def soft_delete_kyc(self, request, queryset):
        """Soft delete selected KYC records."""
        updated = queryset.filter(is_deleted=False).update(
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by=request.user,
        )
        self.message_user(
            request,
            f"{updated} KYC record(s) soft deleted.",
            level=messages.SUCCESS,
        )

    soft_delete_kyc.short_description = "🗑️ Soft Delete"

    def restore_kyc(self, request, queryset):
        """Restore soft deleted KYC records."""
        updated = queryset.filter(is_deleted=True).update(
            is_deleted=False,
            deleted_at=None,
            deleted_by=None,
        )
        self.message_user(
            request,
            f"{updated} KYC record(s) restored.",
            level=messages.SUCCESS,
        )

    restore_kyc.short_description = "↻ Restore"

    # ---------- Save hook ----------

    def save_model(self, request, obj, form, change):
        """
        Auto-set verified_by / verified_at when changing status in admin.
        Also sync User.kyc_status / kyc_verified_at if present.
        """
        status_changed = change and "status" in form.changed_data

        if status_changed and obj.status == "verified":
            if not obj.verified_by:
                obj.verified_by = request.user
            if not obj.verified_at:
                obj.verified_at = timezone.now()

        super().save_model(request, obj, form, change)

        if status_changed:
            user = obj.user
            if hasattr(user, "kyc_status"):
                user.kyc_status = obj.status
            if hasattr(user, "kyc_verified_at") and obj.status == "verified":
                user.kyc_verified_at = obj.verified_at or timezone.now()
            try:
                user.save()
            except Exception:
                pass


# ============================================
# DOCUMENT ADMIN
# ============================================

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin for user documents (Aadhaar, PAN, bank proof, etc.)."""

    list_display = [
        "user_link",
        "document_type_badge",
        "file_name",
        "file_size_display",
        "file_preview_thumb",
        "is_deleted",
        "created_at",
    ]

    list_filter = [
        DocumentTypeFilter,
        SoftDeleteFilter,
        "created_at",
    ]

    search_fields = [
        "user__username",
        "user__email",
        "file_name",
        "description",
    ]

    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    readonly_fields = [
        "file_size",
        "mime_type",
        "created_at",
        "updated_at",
        "deleted_at",
        "deleted_by",
        "file_preview",
    ]

    fieldsets = (
        (
            "Document Information",
            {
                "fields": (
                    "user",
                    "document_type",
                    "file",
                    "file_preview",
                    "file_name",
                    "file_size",
                    "mime_type",
                    "description",
                )
            },
        ),
        (
            "Soft Delete",
            {
                "fields": (
                    "is_deleted",
                    "deleted_at",
                    "deleted_by",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    autocomplete_fields = ["user", "deleted_by"]

    actions = [
        "soft_delete_documents",
        "restore_documents",
    ]

    # ---------- List display helpers ----------

    def user_link(self, obj):
        url = reverse("admin:accounts_user_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)

    user_link.short_description = "User"

    def document_type_badge(self, obj):
        colors = {
            "aadhaar": "#007bff",
            "pan": "#28a745",
            "bank": "#17a2b8",
            "address": "#ffc107",
            "photo": "#6f42c1",
            "signature": "#fd7e14",
            "other": "#6c757d",
        }
        return format_html(
            '<span style="background-color:{};color:white;padding:3px 8px;'
            'border-radius:3px;font-size:10px;">{}</span>',
            colors.get(obj.document_type, "#6c757d"),
            obj.get_document_type_display(),
        )

    document_type_badge.short_description = "Type"

    def file_size_display(self, obj):
        """Render file_size in human-readable form."""
        size = float(obj.file_size or 0)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                size_str = f"{size:.1f}"
                return format_html("{} {}", size_str, unit)
            size /= 1024.0
        size_str = f"{size:.1f}"
        return format_html("{} {}", size_str, "TB")

    file_size_display.short_description = "Size"
    file_size_display.admin_order_field = "file_size"

    def file_preview_thumb(self, obj):
        """Small thumbnail or icon in list view."""
        if obj.file:
            if obj.mime_type and obj.mime_type.startswith("image/"):
                return format_html(
                    '<img src="{}" style="width:60px;height:40px;'
                    'object-fit:cover;border-radius:3px;" />',
                    obj.file.url,
                )
            return format_html("📄 {}", (obj.file_name or "")[:20])
        return format_html('<span style="color:#999;">—</span>')

    file_preview_thumb.short_description = "Preview"

    def file_preview(self, obj):
        """Big preview in detail page."""
        if obj.file:
            if obj.mime_type and obj.mime_type.startswith("image/"):
                url = obj.file.url
                return format_html(
                    '<a href="{}" target="_blank">'
                    '<img src="{}" style="max-width:400px;max-height:300px;border:1px solid #ddd;" />'
                    "</a><br>"
                    '<a href="{}" target="_blank" class="button" style="margin-top:10px;">Download</a>',
                    url,
                    url,
                    url,
                )
            else:
                return format_html(
                    '<div style="padding:10px;background:#f5f5f5;border-radius:5px;">'
                    "<strong>File:</strong> {}<br>"
                    "<strong>Size:</strong> {}<br>"
                    "<strong>Type:</strong> {}<br>"
                    '<a href="{}" target="_blank" class="button" style="margin-top:10px;">📄 Download</a>'
                    "</div>",
                    obj.file_name,
                    self.file_size_display(obj),
                    obj.mime_type or "Unknown",
                    obj.file.url,
                )
        return format_html('<span style="color:#999;">No file</span>')

    file_preview.short_description = "File Preview"

    # ---------- Actions ----------

    def soft_delete_documents(self, request, queryset):
        updated = queryset.filter(is_deleted=False).update(
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by=request.user,
        )
        self.message_user(
            request,
            f"{updated} document(s) soft deleted.",
            level=messages.SUCCESS,
        )

    soft_delete_documents.short_description = "🗑️ Soft Delete selected documents"

    def restore_documents(self, request, queryset):
        updated = queryset.filter(is_deleted=True).update(
            is_deleted=False,
            deleted_at=None,
            deleted_by=None,
        )
        self.message_user(
            request,
            f"{updated} document(s) restored.",
            level=messages.SUCCESS,
        )

    restore_documents.short_description = "↻ Restore selected documents"


# ============================================
# AUDIT LOG ADMIN (READ-ONLY)
# ============================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only admin for compliance audit logs."""

    list_display = [
        "created_at",
        "user_link",
        "action_badge",
        "description_short",
        "ip_address",
    ]

    list_filter = [
        AuditActionFilter,
        "created_at",
    ]

    search_fields = [
        "user__username",
        "user__email",
        "description",
        "ip_address",
    ]

    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    readonly_fields = [
        "user",
        "action",
        "description",
        "ip_address",
        "user_agent",
        "metadata",
        "metadata_display",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            "Event Information",
            {
                "fields": (
                    "created_at",
                    "user",
                    "action",
                    "description",
                )
            },
        ),
        (
            "Request Information",
            {
                "fields": (
                    "ip_address",
                    "user_agent",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Additional Data",
            {
                "fields": (
                    "metadata",
                    "metadata_display",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    formfield_overrides = {
        models.JSONField: {"widget": PrettyJSONWidget},
    }

    # Read-only admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # ---------- Helpers ----------

    def user_link(self, obj):
        if obj.user:
            url = reverse("admin:accounts_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return format_html('<span style="color:#999;">System</span>')

    user_link.short_description = "User"

    def action_badge(self, obj):
        colors = {
            "kyc_submit": "#007bff",
            "kyc_approve": "#28a745",
            "kyc_reject": "#dc3545",
            "document_upload": "#17a2b8",
            "document_delete": "#dc3545",
            "profile_update": "#ffc107",
            "login": "#6f42c1",
            "logout": "#6c757d",
            "password_change": "#fd7e14",
            "other": "#6c757d",
        }
        label = obj.get_action_display()
        return format_html(
            '<span style="background-color:{};color:white;padding:3px 8px;'
            'border-radius:3px;font-size:10px;">{}</span>',
            colors.get(obj.action, "#6c757d"),
            label,
        )

    action_badge.short_description = "Action"

    def description_short(self, obj):
        text = obj.description or ""
        if len(text) > 60:
            return format_html(
                '<span title="{}">{}...</span>',
                text,
                text[:60],
            )
        return text

    description_short.short_description = "Description"

    def metadata_display(self, obj):
        if not obj.metadata:
            return format_html('<span style="color:#999;">No metadata</span>')
        try:
            pretty = json.dumps(obj.metadata, indent=2, ensure_ascii=False)
        except TypeError:
            pretty = str(obj.metadata)
        return format_html(
            '<pre style="background:#f5f5f5;padding:10px;border-radius:5px;'
            'max-height:300px;overflow:auto;white-space:pre-wrap;">{}</pre>',
            pretty,
        )

    metadata_display.short_description = "Metadata (Formatted)"
