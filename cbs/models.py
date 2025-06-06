from django.db import models
from accounts.models import CustomUser

# Create your models here.


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
    extra_t24_data = models.TextField(default="{}")
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.account_number)
