from typing import Any, Dict
from rest_framework import serializers
from datetime import date
from django.core.files.uploadedfile import InMemoryUploadedFile
from .models import IdCard, OnboardingStage
from .choices import DocumentTypeChoices
from .services.aws import aws_service
from loguru import logger


class IdCardFieldSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=500)
    confidence = serializers.FloatField(min_value=0.0, max_value=1.0)


class IdCardSerializer(serializers.ModelSerializer):
    confidence_score = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    expired = serializers.ReadOnlyField()
    low_confidence_fields = serializers.ReadOnlyField()

    front_image = serializers.SerializerMethodField()
    back_image = serializers.SerializerMethodField()
    self_image = serializers.SerializerMethodField()
    selfie_video = serializers.SerializerMethodField()
    additional_images = serializers.SerializerMethodField()

    class Meta:
        model = IdCard
        fields = [
            "id",
            "user",
            "email",
            "first_name",
            "middle_name",
            "last_name",
            "date_of_birth",
            "gender",
            "id_number",
            "document_number",
            "date_of_issue",
            "date_of_expiry",
            "country",
            "state",
            "nationality",
            "mrz",
            "document_type",
            "verified",
            "is_confirmed",
            "decision",
            "review_score",
            "reject_score",
            "longitude",
            "latitude",
            "front_image",
            "back_image",
            "self_image",
            "selfie_video",
            "additional_images",
            "created_at",
            "updated_at",
            "confidence_score",
            "full_name",
            "age",
            "expired",
            "low_confidence_fields",
        ]
        read_only_fields = [
            "id",
            "user",
            "email",
            "created_at",
            "updated_at",
            "confidence_score",
            "full_name",
            "age",
            "expired",
            "low_confidence_fields",
            "verified",
            "review_score",
            "reject_score",
            "front_image",
            "back_image",
            "self_image",
            "selfie_video",
            "additional_images",
        ]

    def _get_presigned_url_for_field(self, obj, field_name):
        """Helper method to generate presigned URL for image fields"""
        field_value = getattr(obj, field_name, None)
        if not field_value:
            return None

        # Handle string values (S3 URLs or file paths)
        if isinstance(field_value, str):
            if field_value.startswith("s3://") or field_value.startswith("id_cards/"):
                try:
                    if field_value.startswith("s3://"):
                        key = aws_service.get_s3_key(field_value)
                    else:
                        key = field_value

                    presigned_url = aws_service.generate_presigned_url(key)
                    return presigned_url if presigned_url else field_value
                except Exception as e:
                    logger.error(
                        f"Error generating presigned URL for {field_name}: {e}"
                    )
                    return field_value
            return field_value

        # Handle file objects
        if hasattr(field_value, "name") and field_value.name:
            try:
                key = (
                    aws_service.get_s3_key(field_value.name)
                    if field_value.name.startswith("s3://")
                    else field_value.name
                )
                presigned_url = aws_service.generate_presigned_url(key)
                return presigned_url if presigned_url else field_value.url
            except Exception as e:
                logger.error(f"Error generating presigned URL for {field_name}: {e}")
                return field_value.url if hasattr(field_value, "url") else None

        return None

    def get_front_image(self, obj):
        return self._get_presigned_url_for_field(obj, "front_image")

    def get_back_image(self, obj):
        return self._get_presigned_url_for_field(obj, "back_image")

    def get_self_image(self, obj):
        return self._get_presigned_url_for_field(obj, "self_image")

    def get_selfie_video(self, obj):
        return self._get_presigned_url_for_field(obj, "selfie_video")

    def get_additional_images(self, obj):
        """Handle additional_images which is a JSON array of URLs"""
        additional_images = obj.additional_images or []
        if not additional_images or not isinstance(additional_images, list):
            return []

        presigned_urls = []
        for url in additional_images:
            if isinstance(url, str) and (
                url.startswith("s3://") or url.startswith("id_cards/")
            ):
                try:
                    if url.startswith("s3://"):
                        key = aws_service.get_s3_key(url)
                    else:
                        key = url

                    presigned_url = aws_service.generate_presigned_url(key)
                    presigned_urls.append(presigned_url if presigned_url else url)
                except Exception as e:
                    logger.error(
                        f"Error generating presigned URL for additional image {url}: {e}"
                    )
                    presigned_urls.append(url)
            else:
                presigned_urls.append(url)

        return presigned_urls


class IdCardCreateSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Email of the customer")
    document_type = serializers.ChoiceField(
        choices=DocumentTypeChoices.choices, help_text="Type of document being uploaded"
    )
    image_front = serializers.ImageField(help_text="Front side of the ID document")
    image_back = serializers.ImageField(
        required=False,
        help_text="Back side of the ID document (optional for some documents)",
    )
    selfie = serializers.ImageField(help_text="Selfie photo for verification")
    selfie_video = serializers.FileField(
        required=False, help_text="Optional selfie video for enhanced verification"
    )

    def validate_image_front(self, value):
        return self._validate_image(value, "front")

    def validate_image_back(self, value):
        if value:
            return self._validate_image(value, "back")
        return value

    def validate_selfie(self, value):
        return self._validate_image(value, "selfie")

    def validate_selfie_video(self, value):
        if value:
            return self._validate_video(value, "selfie_video")
        return value

    def _validate_image(
        self, image: InMemoryUploadedFile, image_type: str
    ) -> InMemoryUploadedFile:
        MAX_SIZE = 10 * 1024 * 1024  # 10MB (increased for better quality)
        ALLOWED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]

        if image.size > MAX_SIZE:
            raise serializers.ValidationError(
                f"{image_type.title()} image size cannot exceed 10MB"
            )

        if image.content_type not in ALLOWED_TYPES:
            raise serializers.ValidationError(
                f"{image_type.title()} image must be JPEG, PNG, GIF, or WebP"
            )

        if image_type in ["front", "back"]:
            try:
                from PIL import Image

                img = Image.open(image)
                width, height = img.size

                image.seek(0)

                if width < 800 or height < 600:
                    raise serializers.ValidationError(
                        f"{image_type.title()} image should be at least 800x600 pixels for better OCR results"
                    )
            except ImportError:
                pass
            except Exception:
                raise serializers.ValidationError(f"Invalid {image_type} image format")

        return image

    def _validate_video(
        self, video: InMemoryUploadedFile, video_type: str
    ) -> InMemoryUploadedFile:
        MAX_SIZE = 50 * 1024 * 1024  # 50MB
        ALLOWED_TYPES = ["video/mp4", "video/webm", "video/mov", "video/avi"]

        if video.size > MAX_SIZE:
            raise serializers.ValidationError(
                f"{video_type.title()} video size cannot exceed 50MB"
            )

        if video.content_type not in ALLOWED_TYPES:
            raise serializers.ValidationError(
                f"{video_type.title()} video must be MP4, WebM, MOV, or AVI"
            )

        return video

    def validate(self, attrs: Dict[str, Any]):
        document_type = attrs.get("document_type")
        if not document_type:
            raise serializers.ValidationError("Document type is required")

        image_back = attrs.get("image_back")

        if document_type in [
            DocumentTypeChoices.NATIONAL_ID,
            DocumentTypeChoices.DRIVER_LICENSE,
        ]:
            if not image_back:
                raise serializers.ValidationError(
                    {
                        "image_back": f"{document_type.replace('_', ' ').title()} requires back side image"
                    }
                )

        return attrs


class IdCardConfirmSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=False)
    middle_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    date_of_birth = serializers.DateField(required=False)
    gender = serializers.CharField(max_length=20, required=False)
    id_number = serializers.CharField(max_length=100, required=False)
    document_number = serializers.CharField(max_length=100, required=False)
    date_of_issue = serializers.DateField(required=False)
    date_of_expiry = serializers.DateField(required=False)
    country = serializers.CharField(max_length=100, required=False)
    state = serializers.CharField(max_length=100, required=False)
    nationality = serializers.CharField(max_length=100, required=False)
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)

    def validate_date_of_expiry(self, value):
        if value and value < date.today():
            raise serializers.ValidationError(
                "Document expiry date cannot be in the past"
            )
        return value

    def validate_date_of_birth(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("Birth date cannot be in the future")

        # Check reasonable age limits (18-120 years)
        if value:
            today = date.today()
            age = (
                today.year
                - value.year
                - ((today.month, today.day) < (value.month, value.day))
            )
            # if age < 18:  # TODO: Uncomment this if we want to restrict users under 18
            #     raise serializers.ValidationError("User must be at least 18 years old")
            if age > 120:
                raise serializers.ValidationError("Invalid birth date")

        return value

    def validate_date_of_issue(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("Issue date cannot be in the future")
        return value

    def validate_id_number(self, value):
        if value and len(value.strip()) < 3:
            raise serializers.ValidationError("ID number is too short")
        return value

    def validate_document_number(self, value):
        if value and len(value.strip()) < 3:
            raise serializers.ValidationError("Document number is too short")
        return value


class OnboardingStageSerializer(serializers.ModelSerializer):
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)

    class Meta:
        model = OnboardingStage
        fields = [
            "user",
            "stage",
            "stage_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "user",
            "stage_display",
            "created_at",
            "updated_at",
        ]


class DocumentVerificationResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    id_card_id = serializers.UUIDField(required=False)
    confidence_score = serializers.FloatField(required=False)
    decision = serializers.CharField(required=False)
    warnings = serializers.ListField(required=False)
    low_confidence_fields = serializers.ListField(required=False)
