from rest_framework.routers import DefaultRouter
from . import views


app_name = "cbs"

router = DefaultRouter()

router.register("bank-accounts", views.BankAccountViewset, basename="bank-accounts")
router.register("transfer", views.TransferViewset, basename="transfer")
router.register("payment-billers", views.PaymentBiller, basename="payment-billers")
router.register("payments", views.PaymentViewset, basename="payments")
router.register("bank-statement", views.BankStatementViewset, basename="bank-statement")
router.register("beneficiary", views.BeneficiaryViewset, basename="beneficiary")
router.register("standing-order", views.StandingOrderViewset, basename="standing-order")
router.register("cheque-request", views.ChequeRequestViewset, basename="cheque-request")

urlpatterns = []

urlpatterns += router.urls
