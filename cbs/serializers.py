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
    approver = serializers.SerializerMethodField(read_only=True)
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

    def get_approver(self, obj):
        if obj.approval_by:
            return obj.approval_by.fullname
        return ""

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
            "approver",
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


class ComentsOnApprovalsAndRejectionSerializer(serializers.Serializer):
    comments = serializers.CharField()


class WalletPhoneNumberSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
