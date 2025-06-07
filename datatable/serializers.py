from rest_framework import serializers
from . import models

# from django.utils.translation import gettext_lazy as _


class SecurityQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SecurityQuestion
        fields = (
            "id",
            "question",
        )


# class IDIssueOrgSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.IDIssueOrg
#         fields = (
#             "id",
#             "name",
#         )


class IDTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.IDType
        fields = (
            "id",
            "name",
        )


class OccupationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Occupation
        fields = (
            "id",
            "name",
        )


class AccountCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AccountCategory
        fields = (
            "id",
            "account_type",
            "name",
            "category",
        )


class TranscationPurposeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TransactionPurpose
        fields = (
            "id",
            "name",
        )


class BankBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BankBranch
        fields = (
            "id",
            "name",
            "country",
            "langtitude_cordinates",
            "longitude_cordinates",
        )


class ATMSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Atm
        fields = (
            "id",
            "country",
            "langtitude_cordinates",
            "longitude_cordinates",
            "address",
        )


class TermsAndConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TermsAndCondition
        fields = (
            "mobile_terms_and_conditions",
            "account_opening_terms_and_conditions",
        )


class OtherBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OtherBank
        fields = (
            "id",
            "name",
        )


class CardReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CardServiceReason
        fields = ("id", "reason")


class SwiftCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SwiftCode
        fields = (
            "id",
            "swift_code",
            "bank_name",
            "bank_address",
        )


class ValidateSwiftCodeSerializer(serializers.Serializer):
    swift_code = serializers.CharField()


class NetworkProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NetworkProvider
        fields = (
            "id",
            "name",
            "active",
        )
