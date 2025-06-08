# Register your models here.

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import IdCard, OnboardingStage
from .choices import DecisionChoices


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
                    "front_image",
                    "back_image",
                    "self_image",
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
        return format_html('<span style="color: {};">{:.2%}</span>', color, score)

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
