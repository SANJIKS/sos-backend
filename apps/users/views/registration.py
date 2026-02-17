from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.serializers.registration import RegisterSerializer
from apps.users.services.code_generator import generate_confirmation_code
from apps.users.use_cases.create_confirm_code import CreateConfirmCodeUseCase
from apps.users.use_cases.registration import RegisterUserUseCase

from apps.users.tasks import send_email_confirmation_code


class RegisterView(APIView):
    @extend_schema(
        request=RegisterSerializer,
        responses={201: RegisterSerializer},
        tags=['users'],
    )
    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        use_case = RegisterUserUseCase(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            phone=serializer.validated_data.get('phone'),
            consent_data_processing=serializer.validated_data['consent_data_processing']
        )
        user = use_case.execute()
        CreateConfirmCodeUseCase.execute(user)

        return Response({"detail": "Регистрация прошла успешно. Подтвердите email."}, status=status.HTTP_201_CREATED)
