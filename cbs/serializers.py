from rest_framework import serializers
from . import models
from django.http import HttpRequest


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
