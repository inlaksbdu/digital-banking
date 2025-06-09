from typing import Any, Dict
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig

from cbs.models import BankAccount
from .base import GenericBaseTool


class AccountBalanceInput(BaseModel):
    source_account_id: int = Field(
        description="ID of the account to retrieve the balance for"
    )


class AccountBalanceTool(GenericBaseTool):
    name: str = "account_balance_tool"
    description: str = "Retrieve the balance of a customer's bank account"
    args_schema: Any = AccountBalanceInput

    def _run(
        self,
        source_account_id: int,
        config: RunnableConfig | None = None,
    ) -> Dict[str, Any]:
        user = self.get_user(config)
        user_id = user.get("id")

        try:
            account = BankAccount.objects.get(id=source_account_id, user_id=user_id)
        except BankAccount.DoesNotExist:
            raise ValueError(f"BankAccount with id {source_account_id} not found.")

        return {
            "account_id": source_account_id,
            "account_number": account.account_number,
            "balance": str(account.account_balance),
            "currency": account.currency,
        }
