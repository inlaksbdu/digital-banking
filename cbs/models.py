from django.db import models
from accounts.models import CustomUser
from helpers.functions import generate_reference_id
import uuid
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

# Create your models here.


class GenericStatus(models.TextChoices):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class CardType(models.TextChoices):
    DEBIT = "DEBIT CARD"
    CREDIT = "CREDIT CARD"


class CBSStatus(models.TextChoices):
    PENDING = "Pending"
    REQUESTED = "Requested"


class BankAccount(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="bank_accounts",
    )
    account_number = models.CharField(max_length=200)
    account_name = models.CharField(max_length=200)
    account_category = models.CharField(max_length=100)
    account_balance = models.DecimalField(
        max_digits=19,
        decimal_places=2,
        default=0,
        editable=False,
    )
    currency = models.CharField(max_length=20)
    account_restricted = models.BooleanField(default=False)
    default = models.BooleanField(default=False)
    extra_t24_data = models.TextField(default="{}")
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.account_number)

    class Meta:
        ordering = ("-default",)


class Transfer(models.Model):
    class TransferType(models.TextChoices):
        OWN_ACCOUNT_TRANSFER = "Own Account Transfer"
        SAME_BANK_TRANSFER = "Same Bank Transfer"
        OTHER_BANK_TRANSFER = "Other Bank Transfer"
        INTERNATIONAL_TRANSFER = "International Transfer"
        ACCOUNT_TO_WALLET = "Account To Wallet"

    class TransferStatus(models.TextChoices):
        PENDING = "Pending"
        SUCCESS = "Success"
        FAILED = "Failed"

    class ApprovalStatus(models.TextChoices):
        PENDING = "Pending"
        APPROVED = "Approved"
        REJECTED = "Rejected"

    class ChargesBy(models.TextChoices):
        SELF = "SELF"
        BENEFICIARY = "BENEFICIARY"

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="transfers"
    )
    source_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name="transfers"
    )

    recipient_account = models.CharField(max_length=100)
    recipient_name = models.CharField(max_length=100, null=True, blank=True)
    recipient_country = models.CharField(max_length=100, null=True, blank=True)
    recipient_iban_number = models.CharField(max_length=100, null=True, blank=True)
    recipient_bank = models.CharField(max_length=100, null=True, blank=True)
    recipient_swift_code = models.CharField(max_length=100, null=True, blank=True)
    recipient_phone_number = models.CharField(max_length=100, null=True, blank=True)
    recipient_email = models.EmailField(null=True, blank=True)
    recipient_residence_address = models.CharField(
        max_length=100, null=True, blank=True
    )
    charges = models.CharField(
        choices=ChargesBy.choices,
        max_length=50,
        default=ChargesBy.SELF,
    )
    network = models.CharField(max_length=100, null=True, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, null=True, blank=True)

    transfer_type = models.CharField(choices=TransferType.choices, max_length=50)

    purpose_of_transaction = models.CharField(max_length=240)
    comments = models.TextField(null=True, blank=True)

    # statuses
    status = models.CharField(
        choices=TransferStatus.choices, max_length=50, default=CBSStatus.PENDING
    )
    failed_reason = models.TextField(null=True, blank=True)
    edited = models.BooleanField(default=False)

    # OTHER META DATA
    reference = models.CharField(
        max_length=400,
        null=True,
        blank=True,
    )
    channel = models.CharField(max_length=40, null=True, blank=True)
    t24_reference = models.CharField(max_length=240, null=True, blank=True)
    uuid = models.UUIDField(unique=True, blank=True, null=True, default=uuid.uuid4)

    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{}:{}:{}".format(self.transfer_type, self.user, self.reference)

    def save(self, *args, **kwargs):
        # if not self.user.corporate_account:
        self.approval_status = Transfer.ApprovalStatus.APPROVED
        self.approval_by = self.user

        if not self.reference:
            reference = generate_reference_id()
            while Transfer.objects.filter(reference=reference).exists():
                reference = generate_reference_id()
            self.reference = reference
        if not self.currency:
            self.currency = self.source_account.currency

        if (
            not self.recipient_name
            and self.transfer_type == Transfer.TransferType.OWN_ACCOUNT_TRANSFER
        ):
            try:
                recipient_account = BankAccount.objects.get(
                    account_number=self.recipient_account
                )
                self.recipient_name = recipient_account.account_name
            except Exception:
                pass
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ("-date_created",)


class TransactionHistory(models.Model):
    class TransactionType(models.TextChoices):
        TRANSFER = "Transfer"
        PAYMENT = "Payment"
        DEPOSIT = "Deposit"
        WITHDRAWAL = "Withdrawal"

    class CreditDebitStatus(models.TextChoices):
        DEBIT = "Debit"
        CREDIT = "Credit"

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="transaction_history",
    )
    history_ct = models.ForeignKey(
        ContentType,
        related_name="history",
        on_delete=models.SET_NULL,
        null=True,
    )
    history_id = models.PositiveIntegerField(null=True, blank=True)
    history_model = GenericForeignKey("history_ct", "history_id")
    history_type = models.CharField(choices=TransactionType.choices, max_length=20)
    credit_debit_status = models.CharField(
        max_length=20,
        choices=CreditDebitStatus.choices,
        null=True,
        blank=True,
    )
    date_created = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    obj_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.user)

    class Meta:
        ordering = ("-date_created",)
