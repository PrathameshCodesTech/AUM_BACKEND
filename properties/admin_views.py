"""
Property Admin Views
APIs for admin property management
"""
import logging

from django.utils import timezone
from django.db.models import Q
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from accounts.permissions import IsAdmin
from .models import Property, PropertyImage, PropertyDocument, PropertyUnit
from .admin_serializers import (
    AdminPropertyListSerializer,
    AdminPropertyDetailSerializer,
    AdminPropertyCreateUpdateSerializer,
    AdminPropertyActionSerializer,
    PropertyUnitSerializer,
    PropertyImageSerializer,
    PropertyDocumentSerializer,
    PropertyImageUploadSerializer,
    PropertyDocumentUploadSerializer,
    PropertyUnitCreateUpdateSerializer,
)

logger = logging.getLogger(__name__)


# ========================================
# PROPERTY MANAGEMENT
# ========================================

class AdminPropertyListView(generics.ListAPIView):
    """
    GET /api/admin/properties/

    List all properties with filters
    Query params:
    - search: Search by name, address, city
    - status: Filter by status (draft, pending_approval, approved, live, ...)
    - property_type: Filter by type (HYBRID/EQUITY/DEBT/INCOME)
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = AdminPropertyListSerializer

    def get_queryset(self):
        queryset = (
            Property.objects.filter(is_deleted=False)
            .select_related("developer")
            .order_by("-created_at")
        )

        # Search
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(address__icontains=search)
                | Q(city__icontains=search)
            )

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by property type
        property_type = self.request.query_params.get("property_type")
        if property_type:
            queryset = queryset.filter(property_type=property_type)

        return queryset


class AdminPropertyDetailView(APIView):
    """
    GET /api/admin/properties/{property_id}/

    Get detailed property information
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, property_id):
        try:
            property_obj = Property.objects.select_related("developer").get(
                id=property_id, is_deleted=False
            )
        except Property.DoesNotExist:
            return Response(
                {"success": False, "message": "Property not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminPropertyDetailSerializer(
            property_obj, context={"request": request}
        )
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class AdminPropertyCreateView(APIView):
    """
    POST /api/admin/properties/create/

    Create new property
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = AdminPropertyCreateUpdateSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            property_obj = serializer.save()

            logger.info(
                f"✅ Property created by admin {request.user.username}: {property_obj.name}"
            )

            detail = AdminPropertyDetailSerializer(
                property_obj, context={"request": request}
            ).data

            return Response(
                {
                    "success": True,
                    "message": "Property created successfully",
                    "data": detail,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"❌ Error creating property: {str(e)}")
            return Response(
                {
                    "success": False,
                    "message": f"Failed to create property: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminPropertyUpdateView(APIView):
    """
    PUT /api/admin/properties/{property_id}/update/

    Update existing property
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def put(self, request, property_id):
        try:
            property_obj = Property.objects.get(id=property_id, is_deleted=False)
        except Property.DoesNotExist:
            return Response(
                {"success": False, "message": "Property not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminPropertyCreateUpdateSerializer(
            property_obj,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            property_obj = serializer.save()

            logger.info(
                f"✅ Property updated by admin {request.user.username}: {property_obj.name}"
            )

            detail = AdminPropertyDetailSerializer(
                property_obj, context={"request": request}
            ).data

            return Response(
                {
                    "success": True,
                    "message": "Property updated successfully",
                    "data": detail,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"❌ Error updating property: {str(e)}")
            return Response(
                {
                    "success": False,
                    "message": f"Failed to update property: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminPropertyDeleteView(APIView):
    """
    DELETE /api/admin/properties/{property_id}/delete/

    Delete property (soft delete)
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def delete(self, request, property_id):
        try:
            property_obj = Property.objects.get(id=property_id, is_deleted=False)
        except Property.DoesNotExist:
            return Response(
                {"success": False, "message": "Property not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Soft delete
        property_obj.is_deleted = True
        property_obj.deleted_at = timezone.now()
        # assuming SoftDeleteModel has deleted_by
        property_obj.deleted_by = request.user
        property_obj.save()

        logger.info(
            f"✅ Property deleted by admin {request.user.username}: {property_obj.name}"
        )

        return Response(
            {"success": True, "message": "Property deleted successfully"},
            status=status.HTTP_200_OK,
        )


class AdminPropertyActionView(APIView):
    """
    POST /api/admin/properties/{property_id}/action/

    Perform actions on property:
    - approve / reject
    - publish / unpublish
    - archive
    - feature / unfeature
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, property_id):
        try:
            property_obj = Property.objects.get(id=property_id, is_deleted=False)
        except Property.DoesNotExist:
            return Response(
                {"success": False, "message": "Property not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminPropertyActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action = serializer.validated_data["action"]
        rejection_reason = serializer.validated_data.get("rejection_reason", "")
        now = timezone.now()
        message = ""

        # ----- APPROVAL FLOW -----
        if action == "approve":
            property_obj.status = "approved"
            property_obj.approved_by = request.user
            property_obj.approved_at = now
            property_obj.rejection_reason = ""
            message = f'Property "{property_obj.name}" approved successfully'

        elif action == "reject":
            # keep it as draft with rejection reason
            property_obj.status = "draft"
            property_obj.approved_by = None
            property_obj.approved_at = None
            property_obj.rejection_reason = rejection_reason
            property_obj.is_published = False
            property_obj.is_featured = False
            message = f'Property "{property_obj.name}" rejected'

        # ----- PUBLISH FLOW -----
        elif action == "publish":
            # if not yet approved, first mark approved, then live
            if property_obj.status in ["draft", "pending_approval"]:
                property_obj.status = "approved"
            # make it live
            if property_obj.status == "approved":
                property_obj.status = "live"

            property_obj.is_published = True
            # for now we treat publish as public sale
            property_obj.is_public_sale = True
            message = f'Property "{property_obj.name}" published (live)'

        elif action == "unpublish":
            property_obj.is_published = False
            # if it was live, move it back to approved
            if property_obj.status == "live":
                property_obj.status = "approved"
            message = f'Property "{property_obj.name}" unpublished'

        # ----- ARCHIVE / CLOSE -----
        elif action == "archive":
            property_obj.status = "closed"
            property_obj.is_published = False
            property_obj.is_public_sale = False
            property_obj.is_featured = False
            message = f'Property "{property_obj.name}" archived (closed)'

        # ----- FEATURE TOGGLE -----
        elif action == "feature":
            property_obj.is_featured = True
            message = f'Property "{property_obj.name}" marked as featured'

        elif action == "unfeature":
            property_obj.is_featured = False
            message = f'Property "{property_obj.name}" removed from featured'

        property_obj.save()

        logger.info(
            f"✅ Admin {request.user.username} performed '{action}' on property: {property_obj.name}"
        )

        detail = AdminPropertyDetailSerializer(
            property_obj, context={"request": request}
        ).data

        return Response(
            {"success": True, "message": message, "data": detail},
            status=status.HTTP_200_OK,
        )


# ========================================
# IMAGE MANAGEMENT
# ========================================

class PropertyImageListView(generics.ListAPIView):
    """
    GET /api/admin/properties/{property_id}/images/
    List all images for a property
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = PropertyImageSerializer

    def get_queryset(self):
        property_id = self.kwargs.get("property_id")
        return PropertyImage.objects.filter(property_id=property_id).order_by("order")


class PropertyImageUploadView(APIView):
    """
    POST /api/admin/properties/{property_id}/images/upload/
    Upload new image for property
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, property_id):
        try:
            property_obj = Property.objects.get(id=property_id)
        except Property.DoesNotExist:
            return Response(
                {"success": False, "message": "Property not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ⬇️ use request.data directly, no .copy()
        serializer = PropertyImageUploadSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning(f"Image upload errors: {serializer.errors}")
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ⬇️ inject property here
        image = serializer.save(property=property_obj)

        logger.info(
            f"✅ Image uploaded for property {property_obj.name} by {request.user.username}"
        )

        return Response(
            {
                "success": True,
                "message": "Image uploaded successfully",
                "data": PropertyImageSerializer(
                    image, context={"request": request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )



class PropertyImageDeleteView(APIView):
    """
    DELETE /api/admin/properties/{property_id}/images/{image_id}/
    Delete property image
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def delete(self, request, property_id, image_id):
        try:
            image = PropertyImage.objects.get(id=image_id, property_id=property_id)
        except PropertyImage.DoesNotExist:
            return Response(
                {"success": False, "message": "Image not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        image.delete()

        logger.info(
            f"✅ Image deleted from property {property_id} by {request.user.username}"
        )

        return Response(
            {"success": True, "message": "Image deleted successfully"},
            status=status.HTTP_200_OK,
        )


# ========================================
# DOCUMENT MANAGEMENT
# ========================================

class PropertyDocumentListView(generics.ListAPIView):
    """
    GET /api/admin/properties/{property_id}/documents/
    List all documents for a property
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = PropertyDocumentSerializer

    def get_queryset(self):
        property_id = self.kwargs.get("property_id")
        return PropertyDocument.objects.filter(property_id=property_id).order_by(
            "-created_at"
        )


class PropertyDocumentUploadView(APIView):
    """
    POST /api/admin/properties/{property_id}/documents/upload/
    Upload new document for property
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, property_id):
        try:
            property_obj = Property.objects.get(id=property_id)
        except Property.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Property not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ❌ DON'T: data = request.data.copy()  # this is causing the BufferedRandom deepcopy error

        # ✅ Just pass request.data directly; DRF handles the file
        serializer = PropertyDocumentUploadSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ✅ Inject property + uploaded_by via save kwargs
        document = serializer.save(
            property=property_obj,
            uploaded_by=request.user,
        )

        logger.info(
            f"✅ Document uploaded for property {property_obj.name} by {request.user.username}"
        )

        return Response(
            {
                "success": True,
                "message": "Document uploaded successfully",
                "data": PropertyDocumentSerializer(
                    document, context={"request": request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PropertyDocumentDeleteView(APIView):
    """
    DELETE /api/admin/properties/{property_id}/documents/{document_id}/
    Delete property document
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def delete(self, request, property_id, document_id):
        try:
            document = PropertyDocument.objects.get(
                id=document_id, property_id=property_id
            )
        except PropertyDocument.DoesNotExist:
            return Response(
                {"success": False, "message": "Document not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        document.delete()

        logger.info(
            f"✅ Document deleted from property {property_id} by {request.user.username}"
        )

        return Response(
            {"success": True, "message": "Document deleted successfully"},
            status=status.HTTP_200_OK,
        )


# ========================================
# UNIT MANAGEMENT
# ========================================

class PropertyUnitListView(generics.ListAPIView):
    """
    GET /api/admin/properties/{property_id}/units/
    List all units for a property
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = PropertyUnitSerializer

    def get_queryset(self):
        property_id = self.kwargs.get("property_id")
        return PropertyUnit.objects.filter(property_id=property_id).order_by(
            "unit_number"
        )


class PropertyUnitCreateView(APIView):
    """
    POST /api/admin/properties/{property_id}/units/create/
    Create new unit for property
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, property_id):
        try:
            property_obj = Property.objects.get(id=property_id, is_deleted=False)
        except Property.DoesNotExist:
            return Response(
                {"success": False, "message": "Property not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data.copy()
        data["property"] = property_id

        serializer = PropertyUnitCreateUpdateSerializer(data=data)

        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unit = serializer.save()

        logger.info(
            f"✅ Unit created for property {property_obj.name} by {request.user.username}"
        )

        return Response(
            {
                "success": True,
                "message": "Unit created successfully",
                "data": PropertyUnitSerializer(unit).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PropertyUnitUpdateView(APIView):
    """
    PUT /api/admin/properties/{property_id}/units/{unit_id}/update/
    Update property unit
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def put(self, request, property_id, unit_id):
        try:
            unit = PropertyUnit.objects.get(id=unit_id, property_id=property_id)
        except PropertyUnit.DoesNotExist:
            return Response(
                {"success": False, "message": "Unit not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PropertyUnitCreateUpdateSerializer(
            unit, data=request.data, partial=True
        )

        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unit = serializer.save()

        logger.info(
            f"✅ Unit updated for property {property_id} by {request.user.username}"
        )

        return Response(
            {
                "success": True,
                "message": "Unit updated successfully",
                "data": PropertyUnitSerializer(unit).data,
            },
            status=status.HTTP_200_OK,
        )


class PropertyUnitDeleteView(APIView):
    """
    DELETE /api/admin/properties/{property_id}/units/{unit_id}/
    Delete property unit
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def delete(self, request, property_id, unit_id):
        try:
            unit = PropertyUnit.objects.get(id=unit_id, property_id=property_id)
        except PropertyUnit.DoesNotExist:
            return Response(
                {"success": False, "message": "Unit not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        unit.delete()

        logger.info(
            f"✅ Unit deleted from property {property_id} by {request.user.username}"
        )

        return Response(
            {"success": True, "message": "Unit deleted successfully"},
            status=status.HTTP_200_OK,
        )

class PropertyTypeListView(APIView):
    """
    GET /api/admin/properties/types/
    Returns all property_type choices (for dropdown)
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        choices = [
            {"value": key, "label": label}
            for key, label in Property.PROPERTY_TYPE_CHOICES
        ]
        return Response({"success": True, "data": choices})