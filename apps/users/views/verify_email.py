from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError

from apps.users.serializers.verify_email import VerifyEmailSerializer
from apps.users.use_cases.verify_email_code import VerifyEmailCodeUseCase


class VerifyEmailView(APIView):
    @extend_schema(
        request=VerifyEmailSerializer,
        responses={200: VerifyEmailSerializer},
        tags=['users'],
    )
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            VerifyEmailCodeUseCase.execute(
                email=serializer.validated_data["email"],
                code=serializer.validated_data["code"],
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"detail": "Email успешно подтверждён"}, status=status.HTTP_200_OK)
