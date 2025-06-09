from typing import Dict, Any, Literal

from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig

from cbs.models import CardRequest
from .base import GenericBaseTool
from django.forms.models import model_to_dict


class CardRequestInput(BaseModel):
    crud: Literal["CREATE", "UPDATE", "VIEW"] = Field(
        description="The action to perform on the card request"
    )
    card_type: Literal["DEBIT CARD", "CREDIT CARD"] | None = Field(
        default=None, description="The type of card to request if CREATE or UPDATE"
    )
    delivery_method: Literal["BRANCH_PICKUP"] | None = Field(
        default=None,
        description="The method of delivery for the card if CREATE or UPDATE",
    )
    pick_up_branch_id: int | None = Field(
        default=None,
        description="ID of the branch to pick up the card from if CREATE or UPDATE",
    )
    source_account_id: int | None = Field(
        default=None,
        description="ID of the account to request the card from if CREATE or UPDATE",
    )
    request_id: int | None = Field(
        default=None,
        description="ID of the card request (required for UPDATE operations)",
    )
    status: Literal["PENDING", "PROCESSING", "REJECTED"] | None = Field(
        default=None, description="The status of the card request"
    )


class CardRequestTool(GenericBaseTool):
    name: str = "card_request_tool"
    description: str = "Use this to create, update, or view card requests"
    args_schema: Any = CardRequestInput

    def _run(
        self,
        crud: Literal["CREATE", "UPDATE", "VIEW"],
        card_type: Literal["DEBIT CARD", "CREDIT CARD"] | None = None,
        delivery_method: Literal["BRANCH_PICKUP"] | None = None,
        pick_up_branch_id: int | None = None,
        source_account_id: int | None = None,
        request_id: int | None = None,
        status: Literal["PENDING", "PROCESSING", "REJECTED"] | None = None,
        config: RunnableConfig | None = None,
    ):
        user: Dict[str, Any] = self.get_user(config)
        user_id = user["id"]

        if crud == "CREATE":
            # Prevent duplicate requests
            if CardRequest.objects.filter(
                user_id=user_id,
                card_type=card_type,
                delivery_method=delivery_method,
                pick_up_branch_id=pick_up_branch_id,
                source_account_id=source_account_id,
            ).exists():
                raise ValueError(
                    "A card request with the same parameters already exists."
                )

            new_request = CardRequest.objects.create(
                user_id=user_id,
                card_type=card_type,
                delivery_method=delivery_method,
                pick_up_branch_id=pick_up_branch_id,
                source_account_id=source_account_id,
            )
            return model_to_dict(new_request)

        elif crud == "UPDATE":
            if request_id is None:
                raise ValueError("request_id is required for update operations.")
            try:
                existing_request = CardRequest.objects.get(
                    id=request_id, user_id=user_id
                )
            except CardRequest.DoesNotExist:
                raise ValueError(f"CardRequest with id {request_id} not found.")
            existing_request.card_type = card_type
            existing_request.delivery_method = delivery_method
            existing_request.pick_up_branch_id = pick_up_branch_id  # type: ignore[attr-defined]
            existing_request.source_account_id = source_account_id  # type: ignore[attr-defined]
            existing_request.save()
            return model_to_dict(existing_request)

        elif crud == "VIEW":
            queryset = CardRequest.objects.filter(user_id=user_id)
            if request_id is not None:
                queryset = queryset.filter(id=request_id)
            if status is not None:
                queryset = queryset.filter(status=status)
            results = list(queryset.values())
            return results

        else:
            raise ValueError(f"Unsupported CRUD operation: {crud}")
