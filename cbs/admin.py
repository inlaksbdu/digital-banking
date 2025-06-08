from django.contrib import admin
from . import models
from unfold.admin import ModelAdmin, TabularInline


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


@admin.register(models.LoanCategory)
class LoanCategoryAdmin(ModelAdmin):
    list_display = (
        "id",
        "product_id",
        "amount",
        "interest",
        "description",
        "term",
        "processing_fee",
        "loan_product_group",
    )
    readonly_fields = (
        "product_id",
        "amount",
        "interest",
        "description",
        "term",
        "processing_fee",
        "loan_product_group",
    )


@admin.register(models.LoanRequest)
class LoanRequestAdmin(ModelAdmin):
    list_display = (
        "id",
        "user",
        "loan_category",
        "amount",
        "duration",
        "status",
        "date_created",
    )
    list_filter = ["status"]


@admin.register(models.AppointmentBooking)
class AppointmentBookingAdmin(ModelAdmin):
    list_display = (
        "id",
        "user",
        "service_type",
        "booking_type",
        "status",
        "branch",
        "date_created",
    )
    list_filter = ["status", "booking_type", "service_type"]


@admin.register(models.ExpenseLimit)
class ExpenseLimitAdmin(ModelAdmin):
    list_display = (
        "id",
        "user",
        "account",
        "limit_type",
        "limit_amount",
        "amount_spent",
        "start_date",
        "end_date",
        "status",
    )
    list_filter = ["limit_type", "status"]


@admin.register(models.CardlessWithdrawal)
class CardlessWithdrawalAdmin(ModelAdmin):
    list_display = (
        "id",
        "user",
        "source_account",
        "amount",
        "withdrawal_party",
        "token_type",
        "valid_through",
        "token_redeemed",
        "token_expired",
        "date_created",
    )
    list_filter = ["withdrawal_party", "token_type", "token_redeemed", "token_expired"]


@admin.register(models.EmailIndemnity)
class EmailIndemnityAdmin(ModelAdmin):
    list_display = (
        "id",
        "user",
        "source_account",
        "primary_email",
        "phone_number",
        "date_created",
    )


class BillSharingPayeeInline(TabularInline):
    model = models.BillSharingPyee
    fields = ["user", "amount", "status", "comments"]
    extra = 0


@admin.register(models.BillSharing)
class BillSharingAdmin(ModelAdmin):
    list_display = (
        "id",
        "title",
        "initiator",
        "merchant_number",
        "merchant_name",
        "bill_amount",
        "paid_amount",
        "date_created",
    )
    inlines = [BillSharingPayeeInline]
