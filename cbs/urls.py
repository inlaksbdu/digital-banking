from rest_framework.routers import DefaultRouter
from . import views
from django.urls import path


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
router.register(
    "loan-categories", views.LoanCategoryViewset, basename="loan-categories"
)
router.register("loan-requests", views.LoanRequestViewset, basename="loan-requests")
router.register(
    "appointment-booking",
    views.AppointmentBookingViewset,
    basename="appointment-booking",
)
router.register("expense-limit", views.ExpenseLimitViewset, basename="expense-limit")
router.register(
    "cardless-withdrawal",
    views.CardlessWithdrawalViewset,
    basename="cardless-withdrawal",
)
router.register(
    "email-indemnity", views.EmailIndemnityViewset, basename="email-indemnity"
)
urlpatterns = [
    path(
        "fx-rates/",
        views.ForexViewset.as_view(),
        name="fx-rates",
    ),
]

urlpatterns += router.urls
