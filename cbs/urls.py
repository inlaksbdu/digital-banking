from rest_framework.routers import DefaultRouter
from . import views


app_name = "cbs"

router = DefaultRouter()

router.register("bank-accounts", views.BankAccountViewset, basename="bank-accounts")

urlpatterns = []

urlpatterns += router.urls
