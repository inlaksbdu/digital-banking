from django.contrib import admin
from . import models
from unfold.admin import ModelAdmin


@admin.register(models.BankAccount)
class BankAccountAdmin(ModelAdmin):
    list_display = [
        "id",
        "account_number",
        "account_category",
        "user",
        "date_created",
    ]
    search_fields = ["account_number", "account_category", "user__fullname"]
    list_filter = ["account_category"]


@admin.register(models.Transfer)
class TransferAdmin(ModelAdmin):
    list_display = [
        "id",
        "user",
        "transfer_type",
        "source_account",
        "amount",
        "recipient_account",
        "recipient_name",
        "status",
        "reference",
        "t24_reference",
        "date_created",
    ]
    search_fields = ["user", "user__email", "source_account"]
    list_filter = ["status", "transfer_type"]


@admin.register(models.Payment)
class PaymentAdmin(ModelAdmin):
    list_display = [
        "id",
        "user",
        "source_account",
        "amount",
        "payment_type",
        "reference",
        "status",
    ]
    search_fields = ["user", "user__email", "source_account"]
    list_filter = [
        "status",
    ]
    readonly_fields = [
        "uuid",
    ]


@admin.register(models.PaymentBiller)
class PaymentBillerAdmin(ModelAdmin):
    list_display = [
        "id",
        "name",
        "biller_account",
    ]
