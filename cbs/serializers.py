from rest_framework import serializers
from . import models


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
