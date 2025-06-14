from datetime import date
from typing import Any, Dict

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from loguru import logger
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from .choices import StageChoices
from .exceptions import (
    CardVerificationError,
    DocumentVerificationError,
    UnsupportedDocumentTypeError,
)
from .filters import IdCardFilter
from .models import IdCard, OnboardingStage
from .serializers import (
    IdCardConfirmSerializer,
    IdCardCreateSerializer,
    IdCardSerializer,
    OnboardingStageSerializer,
)
from .services.aws import aws_service
from .services.onboarding import onboarding_service
from .services.verification import verification_service

User = get_user_model()


class OnboardingStageView(generics.RetrieveAPIView):
    serializer_class = OnboardingStageSerializer
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    @method_decorator(vary_on_headers("Authorization"))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object(self):
        stage, created = OnboardingStage.objects.get_or_create(
            user=self.request.user, defaults={"stage": StageChoices.DOCUMENT_UPLOAD}
        )
        return stage


class DocumentOCRView(generics.CreateAPIView):
    serializer_class = IdCardCreateSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                # Prevent duplicate submissions by email
                email = serializer.validated_data.get("email")
                if email and IdCard.objects.filter(email=email).exists():
                    return Response(
                        {"error": "ID card already exists for this email"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Pass authenticated user if present, else None
                user = (
                    request.user
                    if getattr(request.user, "is_authenticated", False)
                    else None
                )
                logger.info(f"User: {user}")
                result = self._process_document_verification(
                    user, serializer.validated_data
                )

                return Response(result, status=status.HTTP_201_CREATED)

        except (CardVerificationError, UnsupportedDocumentTypeError) as e:
            logger.error(f"Verification error for user {request.user.id}: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except DocumentVerificationError as e:
            raise e
        except Exception as e:
            logger.error(
                f"Unexpected error during OCR for user {request.user.id}: {str(e)}"
            )
            return Response(
                {"error": "An unexpected error occurred during document verification"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _process_document_verification(
        self, user, validated_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        verification_result = verification_service.verify_document(
            validated_data["image_front"],
            validated_data["image_back"],
            validated_data["selfie"],
            validated_data.get("selfie_video"),
        )

        if verification_result.warnings:
            raise DocumentVerificationError(
                detail=list(
                    map(
                        lambda w: w.model_dump(exclude_none=True),
                        verification_result.warnings,
                    )
                ),
                error_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                response_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if not verification_result.success:
            raise CardVerificationError(
                "Document verification failed",
                error_code=status.HTTP_400_BAD_REQUEST,
                response_code=status.HTTP_400_BAD_REQUEST,
            )

        document_type = None
        for data_item in verification_result.data:
            if data_item.field == "documentType":
                type_mapping = {
                    "P": "passport",
                    "I": "national_id",
                    "D": "driver_license",
                }
                document_type = type_mapping.get(
                    data_item.value, data_item.value.lower()
                )
                break

        if not document_type:
            document_type = validated_data.get("document_type", "national_id")

        if not onboarding_service.is_document_type_supported(document_type):
            raise UnsupportedDocumentTypeError(
                f"Document type '{document_type}' is not supported",
                error_code=status.HTTP_400_BAD_REQUEST,
                response_code=status.HTTP_400_BAD_REQUEST,
            )

        expiry_date = None
        for data_item in verification_result.data:
            if data_item.field == "expiry":
                expiry_date = data_item.value
                break

        if expiry_date and onboarding_service.is_document_expired(expiry_date):
            raise CardVerificationError(
                "Document has expired",
                error_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                response_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Upload without requiring user id (type-ignore for validated_data types)
        s3_urls = aws_service.upload_to_s3(  # type: ignore
            validated_data["image_front"],
            validated_data.get("image_back"),
            validated_data["selfie"],
            validated_data.get("selfie_video"),
        )

        id_card = onboarding_service.create_id_card_from_verification(
            user=user,
            verification_result=verification_result,
            s3_urls=s3_urls,  # type: ignore
        )

        # Attach provided email
        if validated_data.get("email"):
            id_card.email = validated_data.get("email")
            id_card.save(update_fields=["email"])

        # onboarding_stage, _ = OnboardingStage.objects.get_or_create(
        #     user=user, defaults={"stage": StageChoices.ID_VERIFICATION}
        # )
        # onboarding_stage.stage = StageChoices.ID_VERIFICATION
        # onboarding_stage.save()

        if user:
            cache.delete(f"onboarding_stage_{user.pk}")

        ocr_data = id_card.to_dict(
            exclude=[
                "user",
                "id_number_text",
                "document_number_text",
                "updated_at",
                "additional_images",
                "front_image",
                "back_image",
                "self_image",
                "selfie_video",
            ],
            show_field_confidence=True,
        )

        return {
            "status": "success",
            "confidence_score": id_card.confidence_score,
            "decision": id_card.decision,
            "ocr_data": ocr_data,
            "warnings": [
                {
                    "code": w.code,
                    "description": w.description,
                    "severity": w.severity,
                    "confidence": w.confidence,
                }
                for w in verification_result.warnings
            ]
            if verification_result.warnings
            else [],
        }


class IdCardConfirmView(generics.UpdateAPIView):
    serializer_class = IdCardConfirmSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        email = getattr(self.request.user, "email", None)
        return get_object_or_404(IdCard.objects.select_related("user"), email=email)

    def update(self, request: Request, *args, **kwargs) -> Response:
        id_card = self.get_object()
        if not id_card.user:
            id_card.user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                for field_name, value in serializer.validated_data.items():  # type: ignore
                    if value is not None:
                        if field_name in ("latitude", "longitude"):
                            setattr(id_card, field_name, value)
                        else:
                            ocr_field_value = {
                                "content": self._format_value(value),
                                "confidence": 1.0,  # User confirmed data has 100% confidence
                            }
                            setattr(id_card, field_name, ocr_field_value)

                id_card.is_confirmed = True
                id_card.save()

                onboarding_stage, _ = OnboardingStage.objects.get_or_create(
                    user=request.user, defaults={"stage": StageChoices.ID_CONFIRMATION}
                )
                onboarding_stage.stage = StageChoices.ID_CONFIRMATION
                onboarding_stage.save()

                cache.delete(f"onboarding_stage_{request.user.pk}")

                return Response(
                    {"status": "success", "message": "ID card confirmed successfully"}
                )

        except Exception as e:
            logger.error(
                f"Error confirming ID card for user {request.user.pk}: {str(e)}"
            )
            return Response(
                {"error": "An error occurred while confirming the ID card"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _format_value(self, value):
        if isinstance(value, date):
            return value.strftime("%d/%m/%Y")
        return str(value)


class IdCardDetailView(generics.RetrieveAPIView):
    serializer_class = IdCardSerializer
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(cache_page(60 * 2))  # Cache for 2 minutes
    @method_decorator(vary_on_headers("Authorization"))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object(self):
        return get_object_or_404(
            IdCard.objects.select_related("user"), user=self.request.user
        )


class IdCardListView(generics.ListAPIView):
    serializer_class = IdCardSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_class = IdCardFilter
    search_fields = ["user__username", "user__email", "document_number_text"]
    ordering_fields = ["created_at", "updated_at", "confidence_score"]
    ordering = ["-created_at"]

    def get_queryset(self):  # type: ignore
        return IdCard.objects.select_related("user").prefetch_related(
            Prefetch("user", queryset=User.objects.only("id", "username", "email"))
        )


class IdCardDeleteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAdminUser]

    def get_object(self):
        return get_object_or_404(IdCard, id=self.kwargs.get("id"))

    def destroy(self, request, *args, **kwargs):
        id_card = self.get_object()
        id_card.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IdCardDetailByEmailView(generics.RetrieveAPIView):
    serializer_class = IdCardSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object(self):
        email = self.kwargs.get("email")
        return get_object_or_404(IdCard.objects.select_related("user"), email=email)
