from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import CustomUser
from cbs.models import BankAccount, CardRequest
from datatable.models import BankBranch


class Command(BaseCommand):
    help = "Add multiple sample CardRequest records and all dependencies."

    def handle(self, *args, **options):
        with transaction.atomic():
            # Create Users
            users = []
            for i in range(3):
                user, _ = CustomUser.objects.get_or_create(
                    email=f"sampleuser{i}@example.com",
                    defaults={
                        "username": f"sampleuser{i}",
                        "fullname": f"Sample User {i}",
                        "password": "pbkdf2_sha256$260000$test$test",  # Not a real password
                    },
                )
                users.append(user)

            # Create Bank Branches
            branches = []
            for i in range(2):
                branch, _ = BankBranch.objects.get_or_create(
                    name=f"Branch {i}",
                    defaults={
                        "country": "São Tomé and Príncipe",
                        "address": f"{i} Main St",
                    },
                )
                branches.append(branch)

            # Create Bank Accounts
            accounts = []
            for i, user in enumerate(users):
                account, _ = BankAccount.objects.get_or_create(
                    account_number=f"100000000{i}",
                    defaults={
                        "user": user,
                        "account_name": user.fullname,
                        "account_category": "SAVINGS",
                        "currency": "STD",
                    },
                )
                accounts.append(account)

            # Create CardRequests
            for i in range(5):
                user = users[i % len(users)]
                account = accounts[i % len(accounts)]
                branch = branches[i % len(branches)]
                CardRequest.objects.create(
                    user=user,
                    source_account=account,
                    card_type="DEBIT CARD" if i % 2 == 0 else "CREDIT CARD",
                    delivery_method="Branch PickUp",
                    pick_up_branch=branch,
                    comments=f"Sample card request {i}",
                )

            self.stdout.write(
                self.style.SUCCESS("Sample CardRequest data and dependencies created.")
            )
