from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import SendEmailSerializer
from .services.email_service import send_dynamic_email


class SendEmailAPI(APIView):

    def post(self, request):
        print("Received data:", request.data)

        serializer = SendEmailSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                "success": False,
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        email_type = serializer.validated_data["email_type"]
        to = serializer.validated_data["to"]
        params = serializer.validated_data["params"]

        try:
            result = send_dynamic_email(email_type, to, params)
            return Response({
                "success": True,
                "details": result
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)