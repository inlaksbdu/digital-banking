from rest_framework.routers import DefaultRouter
from . import views


app_name = "cbs"

router = DefaultRouter()

router.register("bank-accounts", views.BankAccountViewset, basename="bank-accounts")
# router.register("transfer", views.TransferViewset, basename="transfer")

urlpatterns = []

urlpatterns += router.urls
