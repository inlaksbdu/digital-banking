from rest_framework.routers import DefaultRouter
from . import views


app_name = "cbs"

router = DefaultRouter()

router.register("bank-accounts", views.BankAccountViewset, basename="bank-accounts")
router.register("transfer", views.TransferViewset, basename="transfer")
router.register("payment-billers", views.PaymentBiller, basename="payment-billers")
router.register("payments", views.PaymentViewset, basename="payments")

urlpatterns = []

urlpatterns += router.urls
