from django.db import models
from accounts.models import CustomUser
from helpers.functions import generate_reference_id
import uuid
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from datatable import models as data_tables

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


class PaymentBiller(models.Model):
    name = models.CharField(max_length=240)
    biller_account = models.CharField(max_length=100)
    biller_logo = models.ImageField(upload_to="payment-billers/", null=True, blank=True)

    uuid = models.UUIDField(unique=True, blank=True, null=True, default=uuid.uuid4)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)


class Payment(models.Model):
    class PaymentType(models.TextChoices):
        AIRTIME = "Airtime"
        DATA = "Data"
        BILL_PAYMENT = "Bill Payment"

    class PaymentStatus(models.Choices):
        PENDING = "Pending"
        SUCCESS = "Success"
        FAILED = "Failed"

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="payments"
    )
    source_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name="payments"
    )

    beneficiary = models.CharField(max_length=240, null=True, blank=True)
    beneficiary_name = models.CharField(max_length=100, null=True, blank=True)

    amount = models.DecimalField(max_digits=19, decimal_places=2)
    currency = models.CharField(max_length=10, null=True, blank=True)

    payment_type = models.CharField(
        choices=PaymentType.choices,
        max_length=100,
    )
    biller = models.ForeignKey(
        PaymentBiller,
        related_name="payments",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    data_plan = models.ForeignKey(
        data_tables.TelcoDataPlan,
        related_name="payments",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    network_provider = models.ForeignKey(
        data_tables.NetworkProvider,
        related_name="payments",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    purpose_of_transaction = models.CharField(max_length=200)

    # META DATA
    status = models.CharField(
        choices=PaymentStatus.choices, max_length=50, default=CBSStatus.PENDING
    )
    reference = models.CharField(
        max_length=240,
        null=True,
        blank=True,
        editable=False,
    )
    channel = models.CharField(max_length=40, null=True, blank=True)
    t24_reference = models.CharField(max_length=240, null=True, blank=True)
    uuid = models.UUIDField(unique=True, blank=True, null=True, default=uuid.uuid4)
    failed_reason = models.TextField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{}:{}:{}".format(self.payment_type, self.user, self.reference)

    def save(self, *args, **kwargs):
        if not self.reference:
            reference = generate_reference_id()
            while Payment.objects.filter(reference=reference).exists():
                reference = generate_reference_id()
            self.reference = reference
        if not self.currency:
            self.currency = self.source_account.currency
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ("-date_created",)


class BankStatement(models.Model):
    class StatementType(models.TextChoices):
        # E_STATEMENT = "E-Statement"
        OFFICIAL_STATEMENT = "Official Statement"

    class Status(models.TextChoices):
        PENDING = "Pending"
        SUCCESS = "Success"
        FAILED = "Failed"

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="bank_statements",
    )
    statement_type = models.CharField(
        choices=StatementType.choices,
        default=StatementType.OFFICIAL_STATEMENT,
        max_length=240,
    )
    source_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name="bank_statements",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    recipient_email = models.EmailField(null=True, blank=True)
    purpose = models.CharField(max_length=240)
    pick_up_branch = models.ForeignKey(
        data_tables.BankBranch,
        on_delete=models.CASCADE,
        related_name="pick_up_branches",
        null=True,
        blank=True,
    )

    status = models.CharField(
        choices=Status.choices,
        max_length=50,
        default=Status.PENDING,
    )
    uuid = models.UUIDField(
        unique=True,
        blank=True,
        null=True,
        default=uuid.uuid4,
    )
    comments = models.TextField(null=True, blank=True)
    channel = models.CharField(max_length=40, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.user)

    class Meta:
        ordering = ("-date_created",)


class Beneficiary(models.Model):

    class BeneficiaryType(models.TextChoices):
        AIRTME = "Airtime"
        DATA = "Data"
        SAME_BANK = "Same Bank"
        OTHER_BANK = "Other Bank"
        ACCOUNT_TO_WALLET = "Account To Wallet"
        INTERNATIONAL_TRANSFER = "International Transfer"
        BILL_PAYMNET = "Bill Payment"

    user = models.ForeignKey(
        CustomUser,
        related_name="beneficiaries",
        on_delete=models.SET_NULL,
        null=True,
    )

    source_account = models.ForeignKey(
        BankAccount,
        related_name="beneficiaries",
        on_delete=models.SET_NULL,
        null=True,
    )

    network_provider = models.ForeignKey(
        data_tables.NetworkProvider,
        related_name="beneficiaries",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    biller = models.ForeignKey(
        PaymentBiller,
        related_name="beneficiaries",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    beneficiary_type = models.CharField(
        choices=BeneficiaryType.choices,
        max_length=100,
    )

    # BENEFICIARY NUMBER
    avatar = models.FileField(upload_to="beneficiary_avatars/", null=True, blank=True)
    beneficiary_number = models.CharField(max_length=200)
    beneficiary_name = models.CharField(max_length=200)
    benficiary_nick_name = models.CharField(max_length=200)

    # BENEFICARY FOR INTERNATIONAL
    beneficiary_country = models.CharField(max_length=200, null=True, blank=True)
    beneficiary_swift_code = models.CharField(max_length=200, null=True, blank=True)
    beneficiary_bank = models.CharField(max_length=200, null=True, blank=True)
    beneficiary_bank_address = models.CharField(max_length=200, null=True, blank=True)
    beneficiary_iban_number = models.CharField(max_length=200, null=True, blank=True)
    beneficiary_email = models.EmailField(null=True, blank=True)
    beneficiary_residence_address = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )

    uuid = models.UUIDField(default=uuid.uuid4, blank=True, null=True, unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.user)

    class Meta:
        ordering = ("-date_created",)


class StandingOrder(models.Model):

    class StandingOrderType(models.TextChoices):
        OWN_ACCOUNT_TRANSFER = "Airtime"
        SAME_BANK = "Same Bank"
        OTHER_BANK = "Other Bank"
        ACCOUNT_TO_WALLET = "Account To Wallet"
        BILL_PAYMNET = "Bill Payment"

    class Interval(models.TextChoices):
        DAILY = "Daily"
        WEEKLY = "Weekly"
        MONTHLY = "Monthly"
        YEARLY = "Yearly"

    class Stuatus(models.TextChoices):
        ACTIVE = "Active"
        INACTIVE = "Inactive"

    class CBSStatus(models.TextChoices):
        PENDING = "Pending"
        REQUESTED = "Requested"
        FAILED = "Failed"

    user = models.ForeignKey(
        CustomUser,
        related_name="standing_order",
        on_delete=models.SET_NULL,
        null=True,
    )

    source_account = models.ForeignKey(
        BankAccount,
        related_name="standing_order",
        on_delete=models.SET_NULL,
        null=True,
    )

    standing_order_type = models.CharField(
        choices=StandingOrderType.choices,
        max_length=100,
    )

    # RECIPIENT
    other_bank = models.ForeignKey(
        data_tables.OtherBank,
        related_name="standing_orders",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    network_provider = models.ForeignKey(
        data_tables.NetworkProvider,
        related_name="standing_orders",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    recipient_account = models.CharField(max_length=200)
    amount = models.DecimalField(decimal_places=2, max_digits=19)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose_of_transaction = models.CharField(max_length=200)

    interval = models.CharField(max_length=100, choices=Interval.choices)

    cbs_status = models.CharField(
        max_length=100, choices=CBSStatus.choices, default=CBSStatus.PENDING
    )
    status = models.CharField(
        max_length=100, choices=Stuatus.choices, default=Stuatus.ACTIVE
    )
    uuid = models.UUIDField(default=uuid.uuid4, blank=True, null=True, unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.user)

    class Meta:
        ordering = ("-date_created",)


class ChequeRequest(models.Model):

    class ChequeLeaves(models.TextChoices):
        TEN = "10 LEAVES"
        TWENTY_FIVE = "25 LEAVES"
        FIFTY = "50 LEAVES"
        SEVENTY_FIVE = "75 LEAVES"
        HUNDRED = "100 LEAVES"
        ONE_FIFTY = "150 LEAVES"

    class ChequeRequestType(models.TextChoices):
        CHEQUE_REQUEST = "CHEQUE REQUEST"
        BLOCK_CHEQUE_REQUEST = "BLOCK CHEQUE"
        CHEQUE_CONFIRMATION = "CONFIRM CHEQUE"

    cheque_request_type = models.CharField(
        choices=ChequeRequestType.choices, max_length=50
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="user_cheque_requests",
    )

    source_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cheque_requests",
    )

    # CHEQUE REQUESTS
    leaves = models.CharField(
        choices=ChequeLeaves.choices,
        max_length=50,
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        data_tables.BankBranch,
        related_name="cheque_services_requests",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # BLOCK/CONFIRM CHEQUE
    cheque_numbers = models.TextField(null=True, blank=True)
    amount = models.DecimalField(
        max_digits=19,
        decimal_places=2,
        null=True,
        blank=True,
    )
    cheque_date = models.DateField(null=True, blank=True)
    reason = models.CharField(max_length=200, null=True, blank=True)

    # META DATA
    comments = models.TextField(null=True, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, blank=True, null=True)
    status = models.CharField(
        choices=GenericStatus.choices,
        default=GenericStatus.PENDING,
    )
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-date_created",)

    def __str__(self):
        return str(self.user)
