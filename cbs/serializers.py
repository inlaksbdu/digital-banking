from rest_framework import serializers
from . import models
from django.http import HttpRequest
from accounts.serializers import ShortUserInfoSerializer
from helpers import exceptions
from accounts.models import CustomUser


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BankAccount
        fields = (
            "id",
            "account_number",
            "account_name",
            "account_category",
            "currency",
            "default",
            "account_restricted",
        )


class ValidateAccountNumberSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=100)


class TransferSerializer(serializers.ModelSerializer):
    source_account_name = serializers.SerializerMethodField(read_only=True)
    # purpose_of_transcation_name = serializers.SerializerMethodField(read_only=True)
    initiater_info = serializers.SerializerMethodField(read_only=True)
    can_approve = serializers.SerializerMethodField(read_only=True)
    reference = serializers.SerializerMethodField(read_only=True)

    def get_reference(self, obj):
        return obj.t24_reference

    def get_source_account_name(self, obj):
        return {
            "account_name": obj.source_account.account_name,
            "account_number": obj.source_account.account_number,
            "account_category": obj.source_account.account_category,
        }

    # def get_purpose_of_transcation_name(self, obj):
    #     # if obj.purpose_of_transaction is None:
    #     #     return ""
    #     return obj.purpose_of_transaction

    def get_initiater_info(self, obj):
        return obj.user.fullname

    def get_can_approve(self, obj):
        request: HttpRequest = self.context.get("request")
        user = request.user
        if obj.user == user:
            return False
        elif hasattr(user, "corporate_permissions"):
            return True if user.corporate_permissions.permission == "checker" else False
        return False

    class Meta:
        model = models.Transfer
        fields = (
            "id",
            "user",
            "initiater_info",
            "transfer_type",
            "source_account",
            "source_account_name",
            "recipient_account",
            "recipient_name",
            "recipient_bank",
            "recipient_swift_code",
            "recipient_phone_number",
            "recipient_email",
            "recipient_residence_address",
            "recipient_country",
            "recipient_iban_number",
            "charges",
            "amount",
            "currency",
            "purpose_of_transaction",
            "network",
            "status",
            "reference",
            "t24_reference",
            "can_approve",
            "failed_reason",
            "comments",
            "date_created",
        )
        read_only_fields = (
            "date_created",
            "last_updated",
            "status",
            "t24_reference",
            "failed_reason",
            "user",
            "approval_status",
            "approval_by",
            "comments",
        )


class PaymentBillerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PaymentBiller
        fields = (
            "id",
            "name",
            "biller_account",
            "biller_logo",
        )


class PaymentSerializer(serializers.ModelSerializer):
    source_account_name = serializers.SerializerMethodField(read_only=True)
    initiater_info = serializers.SerializerMethodField(read_only=True)

    def get_initiater_info(self, obj):
        return obj.user.fullname

    def get_source_account_name(self, obj):
        return {
            "account_name": obj.source_account.account_name,
            "account_number": obj.source_account.account_number,
            "account_category": obj.source_account.account_category,
        }

    class Meta:
        model = models.Payment
        fields = (
            "id",
            "initiater_info",
            "payment_type",
            "source_account",
            "source_account_name",
            "amount",
            "currency",
            "network_provider",
            "beneficiary",
            "beneficiary_name",
            "purpose_of_transaction",
            "biller",
            "data_plan",
            "status",
            "reference",
            "t24_reference",
            "failed_reason",
            "date_created",
            "last_updated",
        )
        read_only_fields = (
            "date_created",
            "last_updated",
            "status",
            "currency",
            "failed_reason",
        )


class ValidateBillerNumberSerializer(serializers.Serializer):
    biller_number = serializers.CharField(max_length=100)


class AccountStatementSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    email = serializers.EmailField(required=False, allow_null=True)


class BankStatementSerializer(serializers.ModelSerializer):
    source_account_name = serializers.SerializerMethodField(read_only=True)
    source_account_number = serializers.SerializerMethodField(read_only=True)

    def get_source_account_name(self, obj):
        return obj.source_account.account_name

    def get_source_account_number(self, obj):
        return obj.source_account.account_number

    class Meta:
        model = models.BankStatement
        fields = (
            "id",
            "statement_type",
            "source_account",
            "source_account_name",
            "source_account_number",
            "start_date",
            "end_date",
            "recipient_email",
            "pick_up_branch",
            "purpose",
            "status",
            "comments",
        )
        read_only_fields = (
            "status",
            "comments",
        )


class BeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Beneficiary
        fields = (
            "id",
            "user",
            "avatar",
            "source_account",
            "network_provider",
            "biller",
            "beneficiary_type",
            "beneficiary_number",
            "beneficiary_name",
            "benficiary_nick_name",
            "beneficiary_country",
            "beneficiary_swift_code",
            "beneficiary_bank",
            "beneficiary_bank_address",
            "beneficiary_iban_number",
            "beneficiary_email",
            "beneficiary_residence_address",
            "date_created",
        )
        read_only_fields = (
            "date_created",
            "user",
        )


class StandingOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StandingOrder
        fields = (
            "id",
            "user",
            "source_account",
            "standing_order_type",
            "other_bank",
            "network_provider",
            "recipient_account",
            "amount",
            "start_date",
            "end_date",
            "purpose_of_transaction",
            "interval",
            "status",
        )
        read_only_fields = (
            "date_created",
            "user",
            "status",
        )


class ChequeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ChequeRequest
        fields = (
            "id",
            "user",
            "cheque_request_type",
            "source_account",
            "leaves",
            "branch",
            "cheque_numbers",
            "amount",
            "reason",
            "cheque_date",
            "status",
            "date_created",
        )
        read_only_fields = (
            "date_created",
            "user",
            "status",
        )


class LoanCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LoanCategory
        fields = (
            "id",
            "product_id",
            "loan_product_group",
            "amount",
            "interest",
            "description",
            "term",
            "processing_fee",
        )


class LoanFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LaonRequestFile
        fields = ("id", "file")


class LoanRequestSerializer(serializers.ModelSerializer):
    files = LoanFileSerializer(many=True, read_only=True)
    loan_category = LoanCategorySerializer(many=False, read_only=True)

    class Meta:
        model = models.LoanRequest
        fields = (
            "id",
            "user",
            "application_id",
            "source_account",
            "loan_category",
            "amount",
            "duration",
            "comments",
            "status",
            "files",
            "date_created",
        )
        read_only_fields = (
            "user",
            "application_id",
        )


class LoanRequestCreateSerializer(serializers.ModelSerializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=True,
        required=False,
    )

    def to_representation(self, instance):
        return LoanRequestSerializer(instance).data

    class Meta:
        model = models.LoanRequest
        fields = (
            "source_account",
            "loan_category",
            "amount",
            "duration",
            "files",
        )


class AppointmentSeriailzer(serializers.ModelSerializer):
    class Meta:
        model = models.AppointmentBooking
        fields = (
            "id",
            "user",
            "service_type",
            "source_account",
            "source_account_name",
            "amount",
            "currency",
            "cheque_number",
            "name_of_cheque_issuer",
            "issuing_bank",
            "booking_type",
            "fullname",
            "id_number",
            "phone_number",
            "branch",
            "date",
            "time",
            "booking_code",
            "status",
            "date_created",
        )
        read_only_fields = (
            "user",
            "booking_code",
            "application_id",
            "status",
        )


class ExpenseLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ExpenseLimit
        fields = (
            "id",
            "limit_type",
            "user",
            "account",
            "category",
            "limit_amount",
            "amount_spent",
            "status",
            "start_date",
            "end_date",
            "date_created",
        )
        read_only_fields = (
            "user",
            "amount_spent",
            "status",
        )


class CardlessWithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CardlessWithdrawal
        fields = (
            "id",
            "user",
            "source_account",
            "token_type",
            "token",
            "token_redeemed",
            "token_expired",
            "amount",
            "valid_through",
            "withdrawal_party",
            "recipient_phone_number",
            "recipient_name",
            "notes",
            "date_created",
        )
        read_only_fields = (
            "user",
            "token",
            "token_redeemed",
            "token_expired",
        )


class ValidateCardlessWithdrawalTokenSerializer(serializers.Serializer):
    token = serializers.CharField()


class EmailIndemnitySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EmailIndemnity
        fields = (
            "id",
            "user",
            "source_account",
            "primary_email",
            "secondary_email",
            "phone_number",
            "airtime",
            "data",
            "bill_payment",
            "international_transfer",
            "account_to_wallet",
            "other_bank_transfer",
            "same_bank_transfer",
            "own_account_transfer",
            "merchant_payment",
            "date_created",
            "last_updated",
        )
        read_only_fields = (
            "user",
            "date_created",
            "last_updated",
        )


class BillSharingPayeeInfoSerializer(serializers.ModelSerializer):
    user = ShortUserInfoSerializer(read_only=True)

    class Meta:
        model = models.BillSharingPyee
        fields = (
            "user",
            "amount",
            "status",
            "comments",
        )


class BillSharingSerializer(serializers.ModelSerializer):
    initiator = ShortUserInfoSerializer(read_only=True)

    bill_sharing_payees = BillSharingPayeeInfoSerializer(read_only=True, many=True)

    class Meta:
        model = models.BillSharing
        fields = (
            "id",
            "title",
            "initiator",
            "merchant_number",
            "merchant_name",
            "bill_amount",
            "paid_amount",
            "bill_sharing_payees",
            "date_created",
        )
        read_only_fields = (
            "date_created",
            "paid_amount",
        )


class CreateBillSharingPayee(serializers.Serializer):
    user = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=19, decimal_places=2)


class BillSharingCreateSerializer(serializers.ModelSerializer):
    share_with = serializers.ListField(
        child=CreateBillSharingPayee(),
    )

    def to_representation(self, instance):
        return BillSharingSerializer(instance).data

    class Meta:
        model = models.BillSharing
        fields = (
            "title",
            "merchant_number",
            "merchant_name",
            "bill_amount",
            "share_with",
        )

    def validate(self, attrs):
        share_with = attrs.get("share_with")

        if len(share_with) < 2:
            raise exceptions.GeneralException(
                detail="Bill sharing must have at least 2 payees"
            )

        total_payee_amount = 0
        for user in share_with:
            user_id = user.get("user")
            total_payee_amount += user.get("amount")
            if not CustomUser.objects.filter(id=user_id).exists():
                raise exceptions.GeneralException(
                    detail=f"User with id {user_id} does not exist"
                )

        if total_payee_amount != attrs.get("bill_amount"):
            raise exceptions.GeneralException(
                detail="Total amount of payees must be equal to the bill amount"
            )
        return super().validate(attrs)


class BillSharingShortInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BillSharing
        fields = (
            "id",
            "title",
            "merchant_number",
            "merchant_name",
            "bill_amount",
            "date_created",
        )


class BillSharingPayeeSerializer(serializers.ModelSerializer):
    bill_sharing = BillSharingShortInfoSerializer(read_only=True)

    class Meta:
        model = models.BillSharingPyee
        fields = (
            "id",
            "bill_sharing",
            "user",
            "amount",
            "status",
            "date_created",
        )


class MakeBillSharingPaymentAccountSerializer(serializers.Serializer):
    account_number = serializers.CharField()

    def validate_account_number(self, account_number):
        if not models.BankAccount.objects.filter(
            account_number=account_number,
        ).exists():
            raise exceptions.AccountNumberNotExist()
        return models.BankAccount.objects.filter(
            account_number=account_number,
        ).first()


class RejectBillSharingRequestSerializer(serializers.Serializer):
    reason = serializers.CharField()


class CardSerializer(serializers.ModelSerializer):
    card_holder = serializers.SerializerMethodField(read_only=True)

    def get_card_holder(self, obj):
        return obj.user.fullname

    class Meta:
        model = models.Card
        fields = (
            "id",
            "user",
            "card_holder",
            "card_number",
            "card_scheme",
            "card_type",
            "card_form",
            "virtual_card_type",
            "card_status",
            "date_created",
        )
        read_only_fields = (
            "user",
            "date_created",
        )


class CardRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CardRequest
        fields = (
            "id",
            "user",
            "source_account",
            "card_type",
            "delivery_method",
            "pick_up_branch",
            "comments",
            "status",
            "date_created",
        )
        read_only_fields = (
            "user",
            "status",
            "comments",
            "date_created",
        )


class CardManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CardManagement
        fields = (
            "id",
            "user",
            "management_type",
            "card",
            "reason",
            "through_date",
            "delivery_method",
            "pick_up_branch",
            "comments",
            "date_created",
        )
        read_only_fields = (
            "user",
            "status",
            "comments",
            "date_created",
        )


class TravelNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TravelNotice
        fields = (
            "id",
            "user",
            "departure_date",
            "return_date",
            "source_account",
            "card",
            "alternative_phone",
            "date_created",
        )
        read_only_fields = (
            "user",
            "date_created",
        )


class CreateVirtualCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Card
        fields = (
            "card_scheme",
            "currency",
            "virtual_card_type",
        )
