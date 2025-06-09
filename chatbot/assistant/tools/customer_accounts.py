from typing import Dict, Any
from chatbot.assistant.tools.base import GenericBaseTool
from langchain_core.runnables import RunnableConfig
from cbs.models import BankAccount
from pydantic import BaseModel


class CustomerAccountsInput(BaseModel):
    pass


class CustomerAccountsTool(GenericBaseTool):
    name: str = "customer_accounts"
    description: str = "Use this to list the customer's accounts"
    args_schema: Any = CustomerAccountsInput

    def _run(self, *args, config: RunnableConfig | None = None, **kwargs):
        user: Dict[str, Any] = self.get_user(config)

        accounts = BankAccount.objects.filter(user_id=user["id"])
        if accounts.count() == 0:
            return "No accounts found"
        return "\n".join(
            [
                f"Account ID: {account.pk} - Account Number: {account.account_number} - Account Type: {account.account_category} Account Name: {account.account_name}"
                for account in accounts
            ]
        )
