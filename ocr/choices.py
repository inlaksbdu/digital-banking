from django.db import models


class StageChoices(models.TextChoices):
    DOCUMENT_UPLOAD = "document_upload", "Document Upload"
    ID_VERIFICATION = "id_verification", "ID Verification"
    ID_CONFIRMATION = "id_confirmation", "ID Confirmation"
    LIVENESS_CHECK = "liveness_check", "Liveness Check"
    COMPLETED = "completed", "Completed"


class DocumentTypeChoices(models.TextChoices):
    PASSPORT = "passport", "Passport"
    NATIONAL_ID = "national_id", "National ID"
    DRIVER_LICENSE = "driver_license", "Driver License"


class DecisionChoices(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    REVIEW = "review", "Needs Review"
