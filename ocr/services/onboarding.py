from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction

from ..choices import DocumentTypeChoices
from ..exceptions import (
    CardAlreadyExistsError,
    CardVerificationError,
    UnsupportedDocumentTypeError,
)
from ..models import IdCard

User = get_user_model()


def map_field(fields: List[dict], field_name: str) -> Optional[Dict[str, Any]]:
    field = next((f for f in fields if f["field"] == field_name), None)
    if not field:
        return None
    return {"content": field["value"], "confidence": field["confidence"]}


class OnboardingService:
    SUPPORTED_DOCUMENT_TYPES = [choice[0] for choice in DocumentTypeChoices.choices]

    def get_id_card_by_user(self, user) -> Optional[IdCard]:
        try:
            return IdCard.objects.get(user=user)
        except IdCard.DoesNotExist:
            return None

    def is_document_type_supported(self, document_type: str) -> bool:
        return document_type in self.SUPPORTED_DOCUMENT_TYPES

    def is_document_expired(self, expiry_date: str) -> bool:
        if not expiry_date:
            return False

        try:
            for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"]:
                try:
                    exp_date = datetime.strptime(expiry_date, fmt).date()
                    return exp_date < date.today()
                except ValueError:
                    continue
            return False
        except Exception:
            return False

    def create_id_card_from_verification(
        self,
        user,
        verification_result,
        s3_urls: Dict[Literal["front", "back", "selfie", "selfie_video"], str],
    ) -> IdCard:
        with transaction.atomic():
            if IdCard.objects.filter(user=user).exists():
                raise CardAlreadyExistsError("ID card already exists for this user")

            fields = [
                {
                    "field": item.field,
                    "value": item.value,
                    "confidence": item.confidence,
                }
                for item in verification_result.data
            ]

            doc_type_field = map_field(fields, "documentType")
            if not doc_type_field:
                raise CardVerificationError("Document type is required")

            # Convert document type codes to our choices
            doc_type_mapping = {
                "P": DocumentTypeChoices.PASSPORT,
                "I": DocumentTypeChoices.NATIONAL_ID,
                "D": DocumentTypeChoices.DRIVER_LICENSE,
            }

            doc_type = doc_type_mapping.get(
                doc_type_field["content"], doc_type_field["content"].lower()
            )

            if not self.is_document_type_supported(doc_type):
                raise UnsupportedDocumentTypeError(
                    f"Unsupported document type: {doc_type}"
                )

            id_card = IdCard.objects.create(
                user=user,
                first_name=map_field(fields, "firstName"),
                middle_name=map_field(fields, "middleName"),
                last_name=map_field(fields, "lastName"),
                date_of_birth=map_field(fields, "dob"),
                gender=map_field(fields, "sex"),
                id_number=map_field(fields, "personalNumber"),
                document_number=map_field(fields, "documentNumber"),
                date_of_issue=map_field(fields, "issued"),
                date_of_expiry=map_field(fields, "expiry"),
                country=map_field(fields, "countryFull"),
                state=map_field(fields, "stateFull"),
                nationality=map_field(fields, "nationalityFull"),
                mrz=map_field(fields, "mrz"),
                document_type=doc_type,
                decision=verification_result.decision,
                review_score=verification_result.review_score,
                reject_score=verification_result.reject_score,
                selfie_video=s3_urls.get("selfie_video"),
                front_image=s3_urls.get("front"),
                back_image=s3_urls.get("back"),
                self_image=s3_urls.get("selfie"),
                additional_images=list(
                    set(s3_urls.values())
                    - set(
                        [
                            s3_urls.get("front"),
                            s3_urls.get("back"),
                            s3_urls.get("selfie"),
                            s3_urls.get("selfie_video"),
                        ]
                    )
                )
                if s3_urls
                else [],
            )

            return id_card

    def validate_image_file(
        self,
        file: InMemoryUploadedFile,
        max_size: int = 5 * 1024 * 1024,  # 5MB
        allowed_types: Optional[List[str]] = None,
    ) -> None:
        if allowed_types is None:
            allowed_types = ["image/jpeg", "image/png", "image/gif"]

        if not file:
            raise CardVerificationError("File is required")

        if file.size == 0:
            raise CardVerificationError(f"File {file.name} is empty")

        if file.size > max_size:
            raise CardVerificationError(
                f"File {file.name} size ({file.size} bytes) exceeds maximum allowed size ({max_size} bytes)"
            )

        if file.content_type not in allowed_types:
            raise CardVerificationError(
                f"File {file.name} type ({file.content_type}) is not allowed. "
                f"Allowed types are: {', '.join(allowed_types)}"
            )


onboarding_service = OnboardingService()
