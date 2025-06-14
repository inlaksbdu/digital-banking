from django.db import models
from django.db.models import FloatField
from django.db.models.functions import Cast, Sin, Cos, Sqrt, Radians, ATan2
from ckeditor.fields import RichTextField
import uuid

# from geopy.geocoders import GoogleV3

# Create your models here.


class CBSStatus(models.TextChoices):
    PENDING = "Pending"
    REQUESTED = "Requested"


class SecurityQuestion(models.Model):
    question = models.CharField(max_length=500)

    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.question)


class IDType(models.Model):
    name = models.CharField(max_length=240)

    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        ordering = ("name",)


class Occupation(models.Model):
    name = models.CharField(max_length=240)

    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        ordering = ("date_created",)


class AccountCategory(models.Model):
    class AccountType(models.TextChoices):
        CURRENT_LOCAL = "Current Local"
        CURRENT_JOINT = "Current Joint"
        CURRENT_COM = "Current Com"
        CURRENT_FCA = "Current FCA"
        CURRENT_FEA = "Current FEA"
        SAVINGS_LOCAL = "Savings Local"

    account_type = models.CharField(choices=AccountType.choices, max_length=240)
    name = models.CharField(max_length=240)
    category = models.CharField(max_length=20)

    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        ordering = ("name",)


class TransactionPurpose(models.Model):
    name = models.CharField(max_length=240)

    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        ordering = ("name",)


class BankBranch(models.Model):
    name = models.CharField(max_length=240)
    country = models.CharField(max_length=240, default="São Tomé and Príncipe")
    langtitude_cordinates = models.CharField(max_length=240, null=True, blank=True)
    longitude_cordinates = models.CharField(max_length=240, null=True, blank=True)
    address = models.CharField(max_length=400, null=True, blank=True)
    closed = models.BooleanField(default=False)
    secrets = models.UUIDField(default=uuid.uuid4, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs):
        # geolocator = GoogleV3()
        # location = geolocator.reverse("52.509669, 13.376294")
        # self.address = location.address
        super().save(*args, **kwargs)

    @classmethod
    def find_closest(cls, latitude: float, longitude: float) -> list[dict]:
        R = 6371
        lat1_rad = Radians(latitude)
        lon1_rad = Radians(longitude)
        lat2_rad = Radians(Cast("langtitude_cordinates", FloatField()))
        lon2_rad = Radians(Cast("longitude_cordinates", FloatField()))

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = Sin(dlat / 2) ** 2 + Cos(lat1_rad) * Cos(lat2_rad) * Sin(dlon / 2) ** 2
        c = 2 * ATan2(Sqrt(a), Sqrt(1 - a))
        distance = R * c

        closest_branches = list(
            cls.objects.annotate(distance=distance)
            .exclude(closed=True)
            .order_by("distance")
            .values("id", "name", "address", "distance")[:3]
        )

        if not closest_branches:
            raise cls.DoesNotExist("No branches available")

        return closest_branches


class Atm(models.Model):
    country = models.CharField(max_length=240, default="São Tomé and Príncipe")
    langtitude_cordinates = models.CharField(max_length=240, null=True, blank=True)
    longitude_cordinates = models.CharField(max_length=240, null=True, blank=True)
    address = models.CharField(max_length=400, null=True, blank=True)
    closed = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.address)

    class Meta:
        ordering = ("-date_created",)

    def save(self, *args, **kwargs):
        # geolocator = GoogleV3()
        # location = geolocator.reverse("52.509669, 13.376294")
        # self.address = location.address
        super().save(*args, **kwargs)


class NotificationMessage(models.Model):
    class MessageType(models.TextChoices):
        ACCOUNT_PHONE_NUMBER_VERIFICATION = "ACCOUNT_PHONE_NUMBER_VERIFICATION"
        EMAIL_TOKEN_VERIFICATION = "EMAIL_TOKEN_VERIFICATION"
        COPORATE_STAFF_ACCOUNT_DETAILS = "COPORATE_STAFF_ACCOUNT_DETAILS"
        PASSWORD_OTP_RESET = "PASSWORD_OTP_RESET"
        TEMPORARY_PASSWORD = "TEMPORARY_PASSWORD"
        PASSWORD_RESET_LINK = "PASSWORD_RESET_LINK"
        SEND_OTP = "SEND_OTP"
        PIN_RESET_LINK = "PIN_RESET_LINK"
        CORPORATE_AC_TEMP_PASSWORD = "CORPORATE_AC_TEMP_PASSWORD"
        CORPORATE_AC_ISSUED = "CORPORATE_AC_ISSUED"
        CORPORATE_AC_REJECTED = "CORPORATE_AC_REJECTED"
        TRANSFER_APPROVED = "TRANSFER APPROVED"
        TRANSFER_REJECTED = "TRANSFER REJECTED"

    message_type = models.CharField(
        choices=MessageType.choices,
        max_length=100,
        unique=True,
    )
    title = models.CharField(max_length=240, null=True, blank=True)
    message = models.TextField(help_text="")

    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.message_type)

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = self.message_type
        return super().save(*args, *kwargs)


class TermsAndCondition(models.Model):
    mobile_terms_and_conditions = RichTextField(null=True, blank=True)
    account_opening_terms_and_conditions = RichTextField(null=True, blank=True)

    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str("Terms and Conditions")

    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)

    @classmethod
    def object(cls) -> "TermsAndCondition":
        return cls.objects.get_or_create(id=1)[0]


class OtherBank(models.Model):
    name = models.CharField(max_length=240)
    country = models.CharField(max_length=100)
    currency = models.CharField(max_length=100)
    code = models.CharField(max_length=100, null=True, blank=True)
    active = models.BooleanField(default=True)

    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        ordering = ("name",)


class FileManager(models.Model):
    name = models.CharField(max_length=240)
    file = models.FileField(upload_to="file_management/")

    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.name)


class DigitalPlatformVisits(models.Model):
    user = models.ForeignKey(
        "accounts.CustomUser",
        related_name="visits",
        on_delete=models.SET_NULL,
        null=True,
    )
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.user) if self.user else "Anonymous Visit"


class CardServiceReason(models.Model):
    reason = models.CharField(max_length=255)

    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.reason


class SwiftCode(models.Model):
    swift_code = models.CharField(max_length=50, unique=True)
    bank_name = models.CharField(max_length=100)
    bank_address = models.CharField(max_length=200)

    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.swift_code


class NetworkProvider(models.Model):
    name = models.CharField(max_length=240)
    country = models.CharField(max_length=100)
    currency = models.CharField(max_length=100)
    code = models.CharField(max_length=100, null=True, blank=True)

    active = models.BooleanField(default=True)

    uuid = models.UUIDField(default=uuid.uuid4, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ("name",)


class TelcoDataPlan(models.Model):
    network = models.ForeignKey(
        NetworkProvider, on_delete=models.CASCADE, related_name="data_plans"
    )
    name = models.CharField(max_length=240)
    data = models.CharField(max_length=240)
    price = models.DecimalField(max_digits=19, decimal_places=2)

    date_created = models.DateTimeField(auto_now_add=True)
    last_udpated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name
