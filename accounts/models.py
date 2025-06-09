from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
import uuid
from django.contrib.auth.hashers import make_password, check_password
from datatable.models import SecurityQuestion


class CustomUser(AbstractUser):
    fullname = models.CharField(max_length=100, null=True, blank=True)
    # AUTHENTICATION
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    phone_number = PhoneNumberField(blank=True, null=True, unique=True)
    secure_pin = models.CharField(max_length=240, null=True, blank=True)

    # MOBILE APP INFO
    password_set = models.BooleanField(default=False)

    # META DATA
    fcm_app_token = models.CharField(max_length=240, null=True, blank=True)
    last_login_ip = models.CharField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    uuid = models.UUIDField(unique=True, blank=True, null=True, default=uuid.uuid4)
    deactivated_account = models.BooleanField(default=False)

    def __str__(self):
        return self.fullname or self.username

    def save(self, *args, **kwargs):
        if not self.fullname:
            self.fullname = self.get_full_name()
        return super().save(*args, **kwargs)


class CustomerProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = "Male"
        FEMALE = "Female"

    user_account = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        null=True,
        blank=True,
    )
    nationality = models.CharField(max_length=200)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    date_of_birth = models.DateField(null=True, blank=True)

    # ID INFO
    id_number = models.CharField(max_length=240, null=True, blank=True)
    id_type = models.CharField(max_length=240, null=True, blank=True)
    id_front = models.ImageField(upload_to="id_front/", null=True, blank=True)
    id_back = models.ImageField(upload_to="id_back/", null=True, blank=True)
    place_of_issue = models.CharField(max_length=240, null=True, blank=True)
    date_of_issuance = models.DateField(null=True, blank=True)
    date_of_expiry = models.DateField(null=True, blank=True)

    # META DATA
    t24_customer_id = models.CharField(max_length=240, null=True, blank=True)
    mnemonic = models.CharField(max_length=240, null=True, blank=True)
    uuid = models.UUIDField(unique=True, blank=True, null=True, default=uuid.uuid4)
    extra_data = models.TextField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.user_account)

    class Meta:
        ordering = ("user_account",)


class UserSecurityQuestion(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="security_questions",
    )
    question = models.ForeignKey(SecurityQuestion, on_delete=models.CASCADE)
    answer_hash = models.CharField(max_length=128)  # store hashed answer

    # META DATA
    uuid = models.UUIDField(unique=True, blank=True, null=True, default=uuid.uuid4)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "question")  # Prevent duplicate questions per user

    def set_answer(self, raw_answer):
        self.answer_hash = make_password(raw_answer)

    def check_answer(self, raw_answer):
        return check_password(raw_answer, self.answer_hash)


class Staff(models.Model):
    user_account = models.OneToOneField(
        CustomUser,
        related_name="staff_account",
        on_delete=models.CASCADE,
    )

    # META DATA
    uuid = models.UUIDField(unique=True, blank=True, null=True, default=uuid.uuid4)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("user_account",)

    def __str__(self):
        return str(self.user_account)


class ActivityLog(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="activity_logs",
    )
    action = models.TextField()

    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.user)

    class Meta:
        ordering = ("-date_created",)


class AccessGuardian(models.Model):
    class LogTypes(models.TextChoices):
        LOGIN_ATTEMPT = "Login Attempt"
        INVALID_PIN = "Invalid Pin"
        SECURITY_QUESTION = "Security Question"
        CHANGE_PIN = "Change PIN"
        FORGOT_PIN = "Forgot PIN"
        PASSWORD_RESET = "Password Reset"
        PASSWORD_CHANGE = "Change Password"

    log_type = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=100, null=True, blank=True)
    is_customer = models.BooleanField(default=False)
    ip_address = models.CharField(max_length=40, null=True, blank=True)
    device = models.CharField(max_length=20, null=True, blank=True)
    browser = models.CharField(max_length=20, null=True, blank=True)
    browser_version = models.CharField(max_length=20, null=True, blank=True)
    os = models.CharField(max_length=20, null=True, blank=True)
    os_version = models.CharField(max_length=20, null=True, blank=True)

    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return "{}:{}".format(self.phone_number, self.device)

    class Meta:
        ordering = ("-date_created",)

    # def save(self, *args, **kwargs):
    #     if self.phone_number:
    #         customer = CustomUser.objects.filter(phone_number=self.phone_number).first()
    #         if customer:
    #             self.is_customer = True

    #     return super().save(*args, **kwargs)
