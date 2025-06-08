# Create your views here.
from rest_framework.viewsets import ModelViewSet
from . import serializers
from . import models
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import HttpRequest
from .tasks import get_other_banks, get_other_networks, resolve_phone_number
from drf_spectacular.utils import extend_schema
from helpers import exceptions


class SecurityQuestionviewset(ModelViewSet):
    serializer_class = serializers.SecurityQuestionSerializer
    queryset = models.SecurityQuestion.objects.all()
    # permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get"]


# class IDIssueOrgViewset(ModelViewSet):
#     serializer_class = serializers.IDIssueOrgSerializer
#     queryset = models.IDIssueOrg.objects.all()
#     # permission_classes = [rest_permissions.IsAuthenticated]
#     http_method_names = ["get"]


class IDTypeViewset(ModelViewSet):
    serializer_class = serializers.IDTypeSerializer
    queryset = models.IDType.objects.all()
    # permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get"]


class OccupationViewset(ModelViewSet):
    serializer_class = serializers.OccupationSerializer
    queryset = models.Occupation.objects.all()
    # permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get"]


# class AccountTypeViewset(ModelViewSet):
#     serializer_class = serializers.AccountTypeSerializer
#     queryset = models.AccountType.objects.all()
#     # permission_classes = [rest_permissions.IsAuthenticated]
#     http_method_names = ["get"]


class TransactionPurposeViewset(ModelViewSet):
    serializer_class = serializers.TranscationPurposeSerializer
    queryset = models.TransactionPurpose.objects.all()
    # permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get"]


class BranchesViewset(ModelViewSet):
    serializer_class = serializers.BankBranchSerializer
    queryset = models.BankBranch.objects.all()
    # permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get"]

    def get_queryset(self):
        return self.queryset.filter(closed=False)


class ATMsViewset(ModelViewSet):
    serializer_class = serializers.ATMSerializer
    queryset = models.Atm.objects.all()
    # permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get"]

    def get_queryset(self):
        return self.queryset.filter(closed=False)


class AccountCategoryViewset(ModelViewSet):
    serializer_class = serializers.AccountCategorySerializer
    queryset = models.AccountCategory.objects.all()
    http_method_names = ["get"]


class TermsAndConditionsViewset(ModelViewSet):
    serializer_class = serializers.TermsAndConditionSerializer
    queryset = models.TermsAndCondition.objects.all()
    http_method_names = ["get"]


class TelcoDataPlanViewset(ModelViewSet):
    serializer_class = serializers.TelcoDataPlanSerializer
    queryset = models.TelcoDataPlan.objects.all()
    http_method_names = ["get"]
    filterset_fields = ("network",)


@extend_schema(tags=["Other Banks"])
class OtherBankViewset(ModelViewSet):
    serializer_class = serializers.OtherBankSerializer
    queryset = models.OtherBank.objects.all()
    http_method_names = ["get", "post"]
    filterset_fields = ("country",)

    def get_queryset(self):
        # get other bank celery task here
        get_other_banks()
        return self.queryset.filter(active=True)

    @action(
        methods=["post"],
        detail=True,
        url_path="validate-account",
        url_name="validate-account",
        # permission_classes=[rest_permissions.IsAuthenticated],
        serializer_class=serializers.ValidateAccountNumberSerializer,
    )
    def validate_account_number(self, request: HttpRequest, pk):
        """
        this action is used validate a swift number
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bank = self.get_object()
        account_number = serializer.validated_data["account_number"]

        data = {}

        try:
            response = resolve_phone_number(
                phone_number=account_number,
                network_provider_code=bank.code,
            )

            if not response:
                return Response(
                    data={"status": False, "message": "Invalid code provided"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            data = {
                "account_number": response["data"]["account_number"],
                "account_name": response["data"]["account_name"],
            }
        except Exception as e:
            print("==== error", str(e))
            return Response(
                data={"status": False, "message": "Invalid code provided"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            data={
                "status": True,
                "message": "Account Number is resolved successfully",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


class CardReasonViewset(ModelViewSet):
    serializer_class = serializers.CardReasonSerializer
    queryset = models.CardServiceReason.objects.all()
    http_method_names = ["get"]


class SwiftCodeViewset(ModelViewSet):
    serializer_class = serializers.SwiftCodeSerializer
    queryset = models.SwiftCode.objects.all()
    http_method_names = ["get", "post"]

    def get_queryset(self):
        raise exceptions.NotAuthorizedException()

    def perform_create(self, serializer):
        raise exceptions.NotAuthorizedException()

    @action(
        methods=["post"],
        detail=False,
        url_path="validate-code",
        url_name="validate-code",
        # permission_classes=[rest_permissions.IsAuthenticated],
        serializer_class=serializers.ValidateSwiftCodeSerializer,
    )
    def validate_code(self, request: HttpRequest):
        """
        this action is used validate a swift number
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        swift_code = serializer.validated_data["swift_code"]

        try:
            bank_details = models.SwiftCode.objects.get(swift_code=swift_code)
        except models.SwiftCode.DoesNotExist:
            return Response(
                data={"message": "Invalid code provided"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            data=serializers.SwiftCodeSerializer(
                bank_details,
                context=self.get_serializer_context(),
                many=False,
            ).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Network Provider"])
class NetworkProvidersViewset(ModelViewSet):
    serializer_class = serializers.NetworkProviderSerializer
    queryset = models.NetworkProvider.objects.all()
    http_method_names = ["get", "post"]
    filteset_fields = "country"

    def get_queryset(self):
        get_other_networks()
        return super().get_queryset().filter(active=True)

    @action(
        methods=["post"],
        detail=True,
        url_path="validate-number",
        url_name="validate-number",
        # permission_classes=[rest_permissions.IsAuthenticated],
        serializer_class=serializers.ValidatePhoneNumberSeriailzer,
    )
    def validate_phone_number(self, request: HttpRequest, pk):
        """
        this action is used validate a swift number
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        network_provider = self.get_object()
        phone_number = serializer.validated_data["phone_number"]

        data = {}

        try:
            response = resolve_phone_number(
                phone_number=str(phone_number).replace("+", ""),
                network_provider_code=network_provider.code,
            )

            if not response:
                return Response(
                    data={"status": False, "message": "Invalid code provided"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            data = {
                "account_number": response["data"]["account_number"],
                "account_name": response["data"]["account_name"],
            }
        except Exception as e:
            print("==== error", str(e))
            return Response(
                data={"status": False, "message": "Invalid code provided"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            data={
                "status": True,
                "message": "Phone number is resolved successfully",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )
