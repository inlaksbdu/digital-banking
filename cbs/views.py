from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import HttpRequest
from . import models
from . import serializers
from rest_framework.viewsets import ModelViewSet
from rest_framework import permissions as rest_permissions
from helpers import exceptions
from t24.t24_requests import T24Requests
from . import tasks as celery_tasks
from loguru import logger
from drf_spectacular.utils import extend_schema

# Create your views here.


@extend_schema(tags=["Bank Accounts"])
class BankAccountViewset(ModelViewSet):
    queryset = models.BankAccount.objects.all()
    serializer_class = serializers.BankAccountSerializer
    permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get", "post"]
    filterset_fields = ("id",)

    def perform_create(self, serializer):
        raise exceptions.NotAuthorizedException()

    def get_queryset(self):
        logger.info("=== updating bank accounts ==")
        user = self.request.user
        queryset = self.queryset.filter(user=user)
        # update various account balances

        for obj in queryset:
            T24Requests.update_account_details(account_number=obj.account_number)
            obj.refresh_from_db()

        # update customer bank accounts
        if hasattr(user, "customer_profile"):
            logger.info("=== calling getting other accounts")
            celery_tasks.update_customer_bank_accounts.delay(
                customer_id=user.customer_profile.t24_customer_id
            )
        return queryset

    @action(
        methods=["post"],
        detail=False,
        url_path="validate-account",
        url_name="validate-account",
        permission_classes=[rest_permissions.IsAuthenticated],
        serializer_class=serializers.ValidateAccountNumberSerializer,
    )
    def validate_account(self, request: HttpRequest):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account_number = serializer.validated_data["account_number"]
        response = T24Requests.get_account_details(account_number=account_number)
        if response:
            data = {
                "account_number": response[0]["accountNo"],
                "account_name": response[0]["accountName"],
                "account_category": response[0]["accountCategory"],
            }
        elif models.BankAccount.objects.filter(account_number=account_number).exists():
            obj = models.BankAccount.objects.get(account_number=account_number)
            data = {
                "account_number": obj.account_number,
                "account_name": obj.account_name,
                "account_category": obj.account_category,
            }
        else:
            raise exceptions.AccountNumberNotExist()

        return Response(
            data=data,
            status=status.HTTP_200_OK,
        )

    @action(
        methods=["post"],
        detail=False,
        url_path="check-balance",
        url_name="check-balance",
        permission_classes=[rest_permissions.IsAuthenticated],
        serializer_class=serializers.ValidateAccountNumberSerializer,
    )
    def check_balance(self, request: HttpRequest):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account_number = serializer.validated_data["account_number"]
        response = T24Requests.get_account_details(account_number=account_number)

        if response:
            data = {
                "account_number": response[0]["accountNo"],
                "account_name": response[0]["accountName"],
                "account_category": response[0]["accountCategory"],
                "account_balance": (
                    response[0]["workingBalance"]
                    if "workingBalance" in response[0]
                    else 0.00
                ),
            }
        else:
            data = {
                "status": False,
                "message": "This service is not available at the moment",
            }

        return Response(
            data=data,
            status=status.HTTP_200_OK,
        )

    @action(
        methods=["get"],
        detail=True,
        url_path="set-as-default",
        url_name="set-as-default",
        permission_classes=[rest_permissions.IsAuthenticated],
    )
    def set_as_default(self, request: HttpRequest, pk):
        # SET OTHER BANK ACCOUNTS DEFAULT AS FALSE
        user = request.user
        models.BankAccount.objects.filter(user=user).update(default=False)

        # SET THIS ACCOUNT AS DEFAULT
        obj = self.get_object()
        obj.default = True
        obj.save()

        data = {
            "status": True,
            "message": "Account set as default",
        }

        return Response(
            data=data,
            status=status.HTTP_200_OK,
        )
