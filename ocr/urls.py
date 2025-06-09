from django.urls import path
from . import views

app_name = "ocr"

urlpatterns = [
    path(
        "onboarding/stage/",
        views.OnboardingStageView.as_view(),
        name="onboarding-stage",
    ),
    path("documents/upload/", views.DocumentOCRView.as_view(), name="document-upload"),
    path(
        "id-cards/<uuid:id>/confirm/",
        views.IdCardConfirmView.as_view(),
        name="id-card-confirm",
    ),
    path("id-cards/detail/", views.IdCardDetailView.as_view(), name="id-card-detail"),
    path("admin/id-cards/", views.IdCardListView.as_view(), name="admin-id-card-list"),
    path(
        "admin/id-cards/<uuid:id>/delete/",
        views.IdCardDeleteView.as_view(),
        name="admin-id-card-delete",
    ),
]
