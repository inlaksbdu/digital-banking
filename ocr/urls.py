from django.urls import path
from . import views

app_name = "ocr"

urlpatterns = [
    # Onboarding stage
    path(
        "onboarding/stage/",
        views.OnboardingStageView.as_view(),
        name="onboarding-stage",
    ),
    # Document OCR and verification
    path("documents/upload/", views.DocumentOCRView.as_view(), name="document-upload"),
    # ID card management
    path(
        "id-cards/<uuid:id>/confirm/",
        views.IdCardConfirmView.as_view(),
        name="id-card-confirm",
    ),
    path("id-cards/detail/", views.IdCardDetailView.as_view(), name="id-card-detail"),
    # Admin views
    path("admin/id-cards/", views.IdCardListView.as_view(), name="admin-id-card-list"),
    path(
        "admin/id-cards/low-confidence/",
        views.LowConfidenceIdCardsView.as_view(),
        name="admin-low-confidence",
    ),
]
