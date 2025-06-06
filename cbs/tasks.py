from accounts.models import CustomUser
from . import models
from t24.t24_requests import T24Requests
from config import celery_app


@celery_app.task
def update_customer_bank_accounts(customer_id):
    user = CustomUser.objects.get(t24_customer_id=customer_id)

    response = T24Requests.get_customer_accounts(user.t24_customer_id)

    if response:
        print("== there is response: ", response)
        # update customer accounts here
        for account in response:
            if not models.BankAccount.objects.filter(
                account_number=account["accountNo"]
            ).exists():
                print("=== updating accounts ==")
                models.BankAccount.objects.create(
                    user=user,
                    account_number=account["accountNo"],
                    account_name=account["accountName"],
                    account_category=account["accountCategory"],
                    account_balance=(
                        account["workingBalance"] if "workingBalance" in account else 0
                    ),
                    currency=account["currency"],
                    account_restricted=True if "postingRestrict" in account else False,
                )
    else:
        print("=== no response in other accounts")
