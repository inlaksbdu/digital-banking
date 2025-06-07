from rest_framework.routers import DefaultRouter
from . import views


app_name = "data-tables"

router = DefaultRouter()

router.register(
    "security-question",
    views.SecurityQuestionviewset,
    basename="security-question",
)

router.register(
    "id-type",
    views.IDTypeViewset,
    basename="id-type",
)

router.register(
    "occupation",
    views.OccupationViewset,
    basename="occupation",
)

router.register(
    "transaction-purpose",
    views.TransactionPurposeViewset,
    basename="transaction-purpose",
)
router.register("branches", views.BranchesViewset, basename="branches")
router.register("atm", views.ATMsViewset, basename="atm")
router.register("account-types", views.AccountCategoryViewset, basename="account-types")
router.register("other-banks", views.OtherBankViewset, basename="other-banks")
router.register(
    "terms-and-conditions",
    views.TermsAndConditionsViewset,
    basename="terms-and-conditions",
)
router.register(
    "card-service-reason", views.CardReasonViewset, basename="card-service-reason"
)
router.register("swift-code", views.SwiftCodeViewset, basename="swift-code")
router.register(
    "network-proviers", views.NetworkProvidersViewset, basename="network-proviers"
)
router.register(
    "telco-data-plan", views.TelcoDataPlanViewset, basename="telco-data-plan"
)

urlpatterns = []

urlpatterns += router.urls
