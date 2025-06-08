from django.db import models
from accounts.models import CustomUser
from helpers.functions import generate_reference_id
import uuid
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from datatable import models as data_tables
from phonenumber_field.modelfields import PhoneNumberField
from creditcards.models import CardNumberField, CardExpiryField, SecurityCodeField
from django.utils.translation import gettext_lazy as _

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


class LoanCategory(models.Model):
    amount = models.CharField(max_length=100, null=True, blank=True)
    product_id = models.CharField(max_length=100, null=True, blank=True)
    loan_product_group = models.CharField(max_length=100, null=True, blank=True)
    interest = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=100, null=True, blank=True)
    term = models.CharField(max_length=100, null=True, blank=True)
    processing_fee = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return str(self.product_id)


class LoanRequest(models.Model):
    class ReqeustStatus(models.TextChoices):
        PENDING = "PENDING"
        REVIEWING = "REVIEWING"
        APPROVED = "APPROVED"
        ACTION_REQUIRED = "ACTION REQUIRED"
        REJECTED = "REJECTED"

    application_id = models.CharField(null=True, blank=True, max_length=100)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="loan_requests",
    )
    source_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True,
        related_name="loan_requests",
    )
    loan_category = models.ForeignKey(
        LoanCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name="loan_requests",
    )

    amount = models.DecimalField(decimal_places=2, max_digits=19)
    duration = models.CharField(max_length=100, null=True, blank=True)

    comments = models.TextField(null=True, blank=True)
    # other fields
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        blank=True,
        null=True,
    )
    status = models.CharField(
        choices=ReqeustStatus.choices,
        default=ReqeustStatus.PENDING,
    )
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-date_created",)


class LaonRequestFile(models.Model):
    loan_request = models.ForeignKey(
        LoanRequest, related_name="files", on_delete=models.CASCADE
    )
    file = models.FileField(upload_to="loan_request_files/")

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        blank=True,
        null=True,
    )
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-date_created",)


class AppointmentBooking(models.Model):
    class ServiceType(models.TextChoices):
        CASH_DEPOSIT = "CASH DEPOSIT"
        CASH_WITHDRAWAL = "CASH WITHDRAWAL"
        CHEQUE_DEPOSIT = "CHEQUE DEPOSIT"
        CHEQUE_WITHDRAWAL = "CHEQUE WITHDRAWAL"
        ENQUIRY = "ENQUIRY"

    class BookingType(models.TextChoices):
        SELF = "SELF"
        THIRD_PARTY = "THIRD PARTY"

    class Status(models.TextChoices):
        UPCOMING = "UPCOMING"
        COMPLETED = "COMPLETED"
        CANCELLED = "CANCELLED"

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="appointment_bookings",
    )
    service_type = models.CharField(
        choices=ServiceType.choices, max_length=50, null=True, blank=True
    )

    source_account = models.CharField(max_length=100, null=True, blank=True)
    source_account_name = models.CharField(max_length=100, null=True, blank=True)
    amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=100, null=True, blank=True)

    # FOR CHEQUEs
    cheque_number = models.CharField(max_length=100, null=True, blank=True)
    name_of_cheque_issuer = models.CharField(max_length=100, null=True, blank=True)
    issuing_bank = models.ForeignKey(
        data_tables.OtherBank,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cheque_bookings",
        blank=True,
    )

    # ATTENDEE
    booking_type = models.CharField(max_length=20, choices=BookingType.choices)
    fullname = models.CharField(max_length=100)
    id_number = models.CharField(max_length=100, null=True, blank=True)
    phone_number = PhoneNumberField()

    # BOOKING DETAILS
    branch = models.ForeignKey(
        data_tables.BankBranch,
        on_delete=models.SET_NULL,
        null=True,
        related_name="appointment_bookings",
    )
    date = models.DateField()
    time = models.TimeField()

    # META DATA
    status = models.CharField(
        max_length=100, choices=Status.choices, default=Status.UPCOMING
    )
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        blank=True,
        null=True,
    )
    booking_code = models.CharField(max_length=100, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-date_created",)

    def __str__(self):
        return str(self.user)

    def save(self, *args, **kwargs):
        if not self.booking_code:
            booking = generate_reference_id().upper()
            while AppointmentBooking.objects.filter(booking_code=booking).exists():
                booking = generate_reference_id().upper()
            self.booking_code = booking
        return super().save(*args, **kwargs)


class ExpenseLimit(models.Model):
    class ExpenseLimitType(models.TextChoices):
        ACCOUNT_BUDGET = "Account Budget"
        CATEGORICAL_BUDGET = "Categorical Budget"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        INACTIVE = "INACTIVE"

    limit_type = models.CharField(
        choices=ExpenseLimitType.choices,
        max_length=100,
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="expense_limits",
    )
    account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True,
        related_name="expense_limits",
    )
    category = models.ForeignKey(
        data_tables.TransactionPurpose,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    limit_amount = models.DecimalField(max_digits=19, decimal_places=2)
    amount_spent = models.DecimalField(
        max_digits=19,
        decimal_places=2,
        default=0,
    )

    start_date = models.DateField()
    end_date = models.DateField()

    status = models.CharField(
        max_length=100,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-date_created",)

    def __str__(self):
        return str(self.user)


class CardlessWithdrawal(models.Model):
    class TokenType(models.TextChoices):
        ATM = "ATM"
        MERCHANT = "MERCHANT"

    class WithdrawalParty(models.TextChoices):
        SELF = "SELF"
        THIRD_PARTY = "THIRD_PARTY"

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cardless_withdrawals",
    )
    source_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cardless_withdrawals",
    )
    token_type = models.CharField(
        choices=TokenType.choices,
        max_length=100,
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    valid_through = models.DateField()
    withdrawal_party = models.CharField(
        choices=WithdrawalParty.choices,
        max_length=100,
        null=True,
        blank=True,
        default=WithdrawalParty.SELF,
    )
    recipient_phone_number = PhoneNumberField()
    recipient_name = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    token = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
    )
    token_redeemed = models.BooleanField(default=False)
    token_expired = models.BooleanField(default=False)

    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, blank=True, null=True)

    class Meta:
        ordering = ("-date_created",)

    def __str__(self):
        return str(self.user)

    def save(self, *args, **kwargs):
        if not self.token:
            token = generate_reference_id(12).upper()
            while CardlessWithdrawal.objects.filter(token=token).exists():
                token = generate_reference_id(12).upper()
            self.token = token
        return super().save(*args, **kwargs)


class EmailIndemnity(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="email_indemnity",
    )
    source_account = models.OneToOneField(
        BankAccount,
        on_delete=models.CASCADE,
        related_name="email_indemnity",
    )
    primary_email = models.EmailField()
    secondary_email = models.EmailField(null=True, blank=True)
    phone_number = PhoneNumberField()

    # services
    airtime = models.BooleanField(default=False)
    data = models.BooleanField(default=False)
    bill_payment = models.BooleanField(default=False)
    international_transfer = models.BooleanField(default=False)
    account_to_wallet = models.BooleanField(default=False)
    other_bank_transfer = models.BooleanField(default=False)
    same_bank_transfer = models.BooleanField(default=False)
    own_account_transfer = models.BooleanField(default=False)
    merchant_payment = models.BooleanField(default=False)

    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-date_created",)

    def __str__(self):
        return str(self.user)


class BillSharing(models.Model):
    title = models.CharField(max_length=150)
    initiator = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="bill_sharing_initiated",
    )
    merchant_number = models.CharField(max_length=100)
    merchant_name = models.CharField(max_length=200)
    bill_amount = models.DecimalField(max_digits=19, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=19, decimal_places=2, default=0)

    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-date_created",)

    def __str__(self):
        return str(self.initiator)


class BillSharingPyee(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING"
        PAID = "PAID"
        REJECTED = "REJECTED"
        FAILED = "FAILED"

    bill_sharing = models.ForeignKey(
        BillSharing,
        on_delete=models.CASCADE,
        related_name="bill_sharing_payees",
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="bill_sharing_payees",
    )
    amount = models.DecimalField(max_digits=19, decimal_places=2)

    reference = models.CharField(max_length=100, null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    status = models.CharField(
        choices=Status.choices, max_length=50, default=Status.PENDING
    )
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-date_created",)

    def __str__(self):
        return str(self.user)


class Card(models.Model):
    class CardType(models.TextChoices):
        DEBIT = "DEBIT CARD"
        CREDIT = "CREDIT CARD"

    class VirtualCardType(models.TextChoices):
        GIFT_CARD = "GIFT CARD"
        SHOPPING_CARD = "SHOPPING CARD"

    class CardScheme(models.TextChoices):
        VISA = "VISA"
        MASTERCARD = "MASTERCARD"

    class CardForm(models.TextChoices):
        PHYSICAL = "PHYSICAL CARD"
        VIRTUAL = "VIRTUAL CARD"

    class CardStatus(models.TextChoices):
        ACTIVE = "ACTIVE"
        BLOCKED = "BLOCKED"
        FROZEN = "FROZEN"
        EXPIRED = "EXPIRED"

    card_scheme = models.CharField(
        choices=CardScheme.choices,
        max_length=50,
        default=CardScheme.VISA,
    )
    card_type = models.CharField(
        choices=CardType.choices,
        max_length=50,
        null=True,
        blank=True,
    )
    card_form = models.CharField(
        choices=CardForm.choices,
        max_length=50,
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cards",
    )

    card_number = CardNumberField(_("card number"))
    card_expiry = CardExpiryField(_("expiration date"))
    card_code = SecurityCodeField(_("security code"))
    currency = models.CharField(max_length=50, null=True, blank=True)

    virtual_card_type = models.CharField(
        choices=VirtualCardType.choices,
        max_length=50,
        null=True,
        blank=True,
    )
    card_status = models.CharField(
        choices=CardStatus.choices, default=CardStatus.ACTIVE, max_length=50
    )

    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-date_created",)

    def __str__(self):
        return str(self.card_number)


class CardRequest(models.Model):
    class CardType(models.TextChoices):
        DEBIT = "DEBIT CARD"
        CREDIT = "CREDIT CARD"

    class DeliveryMethod(models.TextChoices):
        BRANCH_PICKUP = "Branch PickUp"

    class Status(models.TextChoices):
        PENDING = "PENDING"
        PROCESSING = "PROCESSING"
        REJECTED = "REJECTED"

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="card_requests",
    )
    source_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name="card_requests",
    )
    card_type = models.CharField(
        choices=CardType.choices,
        max_length=100,
    )
    delivery_method = models.CharField(
        choices=DeliveryMethod.choices,
        max_length=100,
    )
    pick_up_branch = models.ForeignKey(
        data_tables.BankBranch,
        on_delete=models.SET_NULL,
        null=True,
        related_name="card_requests",
    )

    comments = models.TextField(null=True, blank=True)
    status = models.CharField(
        choices=Status.choices,
        max_length=50,
        default=Status.PENDING,
    )
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-date_created",)

    def __str__(self):
        return str(self.user)


class CardManagement(models.Model):
    class ManagementType(models.TextChoices):
        RENEW_CARD = "RENEW CARD"
        REPLACE_CARD = "REPLACE CARD"
        BLOCK_CARD = "BLOCK CARD"
        FREEZE_CARD = "FREEZE CARD"
        UNFREEZE_CARD = "UNFREEZE CARD"

    class DeliveryMethod(models.TextChoices):
        BRANCH_PICKUP = "Branch PickUp"

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="card_managements",
    )
    management_type = models.CharField(
        choices=ManagementType.choices,
        max_length=100,
    )
    card = models.ForeignKey(
        Card,
        on_delete=models.SET_NULL,
        null=True,
        related_name="card_managements",
    )
    reason = models.TextField()
    through_date = models.DateField(
        null=True,
        blank=True,
    )

    delivery_method = models.CharField(
        choices=DeliveryMethod.choices,
        max_length=100,
        null=True,
        blank=True,
    )
    pick_up_branch = models.ForeignKey(
        data_tables.BankBranch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="card_management",
    )
    comments = models.TextField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-date_created",)

    def __str__(self):
        return str(self.user)


class TravelNotice(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="travel_notice",
    )
    departure_date = models.DateField()
    return_date = models.DateField()
    destination_country = models.CharField(max_length=100)

    source_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name="travel_notices",
    )
    card = models.ForeignKey(
        Card,
        on_delete=models.SET_NULL,
        null=True,
        related_name="travel_notices",
    )
    alternative_phone = PhoneNumberField(null=True, blank=True)

    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-date_created",)

    def __str__(self):
        return str(self.user)
