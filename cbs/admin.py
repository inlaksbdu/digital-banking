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
