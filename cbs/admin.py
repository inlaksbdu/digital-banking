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


@admin.register(models.Beneficiary)
class BeneficiarAdmin(ModelAdmin):
    list_display = [
        "id",
        "beneficiary_type",
        "user",
        "source_account",
        "beneficiary_number",
        "beneficiary_name",
        "benficiary_nick_name",
    ]
    list_filter = ["beneficiary_type", "biller", "network_provider"]
    search_fields = [
        "beneficiary_type",
        "user",
        "source_account",
        "beneficiary_number",
        "beneficiary_name",
        "benficiary_nick_name",
    ]


@admin.register(models.StandingOrder)
class StandingOrderAdmin(ModelAdmin):
    list_display = [
        "id",
        "user",
        "source_account",
        "standing_order_type",
        "amount",
        "start_date",
        "end_date",
        "status",
        "cbs_status",
    ]

    list_filter = ["standing_order_type", "network_provider"]
    search_fields = [
        "standing_order_type",
        "user",
        "source_account",
        "beneficiary_number",
        "beneficiary_name",
        "benficiary_nick_name",
    ]
