from rest_framework.routers import DefaultRouter
from . import views

# from django.urls import path


app_name = "cbs"

router = DefaultRouter()

router.register("bank-accounts", views.BankAccountViewset, basename="bank-accounts")

urlpatterns = []

urlpatterns += router.urls
