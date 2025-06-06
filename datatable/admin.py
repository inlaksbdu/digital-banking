from django.contrib import admin
from . import models
from unfold.admin import ModelAdmin


from import_export.admin import ImportExportModelAdmin


class ImportExportAdmin(ImportExportModelAdmin, ModelAdmin): ...


@admin.register(models.SecurityQuestion)
class SecurityQuestionAdmin(ImportExportAdmin):
    list_display = [
        "id",
        "question",
    ]
    search_fields = ["question"]


@admin.register(models.IDType)
class IDTypeAdmin(ImportExportAdmin):
    list_display = [
        "id",
        "name",
    ]
    search_fields = ["name"]


@admin.register(models.Atm)
class AtmAdmin(ImportExportAdmin):
    list_display = [
        "id",
        "address",
        "langtitude_cordinates",
        "longitude_cordinates",
        "closed",
    ]
    search_fields = ["address"]


@admin.register(models.Occupation)
class OccupationAdmin(ImportExportAdmin):
    list_display = [
        "id",
        "name",
    ]
    search_fields = ["name"]


@admin.register(models.AccountCategory)
class AccountCategoryAdmin(ImportExportAdmin):
    list_display = [
        "id",
        "account_type",
        "name",
        "category",
    ]
    search_fields = ["name", "category"]
    list_filter = ["account_type"]


@admin.register(models.TransactionPurpose)
class TransactionPurposeAdmin(ImportExportAdmin):
    list_display = [
        "id",
        "name",
    ]
    search_fields = ["name"]


@admin.register(models.BankBranch)
class BankBranchModel(ImportExportAdmin):
    list_display = [
        "id",
        "name",
        "country",
        "langtitude_cordinates",
        "longitude_cordinates",
    ]
    search_fields = ["name"]


@admin.register(models.NotificationMessage)
class NotificationMessageAdmin(ImportExportAdmin):
    list_display = (
        "id",
        "message_type",
        "title",
        "message",
    )


@admin.register(models.OtherBank)
class OtherBankAdmin(ImportExportAdmin):
    list_display = [
        "id",
        "name",
        "date_created",
        "last_udpated",
    ]


@admin.register(models.FileManager)
class FileManagerAdmin(ImportExportAdmin):
    list_display = [
        "id",
        "name",
        "file",
        "date_created",
    ]


admin.site.register(models.TermsAndCondition)


@admin.register(models.CardServiceReason)
class CardServiceReason(ImportExportAdmin):
    list_display = [
        "id",
        "reason",
        "date_created",
    ]


@admin.register(models.SwiftCode)
class SwiftCodeAdmin(ImportExportAdmin):
    list_display = [
        "id",
        "swift_code",
        "bank_name",
        "bank_address",
        "date_created",
    ]
