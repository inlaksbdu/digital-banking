import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import gevent
from botocore.exceptions import ClientError
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from gevent import spawn
from loguru import logger

from .choices import DecisionChoices, DocumentTypeChoices, StageChoices
from .services.aws import aws_service


class OnboardingStage(models.Model):
    user = models.OneToOneField(
        "accounts.CustomUser", on_delete=models.CASCADE, related_name="onboarding_stage"
    )
    stage = models.CharField(
        max_length=20,
        choices=StageChoices.choices,
        default=StageChoices.DOCUMENT_UPLOAD,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "onboarding_stages"
        indexes = [
            models.Index(fields=["user", "stage"]),
            models.Index(fields=["stage", "updated_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.stage}"


class IdCardField(models.JSONField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("default", dict)
        super().__init__(*args, **kwargs)

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if value and not isinstance(value, dict):
            raise ValidationError("Field must be a dictionary")
        if value and ("content" not in value or "confidence" not in value):
            raise ValidationError('Field must contain "content" and "confidence" keys')


class IdCard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="id_card",
        null=True,
        blank=True,
    )
    email = models.EmailField(null=True, blank=True)

    first_name = IdCardField()
    middle_name = IdCardField(null=True, blank=True)
    last_name = IdCardField()
    date_of_birth = IdCardField()
    gender = IdCardField()
    id_number = IdCardField(null=True, blank=True)
    document_number = IdCardField()
    date_of_issue = IdCardField()
    date_of_expiry = IdCardField()
    country = IdCardField()
    state = IdCardField(null=True, blank=True)
    nationality = IdCardField(null=True, blank=True)
    mrz = IdCardField(null=True, blank=True)

    document_type = models.CharField(max_length=20, choices=DocumentTypeChoices.choices)

    verified = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(default=False)
    decision = models.CharField(
        max_length=20, choices=DecisionChoices.choices, default=DecisionChoices.PENDING
    )
    review_score = models.IntegerField(default=0)
    reject_score = models.IntegerField(default=0)

    longitude = models.FloatField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)

    front_image = models.ImageField(
        upload_to="id_cards/front",
        null=True,
        blank=True,
        help_text="Front side of the ID document",
    )
    back_image = models.ImageField(
        upload_to="id_cards/back",
        null=True,
        blank=True,
        help_text="Back side of the ID document",
    )

    self_image = models.ImageField(
        upload_to="id_cards/self",
        null=True,
        blank=True,
        help_text="Selfie with the ID document",
    )

    selfie_video = models.FileField(
        upload_to="id_cards/selfie_video",
        null=True,
        blank=True,
        help_text="Selfie video for verification",
    )

    additional_images = models.JSONField(
        default=list,
        blank=True,
        help_text="Additional image URLs/paths stored as JSON array",
    )

    id_number_text = models.CharField(
        max_length=100, blank=True, null=True, unique=True
    )
    document_number_text = models.CharField(max_length=100, blank=True, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "id_cards"
        indexes = [
            models.Index(fields=["user", "document_type"]),
            models.Index(fields=["decision", "created_at"]),
            models.Index(fields=["id_number_text"]),
            models.Index(fields=["document_number_text"]),
            models.Index(fields=["verified", "is_confirmed"]),
        ]

    def __str__(self):
        # Fallback to email if no user is associated
        identifier = self.user.username if self.user else (self.email or "Unknown")
        return f"ID Card for {identifier} ({self.document_type})"

    def save(self, *args, **kwargs):
        if self.id_number:
            self.id_number_text = self.id_number.get("content", "")
        if self.document_number:
            self.document_number_text = self.document_number.get("content", "")
        super().save(*args, **kwargs)

    @property
    def full_name(self) -> str:
        first = self.first_name.get("content", "") if self.first_name else ""
        last = self.last_name.get("content", "") if self.last_name else ""
        middle = self.middle_name.get("content", "") if self.middle_name else ""

        if middle:
            return f"{first} {middle} {last}".strip()
        return f"{first} {last}".strip()

    def _parse_date(self, date_str: str) -> date:
        try:
            return datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError:
            try:
                return datetime.fromisoformat(date_str).date()
            except ValueError:
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"]:
                    try:
                        return datetime.strptime(date_str, fmt).date()
                    except ValueError:
                        continue
                raise ValueError(f"Unable to parse date: {date_str}")

    @property
    def age(self) -> Optional[int]:
        if not self.date_of_birth or "content" not in self.date_of_birth:
            return None

        try:
            birth_date = self._parse_date(self.date_of_birth["content"])
            today = date.today()

            age = today.year - birth_date.year
            if today.month < birth_date.month or (
                today.month == birth_date.month and today.day < birth_date.day
            ):
                age -= 1

            return age
        except (ValueError, KeyError):
            return None

    @property
    def expired(self) -> Optional[bool]:
        if not self.date_of_expiry or "content" not in self.date_of_expiry:
            return None

        try:
            expiry_date = self._parse_date(self.date_of_expiry["content"])
            return expiry_date < date.today()
        except (ValueError, KeyError):
            return None

    @property
    def confidence_score(self) -> float:
        confidence_fields = [
            self.first_name,
            self.middle_name,
            self.last_name,
            self.date_of_birth,
            self.gender,
            self.id_number,
            self.document_number,
            self.date_of_issue,
            self.date_of_expiry,
            self.country,
            self.nationality,
            self.state,
            self.mrz,
        ]

        scores = []
        for field in confidence_fields:
            if field is not None and isinstance(field, dict) and "confidence" in field:
                scores.append(field["confidence"])

        if not scores:
            return 0.0

        return round(sum(scores) / len(scores), 2)

    @property
    def low_confidence_fields(self) -> list:
        threshold = 0.8
        low_confidence = []

        field_mapping = {
            "first_name": self.first_name,
            "middle_name": self.middle_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth,
            "gender": self.gender,
            "id_number": self.id_number,
            "document_number": self.document_number,
            "date_of_issue": self.date_of_issue,
            "date_of_expiry": self.date_of_expiry,
            "country": self.country,
            "nationality": self.nationality,
            "state": self.state,
            "mrz": self.mrz,
        }

        for field_name, field_value in field_mapping.items():
            if (
                field_value
                and isinstance(field_value, dict)
                and "confidence" in field_value
                and field_value["confidence"] < threshold
            ):
                low_confidence.append(
                    {
                        "field": field_name,
                        "confidence": field_value["confidence"],
                        "content": field_value.get("content", ""),
                    }
                )

        return low_confidence

    def get_field_value(self, field_name: str) -> Optional[str]:
        field_value = getattr(self, field_name, None)
        if field_value and isinstance(field_value, dict):
            return field_value.get("content")
        return field_value

    def get_field_confidence(self, field_name: str) -> Optional[float]:
        field_value = getattr(self, field_name, None)
        if field_value and isinstance(field_value, dict):
            return field_value.get("confidence")
        return None

    def to_dict(
        self,
        include: List[str] = ["*"],
        exclude: List[str] | None = None,
        show_field_confidence: bool = False,
    ) -> Dict[str, Any]:
        data = {}
        if "*" in include:
            include = [field.name for field in self._meta.fields]
        if exclude:
            include = [field for field in include if field not in exclude]

        image_fields = ["front_image", "back_image", "self_image", "selfie_video"]
        json_array_image_fields = ["additional_images"]

        for field in include:
            try:
                value = self.get_field_value(field)

                if field in image_fields and value:
                    if isinstance(value, str) and (
                        value.startswith("s3://") or value.startswith("id_cards/")
                    ):
                        try:
                            if value.startswith("s3://"):
                                key = aws_service.get_s3_key(value)
                            else:
                                key = value

                            presigned_url = aws_service.generate_presigned_url(key)
                            value = presigned_url if presigned_url else value
                        except Exception as e:
                            logger.error(
                                f"Error generating presigned URL for {field}: {e}"
                            )

                elif field in json_array_image_fields and value:
                    if isinstance(value, list):
                        presigned_urls = []
                        for url in value:
                            if isinstance(url, str) and (
                                url.startswith("s3://") or url.startswith("id_cards/")
                            ):
                                try:
                                    if url.startswith("s3://"):
                                        key = aws_service.get_s3_key(url)
                                    else:
                                        key = url

                                    presigned_url = aws_service.generate_presigned_url(
                                        key
                                    )
                                    presigned_urls.append(
                                        presigned_url if presigned_url else url
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"Error generating presigned URL for {url} in {field}: {e}"
                                    )
                                    presigned_urls.append(url)
                            else:
                                presigned_urls.append(url)
                        value = presigned_urls

                if show_field_confidence:
                    confidence = self.get_field_confidence(field)
                    if confidence is not None:
                        data[field] = {
                            "content": value,
                            "confidence": confidence,
                        }
                    else:
                        data[field] = value
                else:
                    data[field] = value

            except AttributeError:
                continue
            except Exception as e:
                logger.error(f"Error processing field {field}: {e}")
                continue

        return data


def delete_single_file_from_s3(file_ref, file_type):
    try:
        key = aws_service.get_s3_key(file_ref)
        aws_service.delete_from_s3(key)
        logger.info(f"Successfully deleted {file_type} from S3: {key}")
    except ClientError as e:
        logger.error(f"Error deleting {file_type} from S3: {e}")
    except Exception as e:
        logger.error(f"Unexpected error deleting {file_type} from S3: {e}")


@receiver(post_delete, sender=IdCard)
def delete_id_card_files_from_s3(sender, instance: IdCard, **kwargs):
    if not (instance.front_image or instance.back_image or instance.self_image):
        return

    try:
        deletion_tasks = []

        if instance.front_image:
            deletion_tasks.append(
                spawn(
                    delete_single_file_from_s3, instance.front_image.name, "front_image"
                )
            )

        if instance.back_image:
            deletion_tasks.append(
                spawn(
                    delete_single_file_from_s3, instance.back_image.name, "back_image"
                )
            )

        if instance.self_image:
            deletion_tasks.append(
                spawn(
                    delete_single_file_from_s3, instance.self_image.name, "self_image"
                )
            )

        if instance.selfie_video:
            deletion_tasks.append(
                spawn(
                    delete_single_file_from_s3,
                    instance.selfie_video.name,
                    "selfie_video",
                )
            )

        if instance.additional_images:
            for i, image in enumerate(instance.additional_images):
                deletion_tasks.append(
                    spawn(delete_single_file_from_s3, image, f"additional_image_{i}")
                )

        gevent.joinall(deletion_tasks)

        logger.info(f"Completed deletion of {len(deletion_tasks)} files from S3")

    except Exception as e:
        logger.error(f"Error connecting to S3: {e}")
