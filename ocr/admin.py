from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import IdCard, OnboardingStage
from .choices import DecisionChoices
from django.db import models
from django.forms.widgets import ClearableFileInput
from .services.aws import aws_service


@admin.register(OnboardingStage)
class OnboardingStageAdmin(admin.ModelAdmin):
    list_display = ["user", "stage", "stage_display", "created_at", "updated_at"]
    list_filter = ["stage", "created_at", "updated_at"]
    search_fields = ["user__username", "user__email"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-updated_at"]

    def stage_display(self, obj):
        return obj.get_stage_display()

    stage_display.short_description = "Stage"  # type: ignore


class CustomClearableFileInput(ClearableFileInput):
    initial_text = ""
    input_text = "No file chosen"
    clear_checkbox_label = "Clear"


@admin.register(IdCard)
class IdCardAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "document_type",
        "full_name_display",
        "confidence_score_display",
        "decision",
        "verified",
        "is_confirmed",
        "created_at",
    ]
    list_filter = [
        "document_type",
        "decision",
        "verified",
        "is_confirmed",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "user__username",
        "user__email",
        "document_number_text",
        "id_number_text",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "confidence_score_display",
        "full_name_display",
        "age_display",
        "expired_display",
        "low_confidence_fields_display",
        "document_number_text",
        "id_number_text",
        "front_image_preview",
        "back_image_preview",
        "self_image_preview",
        "additional_images_preview",
        "first_name_display",
        "middle_name_display",
        "last_name_display",
        "date_of_birth_display",
        "gender_display",
        "id_number_display",
        "document_number_display",
        "date_of_issue_display",
        "date_of_expiry_display",
        "country_display",
        "state_display",
        "nationality_display",
        "mrz_display",
        "selfie_video_preview",
    ]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "id",
                    "user",
                    "document_type",
                    "verified",
                    "is_confirmed",
                    "decision",
                )
            },
        ),
        (
            "Document Data",
            {
                "fields": (
                    "first_name_display",
                    "middle_name_display",
                    "last_name_display",
                    "date_of_birth_display",
                    "gender_display",
                    "id_number_display",
                    "document_number_display",
                    "date_of_issue_display",
                    "date_of_expiry_display",
                    "country_display",
                    "state_display",
                    "nationality_display",
                    "mrz_display",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Verification Scores",
            {
                "fields": (
                    "review_score",
                    "reject_score",
                    "confidence_score_display",
                    "low_confidence_fields_display",
                )
            },
        ),
        ("Location", {"fields": ("longitude", "latitude"), "classes": ("collapse",)}),
        (
            "Images",
            {
                "fields": (
                    "front_image_preview",
                    "front_image",
                    "back_image_preview",
                    "back_image",
                    "self_image_preview",
                    "self_image",
                    "selfie_video_preview",
                    "selfie_video",
                    "additional_images_preview",
                    "additional_images",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Computed Fields",
            {
                "fields": (
                    "full_name_display",
                    "age_display",
                    "expired_display",
                    "document_number_text",
                    "id_number_text",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    ordering = ["-created_at"]
    formfield_overrides = {
        models.ImageField: {"widget": CustomClearableFileInput},
        models.FileField: {"widget": CustomClearableFileInput},
    }

    def full_name_display(self, obj):
        return obj.full_name or "N/A"

    full_name_display.short_description = "Full Name"  # type: ignore

    def confidence_score_display(self, obj):
        score = obj.confidence_score
        if score >= 0.8:
            color = "green"
        elif score >= 0.6:
            color = "orange"
        else:
            color = "red"
        # Pre-format the percentage string to avoid formatting SafeString with '%' spec
        percent = f"{score:.2%}"
        return format_html('<span style="color: {};">{}</span>', color, percent)

    confidence_score_display.short_description = "Confidence Score"  # type: ignore

    def age_display(self, obj):
        age = obj.age
        return f"{age} years" if age is not None else "N/A"

    age_display.short_description = "Age"  # type: ignore

    def expired_display(self, obj):
        expired = obj.expired
        if expired is None:
            return "Unknown"
        elif expired:
            return format_html('<span style="color: red;">Expired</span>')
        else:
            return format_html('<span style="color: green;">Valid</span>')

    expired_display.short_description = "Document Status"  # type: ignore

    def low_confidence_fields_display(self, obj):
        fields = obj.low_confidence_fields
        if not fields:
            return "None"

        field_list = []
        for field in fields:
            field_list.append(f"{field['field']} ({field['confidence']:.2%})")

        return mark_safe("<br>".join(field_list))

    low_confidence_fields_display.short_description = "Low Confidence Fields"  # type: ignore

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    actions = [
        "mark_as_verified",
        "mark_as_unverified",
        "approve_decision",
        "reject_decision",
    ]

    def mark_as_verified(self, request, queryset):
        updated = queryset.update(verified=True)
        self.message_user(request, f"{updated} ID cards marked as verified.")

    def mark_as_unverified(self, request, queryset):
        updated = queryset.update(verified=False)
        self.message_user(request, f"{updated} ID cards marked as unverified.")

    mark_as_unverified.short_description = "Mark selected ID cards as unverified"  # type: ignore

    def approve_decision(self, request, queryset):
        updated = queryset.update(decision=DecisionChoices.APPROVED)
        self.message_user(request, f"{updated} ID cards approved.")

    approve_decision.short_description = "Approve selected ID cards"  # type: ignore

    def reject_decision(self, request, queryset):
        updated = queryset.update(decision=DecisionChoices.REJECTED)
        self.message_user(request, f"{updated} ID cards rejected.")

    reject_decision.short_description = "Reject selected ID cards"  # type: ignore

    def front_image_preview(self, obj):
        name = obj.front_image.name if obj.front_image else None
        if not name:
            return "No image"
        # Determine S3 key
        key = aws_service.get_s3_key(name) if name.startswith("s3://") else name
        try:
            url = aws_service.generate_presigned_url(key)
        except Exception:
            url = obj.front_image.url
        return format_html('<img src="{}" style="max-height:200px;" />', url)

    front_image_preview.short_description = "Front Image Preview"  # type: ignore

    def back_image_preview(self, obj):
        name = obj.back_image.name if obj.back_image else None
        if not name:
            return "No image"
        key = aws_service.get_s3_key(name) if name.startswith("s3://") else name
        try:
            url = aws_service.generate_presigned_url(key)
        except Exception:
            url = obj.back_image.url
        return format_html('<img src="{}" style="max-height:200px;" />', url)

    back_image_preview.short_description = "Back Image Preview"  # type: ignore

    def self_image_preview(self, obj):
        name = obj.self_image.name if obj.self_image else None
        if not name:
            return "No image"
        key = aws_service.get_s3_key(name) if name.startswith("s3://") else name
        try:
            url = aws_service.generate_presigned_url(key)
        except Exception:
            url = obj.self_image.url
        return format_html('<img src="{}" style="max-height:200px;" />', url)

    self_image_preview.short_description = "Self Image Preview"  # type: ignore

    def additional_images_preview(self, obj):
        imgs = obj.additional_images or []
        if not imgs:
            return "No additional images"
        html = ""
        for img_url in imgs:
            if img_url.startswith("s3://"):
                key = aws_service.get_s3_key(img_url)
                try:
                    url = aws_service.generate_presigned_url(key)
                except Exception:
                    url = img_url
            else:
                url = img_url
            html += f'<img src="{url}" style="max-height:200px;margin:4px;" />'
        return format_html(html)

    additional_images_preview.short_description = "Additional Images Preview"  # type: ignore

    def selfie_video_preview(self, obj):
        name = obj.selfie_video.name if obj.selfie_video else None
        if not name:
            return "No video"
        key = aws_service.get_s3_key(name) if name.startswith("s3://") else name
        try:
            url = aws_service.generate_presigned_url(key)
        except Exception:
            url = obj.selfie_video.url
        return format_html(
            '<video src="{}" controls style="max-height:200px;" /></video>', url
        )

    selfie_video_preview.short_description = "Selfie Video Preview"  # type: ignore

    def _json_display(self, obj, field):
        data = getattr(obj, field) or {}
        content = data.get("content", "")
        conf = data.get("confidence")
        return f"{content} ({conf:.2%})" if conf is not None else content

    first_name_display = lambda self, obj: self._json_display(obj, "first_name")  # noqa: E731
    first_name_display.short_description = "First name"  # type: ignore
    middle_name_display = lambda self, obj: self._json_display(obj, "middle_name")  # noqa: E731
    middle_name_display.short_description = "Middle name"  # type: ignore
    last_name_display = lambda self, obj: self._json_display(obj, "last_name")  # noqa: E731
    last_name_display.short_description = "Last name"  # type: ignore
    date_of_birth_display = lambda self, obj: self._json_display(obj, "date_of_birth")  # noqa: E731
    date_of_birth_display.short_description = "Date of birth"  # type: ignore
    gender_display = lambda self, obj: self._json_display(obj, "gender")  # noqa: E731
    gender_display.short_description = "Gender"  # type: ignore
    id_number_display = lambda self, obj: self._json_display(obj, "id_number")  # noqa: E731
    id_number_display.short_description = "ID number"  # type: ignore
    document_number_display = lambda self, obj: self._json_display(  # noqa: E731
        obj, "document_number"
    )  
    document_number_display.short_description = "Document number"  # type: ignore
    date_of_issue_display = lambda self, obj: self._json_display(obj, "date_of_issue")  # noqa: E731
    date_of_issue_display.short_description = "Date of issue"  # type: ignore
    date_of_expiry_display = lambda self, obj: self._json_display(obj, "date_of_expiry")  # noqa: E731
    date_of_expiry_display.short_description = "Date of expiry"  # type: ignore
    country_display = lambda self, obj: self._json_display(obj, "country")  # noqa: E731
    country_display.short_description = "Country"  # type: ignore
    state_display = lambda self, obj: self._json_display(obj, "state")  # noqa: E731
    state_display.short_description = "State"  # type: ignore
    nationality_display = lambda self, obj: self._json_display(obj, "nationality")  # noqa: E731
    nationality_display.short_description = "Nationality"  # type: ignore
    mrz_display = lambda self, obj: self._json_display(obj, "mrz")  # noqa: E731
    mrz_display.short_description = "MRZ"  # type: ignore
