
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.throttling import LoginRateThrottle

from . import services
from .serializers import (
    OTPSendSerializer, OTPVerifySerializer, RegisterSerializer,
    ShebaTokenObtainPairSerializer, SwitchRoleSerializer, UserSerializer,
)

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = services.register_user(
            phone=data.get("phone"),
            email=data.get("email"),
            password=data["password"],
            full_name=data.get("full_name", ""),
            role=data["role"],
        )

        if user.phone:
            services.send_phone_otp(phone=user.phone)

        return Response(
            {
                "user": UserSerializer(user).data,
                "otp_sent": bool(user.phone),
            },
            status=status.HTTP_201_CREATED,
        )


class OTPSendView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp = services.send_phone_otp(
            phone=serializer.validated_data["phone"],
            purpose=serializer.validated_data["purpose"],
        )
        return Response(
            {"sent": True, "expires_at": otp.expires_at},
            status=status.HTTP_200_OK,
        )


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = services.verify_phone_otp(
            phone=serializer.validated_data["phone"],
            code=serializer.validated_data["code"],
            purpose=serializer.validated_data["purpose"],
        )

        payload = {"verified": True}
        if user is not None:
            payload["user"] = UserSerializer(user).data
        return Response(payload, status=status.HTTP_200_OK)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]
    serializer_class = ShebaTokenObtainPairSerializer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"error": {"code": "refresh_required",
                           "message": "A refresh token is required.",
                           "details": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh).blacklist()
        except Exception:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data,
                                    partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SwitchRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SwitchRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = services.switch_active_role(
            user_id=request.user.id,
            role=serializer.validated_data["role"],
        )
        return Response(UserSerializer(user).data)


class AddProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SwitchRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        services.create_profile(
            user_id=request.user.id,
            role=serializer.validated_data["role"],
        )
        request.user.refresh_from_db()
        return Response(UserSerializer(request.user).data,
                        status=status.HTTP_201_CREATED)
