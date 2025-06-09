from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from . import models
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm


@admin.register(models.CustomUser)
class UserAdmin(UserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    readonly_fields = ("secure_pin", "uuid", "fcm_app_token")
    list_filter = [
        "password_set",
    ]
    list_display = [
        "id",
        "fullname",
        "email",
        "phone_number",
        "date_joined",
        "last_login",
    ]
    fieldsets = [
        *UserAdmin.fieldsets,
    ]
    fieldsets.insert(
        2,
        (
            None,
            {
                "fields": (
                    "fullname",
                    "phone_number",
                    "secure_pin",
                    "password_set",
                    "fcm_app_token",
                    "last_login_ip",
                    "last_seen",
                    "uuid",
                    "deactivated_account",
                ),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        print("== user password: ", obj.password)
        if is_new:
            # You can customize the subject and message
            # send_mail(
            #     subject="Welcome to the platform!",
            #     message=f"Hi {obj.fullname}, your account has been successfully created.",
            #     from_email="no-reply@yourdomain.com",
            #     recipient_list=[obj.email],
            #     fail_silently=False,
            # )
            pass


@admin.register(models.CustomerProfile)
class CustomerProfileAdmin(ModelAdmin):
    list_display = [
        "id",
        "user_account",
        "t24_customer_id",
        "mnemonic",
        "gender",
        "date_of_birth",
        "date_created",
    ]
    search_fields = ["user_account", "t24_customer_id", "mnemonic"]
    # readonly_fields = [
    #     "user_account",
    #     "t24_customer_id",
    #     "mnemonic",
    #     "uuid",
    #     "extra_data",
    # ]


@admin.register(models.UserSecurityQuestion)
class UserSecurityQuestionAdmin(ModelAdmin):
    list_display = [
        "id",
        "user",
        "question",
    ]
    search_fields = ["user", "question"]
    readonly_fields = ["user", "answer_hash", "question", "uuid"]


@admin.register(models.ActivityLog)
class ActivityLogAdmin(ModelAdmin):
    list_display = [
        "id",
        "user",
        "action",
        "date_created",
    ]
    readonly_fields = [
        "user",
        "action",
        "date_created",
    ]
