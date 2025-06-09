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
router.register("bill-sharing", views.BillSharingViewset, basename="bill-sharing")
router.register(
    "bill-sharing-payee", views.BillSharingPayeeViewset, basename="bill-sharing-payee"
)
router.register("cards", views.CardViewset, basename="cards")
router.register("card-requests", views.CardRequestViewset, basename="card-requests")
router.register(
    "card-management", views.CardManagementViewset, basename="card-management"
)
router.register("travel-notice", views.TravelNoticeViewset, basename="travel-notice")
router.register("complaints", views.ComplaintViewset, basename="complaints")
router.register(
    "complaint-category",
    views.ComplaintCategoryViewset,
    basename="complaint-category",
)
router.register("service-charges", views.BankChargesViewset, basename="service-charges")
urlpatterns = [
    path(
        "fx-rates/",
        views.ForexViewset.as_view(),
        name="fx-rates",
    ),
]

urlpatterns += router.urls
