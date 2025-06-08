from accounts.models import CustomUser
from . import models
from t24.t24_requests import T24Requests
from config import celery_app
from django.conf import settings
from loguru import logger
import requests
from .models import ExpenseLimit, BankAccount
from datatable.models import TransactionPurpose


@celery_app.task
def update_customer_bank_accounts(customer_id):
    user = CustomUser.objects.get(customer_profile__t24_customer_id=customer_id)

    response = T24Requests.get_customer_accounts(user.customer_profile.t24_customer_id)

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


@celery_app.task
def get_loan_products():
    page_size = 200
    page_start = 1
    base_url = settings.T24_BASE_URL + "/party/getGtiLoanInfomation/"

    url = f"{base_url}?page_size={page_size}&page_start={page_start}"
    headers = {"Content-Type": "application/json", "companyId": "ST0010001"}
    response = requests.get(url, headers=headers)

    # If the response is not successful, break the loop
    if response.status_code == 200:
        # Parse the response JSON
        data = response.json()
        body = data.get("body", [])
        for data in body:
            try:
                product_id = data.get("productId", "")
                # Check if object with this account number exists
                if not models.LoanCategory.objects.filter(
                    product_id=product_id
                ).exists():
                    category = models.LoanCategory(
                        product_id=data["productId"],
                        loan_product_group=data["loanProductGroup"],
                        amount=data["amount"],
                        interest=data["interest"],
                        description=data["description"],
                        term=data["term"],
                        processing_fee=data["processingFee"],
                    )
                    category.save()
                model = models.LoanCategory.objects.filter(
                    product_id=product_id
                ).first()
                model.loan_product_group = data["loanProductGroup"]
                model.save()
            except Exception as e:
                logger.error("=== error getting loand products ", str(e))
    else:
        logger.info("==== rsponse is not 1000 ====")


@celery_app.task
def update_expense_limit(account_id, transaction_purpose, amount):
    print("== entered function")
    try:
        account = BankAccount.objects.get(id=account_id)
        purpose = TransactionPurpose.objects.get(name=transaction_purpose.strip())

        # check account limit
        if account.expense_limits:
            expense_limit = account.expense_limits.filter(
                limit_type=ExpenseLimit.ExpenseLimitType.ACCOUNT_BUDGET,
                status=ExpenseLimit.Status.ACTIVE,
            )
            if expense_limit.exists():
                expense_limit = expense_limit.first()
                expense_limit.amount_spent += amount
                expense_limit.save()

        # check limit for transaction puprose
        if account.expense_limits:
            expense_limit = account.expense_limits.filter(
                limit_type=ExpenseLimit.ExpenseLimitType.CATEGORICAL_BUDGET,
                category=purpose,
                status=ExpenseLimit.Status.ACTIVE,
            )
            if expense_limit.exists():
                expense_limit = expense_limit.first()
                expense_limit.amount_spent += amount
                expense_limit.save()

        return "Expense limit updated successfully"
    except Exception as e:
        logger.warning(f"An updating expense limit amount {str(e)}")
        return "Error updating expense limit"
