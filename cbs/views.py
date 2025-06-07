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
from rest_framework import filters
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as djangofilters
import json
import requests
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from .utils import generate_pdf_from_html, encrypt_pdf
import os

# Create your views here.


base_url = settings.T24_BASE_URL


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

    @action(
        methods=["post"],
        detail=True,
        url_path="mini-statement",
        url_name="mini-statement",
        permission_classes=[rest_permissions.IsAuthenticated],
        serializer_class=serializers.AccountStatementSerializer,
    )
    def mini_statement(self, request: HttpRequest, pk):
        bank_account = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        start_date = data.get("start_date")
        end_date = data.get("end_date")

        queryset = []

        # Format first and last date
        start_date = str(start_date).replace("-", "")
        end_date = str(end_date).replace("-", "")

        # Make a request to get withdrawal and deposit objects
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}

        params = {
            "accountNo": bank_account.account_number,
            "startDate": start_date,
            "endDate": end_date,
        }

        account_url = f"{base_url}/party/getAccountStatement"
        response = requests.get(account_url, headers=headers, params=params)
        if response.status_code != 200:
            raise exceptions.GeneralException(
                detail="Failed to retrieve account statement",
            )
        alert_response = json.loads(response.text)
        body = alert_response.get("body", [])
        queryset.extend(body)
        data = {
            "status": True,
            "message": "retrieved account statment",
            "data": queryset,
        }

        return Response(
            data=data,
            status=status.HTTP_200_OK,
        )

    @action(
        methods=["post"],
        detail=True,
        url_path="e-statement",
        url_name="e-statement",
        permission_classes=[rest_permissions.IsAuthenticated],
        serializer_class=serializers.AccountStatementSerializer,
    )
    def e_statement(self, request: HttpRequest, pk):
        bank_account = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        start_date = data.get("start_date")
        end_date = data.get("end_date")
        recipient_email = data.get("email")

        if not recipient_email:
            recipient_email = request.user.email

        # Format first and last date
        start_date = str(start_date).replace("-", "")
        end_date = str(end_date).replace("-", "")

        # Get the statement from T24
        statement = T24Requests.get_account_statements(
            account_number=bank_account.account_number,
            start_date=start_date,
            end_date=end_date,
        )

        # Generate context for the email template
        context = {
            "bank_name": "Family Bank",
            "logo": "https://mamicha.com/wp-content/uploads/2019/05/Mamicha-Logos-05.png",
            "customer_name": str(request.user.fullname).upper(),
            "account_number": bank_account.account_number,
            "statements": statement,
            "generated_date": timezone.now(),
        }
        template_path = os.path.join(
            settings.BASE_DIR, "templates", "bank_statement.html"
        )
        html_message = render_to_string(template_path, context)
        pdf_data = generate_pdf_from_html(html_message)
        password = str(bank_account.account_number)[-6:]
        encrypted_pdf_path = encrypt_pdf(pdf_data, password)

        # Create the email subject
        subject = "Account Statement from {} to {}".format(start_date, end_date)
        body = f"Your bank statement from {start_date} to {end_date} is attached. The PDF is password protected. \nUse the last 6 characters of your bank account,for example 200000XXXXXX"
        # Create the email message
        from_email = settings.DEFAULT_FROM_EMAIL
        email = EmailMessage(
            subject,
            body,
            from_email,
            [recipient_email],
        )

        # Attach the encrypted PDF to the email
        with open(encrypted_pdf_path, "rb") as f:
            email.attach("bank_statement.pdf", f.read(), "application/pdf")

        # Send the email
        email.send()

        return Response(
            data=data,
            status=status.HTTP_200_OK,
        )


class TransferFilter(djangofilters.FilterSet):
    start_date = djangofilters.DateFilter(
        field_name="date_created", lookup_expr="gte", required=False
    )
    end_date = djangofilters.DateFilter(
        field_name="date_created", lookup_expr="lte", required=False
    )

    class Meta:
        model = models.Transfer
        fields = (
            "source_account",
            "transfer_type",
            "status",
        )

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        # Handle filtering based on the presence of start_date and end_date
        start_date = self.data.get("start_date")
        end_date = self.data.get("end_date")

        if start_date and end_date:
            queryset = queryset.filter(
                date_created__gte=start_date, date_created__lte=end_date
            )
        elif start_date:
            queryset = queryset.filter(date_created__gte=start_date)
        elif end_date:
            queryset = queryset.filter(date_created__lte=end_date)
        return queryset


@extend_schema(tags=["Transfers"])
class TransferViewset(ModelViewSet):
    queryset = models.Transfer.objects.all()
    serializer_class = serializers.TransferSerializer
    permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch"]
    filterset_fields = ("transfer_type", "status", "approval_status")
    filter_backends = (filters.SearchFilter, DjangoFilterBackend)
    filterset_class = TransferFilter

    def perform_create(self, serializer):
        channel = self.request.META.get("HTTP_CHANNEL", "Other")
        instance = serializer.save(user=self.request.user, channel=channel)

        # create transaction history
        models.TransactionHistory.objects.create(
            user=self.request.user,
            history_id=instance.id,
            history_model=instance,
            credit_debit_status=models.TransactionHistory.CreditDebitStatus.DEBIT,
            history_type=models.TransactionHistory.TransactionType.TRANSFER,
            date_created=timezone.now(),
        )
        return serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)

        # if (
        #     instance.transfer_type
        #     in [
        #         "Other Bank Transfer",
        #         "International Transfer",
        #         "Account to Wallet",
        #     ]
        #     or instance.approval_status == models.Transfer.ApprovalStatus.PENDING
        # ):
        #     headers = self.get_success_headers(serializer.data)
        #     instance.save()
        #     return Response(
        #         {
        #             "status": "pending",
        #             "failed_reason": "",
        #             "model": serializers.TransferSerializer(
        #                 instance,
        #                 context=self.get_serializer_context(),
        #             ).data,
        #         },
        #         status=status.HTTP_201_CREATED,
        #         headers=headers,
        #     )

        try:
            if instance.transfer_type in [
                "Other Bank Transfer",
                "International Transfer",
                "Account to Wallet",
            ]:
                recipient_account = settings.UNITEL_GL_ACCOUNT
            else:
                recipient_account = instance.recipient_account

            payload = {
                "debitAccountId": str(instance.source_account.account_number),
                "creditAccountId": str(recipient_account),
                "debitAmount": str(instance.amount),
                # "debitValueDate": "",
                "debitCurrency": instance.source_account.currency,
                "transactionType": "AC",
                "paymentDetails": instance.purpose_of_transaction,
                "channel": "",
            }

            url = f"{base_url}/party/creategtiFundsTransfer"
            headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
            response = requests.post(
                url, headers=headers, json=json.dumps({"body": payload})
            )
            data = json.loads(response.text)

            req_status = data["header"]["status"]
            errorcode = ""

            if response.status_code != 200:
                if "error" in data:
                    errorData = data["error"]
                    error_detail = errorData["errorDetails"]
                    errorcode = ""
                    for error in error_detail:
                        errorcode += f"{error['message']},  "

                elif "override" in data:
                    errorData = data["override"]
                    error_detail = errorData["overrideDetails"]
                    errorcode = ""
                    for error in error_detail:
                        errorcode += f"{error['description']},  "
                else:
                    errorcode = data
            logger.info(" [FUNDS TRANSFER]: ", response.text)
            instance.failed_reason = errorcode
            instance.t24_reference = (
                data["header"]["id"] if "id" in data["header"] else ""
            )
            instance.status = req_status.title()
            instance.save()

            # create a credit notificaiton to the recipeient account
            if req_status == "success":
                try:
                    recipient_account = models.BankAccount.objects.filter(
                        account_number=instance.recipient_account
                    ).first()

                    if recipient_account:
                        # account_number = recipient_account.first()
                        user_account = recipient_account.user
                        models.TransactionHistory.objects.create(
                            user=user_account,
                            history_id=instance.id,
                            history_model=instance,
                            credit_debit_status=models.TransactionHistory.CreditDebitStatus.CREDIT,
                            history_type=models.TransactionHistory.TransactionType.TRANSFER,
                            date_created=timezone.now(),
                        )
                except Exception:
                    pass

            # Customize your response here
            return Response(
                {
                    "status": req_status,
                    "failed_reason": instance.failed_reason,
                    "model": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            print("===== T24 REQUEST ERROR: ", str(e))

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        orginal_object = self.get_object()
        instance = serializer.save()

        differences = ""

        # Get the model's fields
        for field in orginal_object._meta.fields:
            field_name = field.name
            value1 = getattr(orginal_object, field_name)
            value2 = getattr(instance, field_name)

            if value1 != value2 and field_name != "last_updated":
                differences += f"\n- changed {field_name.replace('_', ' ').title()} from {value1} to {value2}"

        models.TransferEditHistory.objects.create(
            user=self.request.user,
            transfer=instance,
            edit_trail=differences.strip(),
        )

        return super().perform_update(serializer)

    def get_queryset(self):
        return self.queryset.filter(
            # bulk_transfer__isnull=True,
            user=self.request.user
        )


@extend_schema(tags=["Payments"])
class PaymentBiller(ModelViewSet):
    queryset = models.PaymentBiller.objects.all()
    serializer_class = serializers.PaymentBillerSerializer
    permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get", "post"]

    @action(
        methods=["post"],
        detail=True,
        url_path="validate-number",
        url_name="validate-number",
        permission_classes=[rest_permissions.IsAuthenticated],
        serializer_class=serializers.ValidateBillerNumberSerializer,
    )
    def validate_number(self, request: HttpRequest, pk):
        # SET OTHER BANK ACCOUNTS DEFAULT AS FALSE
        # biller = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # validated_data = serializer.validated_data

        # PERFORM CHECK HERE BASED ON THE BILLER
        import requests

        base_url = "https://randomuser.me/api/"
        response = requests.get(base_url)
        if response.status_code != 200:
            return Response(
                data={"status": False, "message": "Something went wrong"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        json_response = json.loads(response.text)
        customer_name = "{} {}".format(
            json_response["results"][0]["name"]["first"],
            json_response["results"][0]["name"]["last"],
        )

        data = {
            "status": True,
            "message": "Biller Number succesfully validated",
            "customer_name": customer_name,
        }

        return Response(
            data=data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Payments"])
class PaymentViewset(ModelViewSet):
    queryset = models.Payment.objects.all()
    serializer_class = serializers.PaymentSerializer
    permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get", "post"]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        channel = self.request.META.get("HTTP_CHANNEL", "Other")
        instance = serializer.save(user=self.request.user, channel=channel)

        # create transaction history
        models.TransactionHistory.objects.create(
            user=self.request.user,
            history_id=instance.id,
            history_model=instance,
            credit_debit_status=models.TransactionHistory.CreditDebitStatus.DEBIT,
            history_type=models.TransactionHistory.TransactionType.PAYMENT,
            date_created=timezone.now(),
        )
        return serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)

        try:
            if instance.payment_type in ["Airtime", "Data"]:
                gl_account = settings.UNITEL_GL_ACCOUNT
            else:
                payment_biller = instance.biller
                gl_account = payment_biller.biller_account
            payload = {
                "debitAccountId": str(instance.source_account.account_number),
                "creditAccountId": str(gl_account),
                "debitAmount": str(instance.amount),
                "debitCurrency": instance.source_account.currency,
                "transactionType": "AC",
                "paymentDetails": instance.purpose_of_transaction,
                "channel": "",
            }

            url = f"{base_url}/party/creategtiFundsTransfer"
            headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
            response = requests.post(
                url, headers=headers, json=json.dumps({"body": payload})
            )
            data = json.loads(response.text)

            req_status = data["header"]["status"]
            errorcode = ""

            if response.status_code != 200:
                if "error" in data:
                    errorData = data["error"]
                    error_detail = errorData["errorDetails"]
                    errorcode = ""
                    for error in error_detail:
                        errorcode += f"{error['message']},  "

                elif "override" in data:
                    errorData = data["override"]
                    error_detail = errorData["overrideDetails"]
                    errorcode = ""
                    for error in error_detail:
                        errorcode += f"{error['description']},  "
                else:
                    errorcode = data
            logger.info(" [FUNDS TRANSFER]: ", response.text)
            instance.failed_reason = errorcode
            instance.t24_reference = (
                data["header"]["id"] if "id" in data["header"] else ""
            )
            instance.status = req_status.title()
            instance.save()
            # Customize your response here
            return Response(
                {
                    "status": req_status,
                    "failed_reason": instance.failed_reason,
                    "model": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            instance.failed_reason = str(e)
            instance.save()
            print("===== T24 REQUEST ERROR: ", str(e))

        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Official Bank Statement"])
class BankStatementViewset(ModelViewSet):
    queryset = models.BankStatement.objects.all()
    serializer_class = serializers.BankStatementSerializer
    permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get", "post"]

    def perform_create(self, serializer):
        channel = self.request.META.get("HTTP_CHANNEL", "Other")
        return serializer.save(user=self.request.user, channel=channel)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


@extend_schema(tags=["Beneficiary"])
class BeneficiaryViewset(ModelViewSet):
    queryset = models.Beneficiary.objects.all()
    serializer_class = serializers.BeneficiarySerializer
    permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get", "post"]
    filterset_fields = ["beneficiary_type"]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)


@extend_schema(tags=["Standing Order"])
class StandingOrderViewset(ModelViewSet):
    queryset = models.StandingOrder.objects.all()
    serializer_class = serializers.StandingOrderSerializer
    permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get", "post"]
    filterset_fields = ["standing_order_type"]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)


@extend_schema(tags=["Cheque Requests"])
class ChequeRequestViewset(ModelViewSet):
    queryset = models.ChequeRequest.objects.all()
    serializer_class = serializers.ChequeRequestSerializer
    permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get", "post"]
    filterset_fields = ["cheque_request_type"]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)


@extend_schema(tags=["Loans"])
class LoanCategoryViewset(ModelViewSet):
    queryset = models.LoanCategory.objects.all()
    serializer_class = serializers.LoanCategorySerializer
    permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get"]
    # filterset_fields = ["loan_product_group"]

    def get_queryset(self):
        celery_tasks.get_loan_products.delay()
        queryset = super().get_queryset()

        # get query params
        params = self.request.query_params
        loan_product_group = params.get("loan_product_group", "")

        if loan_product_group == "CORPORATE":
            return queryset.filter(
                loan_product_group__in=[
                    "CORPORATE",
                    "SME",
                ]
            )
        elif loan_product_group == "RETAIL":
            return queryset.filter(loan_product_group="RETAIL")

        return queryset


@extend_schema(tags=["Loans"])
class LoanRequestViewset(ModelViewSet):
    queryset = models.LoanRequest.objects.all()
    serializer_class = serializers.LoanRequestSerializer
    permission_classes = [rest_permissions.IsAuthenticated]
    http_method_names = ["get", "post"]

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return serializers.LoanRequestCreateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        files = []

        if "files" in data:
            files = serializer.validated_data.pop("files")

        instnace = serializer.save(user=self.request.user)

        # save file in the database
        for file in files:
            models.LaonRequestFile.objects.create(
                loan_request=instnace,
                file=file,
            )

    @action(
        methods=["get"],
        detail=False,
        url_path="applied-loan",
        url_name="applied-loan",
        permission_classes=[rest_permissions.IsAuthenticated],
        serializer_class=None,
    )
    def applied_loans(self, request: HttpRequest):
        # make a request through to t24
        user = request.user
        if (
            not hasattr(user, "customer_profile")
            and not user.customer_profile.t24_customer_id
        ):
            raise exceptions.GeneralException(detail="Sorry, you have no applied loans")
        body = []
        customer_number = user.customer_profile.t24_customer_id
        url = f"/party/getLoanDetails/?customerId={customer_number}"
        response = T24Requests.get_loans(url=url)

        if response:
            body = response

        return Response(
            data=body,
            status=status.HTTP_200_OK,
        )

    @action(
        methods=["get"],
        detail=False,
        url_path="current-loans",
        url_name="current-loans",
        permission_classes=[rest_permissions.IsAuthenticated],
        serializer_class=None,
    )
    def current_loans(self, request: HttpRequest):
        # make a request through to t24
        user = request.user
        if (
            not hasattr(user, "customer_profile")
            and not user.customer_profile.t24_customer_id
        ):
            raise exceptions.GeneralException(detail="Sorry, you have no current loans")
        body = []
        customer_number = user.customer_profile.t24_customer_id
        url = f"/party/getFindLoanDetails/?owner={customer_number}"
        response = T24Requests.get_loans(url=url)

        if response:
            body = response

        return Response(
            data=body,
            status=status.HTTP_200_OK,
        )
