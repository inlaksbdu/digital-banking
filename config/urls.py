from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from django.views.i18n import set_language

urlpatterns = [
    path("digital/control/", admin.site.urls),
    path("i18n/", set_language, name="set_language"),
    path("accounts/", include("allauth.urls")),
    path("", include("dashboard.urls")),
    path("ocr/", include("ocr.urls")),
    path("datatables/", include("datatable.urls")),
    path("cbs/", include("cbs.urls")),
    path("auth/", include("accounts.urls")),
    path("digital/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "digital/api-docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "digital/api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

urlpatterns = (
    urlpatterns
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
)


if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
