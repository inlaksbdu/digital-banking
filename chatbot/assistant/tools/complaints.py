from typing import Dict, Any, Literal

from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig

from cbs.models import Complaint, ComplaintCategory
from .base import GenericBaseTool
from django.forms.models import model_to_dict


class ComplaintInput(BaseModel):
    crud: Literal["CREATE", "UPDATE", "VIEW", "LIST_CATEGORIES"] = Field(
        description="The action to perform: CREATE=submit new complaint, UPDATE=modify existing complaint, VIEW=see complaint history, LIST_CATEGORIES=show available complaint categories"
    )
    category_id: int | None = Field(
        default=None,
        description="ID of the complaint category (required for CREATE, use LIST_CATEGORIES first to see available options)",
    )
    description: str | None = Field(
        default=None, description="Description of the complaint (required for CREATE)"
    )
    priority: Literal["LOW", "MEDIUM", "HIGH"] | None = Field(
        default=None,
        description="Priority level of the complaint (required for CREATE): LOW=general issues, MEDIUM=significant problems, HIGH=urgent matters",
    )
    complaint_id: int | None = Field(
        default=None,
        description="ID of the complaint (required for UPDATE and specific VIEW operations)",
    )
    status: (
        Literal["PENDING", "REVIEWING", "RESOLVED", "CLOSED", "ESCALATED"] | None
    ) = Field(
        default=None,
        description="Status of the complaint (for UPDATE operations or filtering VIEW operations)",
    )


class ComplaintTool(GenericBaseTool):
    """
    Comprehensive complaint management tool for customer service chatbot.

    Features:
    - CREATE: Submit new complaints with category, description, and priority
    - UPDATE: Modify existing complaint details (limited for customers)
    - VIEW: Retrieve complaint history and status
    - LIST_CATEGORIES: Show available complaint categories
    """

    name: str = "complaint_management_tool"
    description: str = "Use this to create, update, or view customer complaints. Customers can submit new complaints, update existing ones, or view their complaint history and status."
    args_schema: Any = ComplaintInput

    def _run(
        self,
        crud: Literal["CREATE", "UPDATE", "VIEW", "LIST_CATEGORIES"],
        category_id: int | None = None,
        description: str | None = None,
        priority: Literal["LOW", "MEDIUM", "HIGH"] | None = None,
        complaint_id: int | None = None,
        status: Literal["PENDING", "REVIEWING", "RESOLVED", "CLOSED", "ESCALATED"]
        | None = None,
        config: RunnableConfig | None = None,
    ):
        user: Dict[str, Any] = self.get_user(config)
        user_id = user["id"]

        if crud == "CREATE":
            if not category_id:
                raise ValueError("category_id is required for creating a complaint.")
            if not description:
                raise ValueError("description is required for creating a complaint.")
            if not priority:
                raise ValueError("priority is required for creating a complaint.")

            try:
                category = ComplaintCategory.objects.get(id=category_id)
            except ComplaintCategory.DoesNotExist:
                available_categories = ComplaintCategory.objects.all().values(
                    "id", "category_name"
                )
                categories_list = ", ".join(
                    [
                        f"{cat['id']}: {cat['category_name']}"
                        for cat in available_categories
                    ]
                )
                raise ValueError(
                    f"ComplaintCategory with id {category_id} not found. Available categories: {categories_list}"
                )

            new_complaint = Complaint.objects.create(
                user_id=user_id,
                category_id=category_id,
                description=description,
                priority=priority,
            )
            result = model_to_dict(new_complaint)
            result["category_name"] = category.category_name
            return result

        elif crud == "UPDATE":
            if complaint_id is None:
                raise ValueError("complaint_id is required for update operations.")

            try:
                existing_complaint = Complaint.objects.get(
                    id=complaint_id, user_id=user_id
                )
            except Complaint.DoesNotExist:
                raise ValueError(
                    f"Complaint with id {complaint_id} not found or you don't have permission to update it."
                )

            if existing_complaint.status in ["CLOSED", "RESOLVED"]:
                raise ValueError(
                    "Cannot update a complaint that has been closed or resolved."
                )

            if description is not None:
                existing_complaint.description = description
            if priority is not None:
                existing_complaint.priority = priority

            existing_complaint.save()
            result = model_to_dict(existing_complaint)
            if existing_complaint.category:
                result["category_name"] = existing_complaint.category.category_name
            return result

        elif crud == "VIEW":
            queryset = Complaint.objects.filter(user_id=user_id)

            if complaint_id is not None:
                queryset = queryset.filter(id=complaint_id)

            if status is not None:
                queryset = queryset.filter(status=status)

            complaints = []
            for complaint in queryset:
                complaint_dict = model_to_dict(complaint)
                complaints.append(complaint_dict)

            return complaints

        elif crud == "LIST_CATEGORIES":
            categories = ComplaintCategory.objects.all().values(
                "id", "category_name", "resolution_sla"
            )
            result = []
            for category in categories:
                category_dict = dict(category)
                if category_dict["resolution_sla"]:
                    category_dict["resolution_sla_hours"] = (
                        category_dict["resolution_sla"] // 3600
                    )
                result.append(category_dict)
            return result

        else:
            raise ValueError(f"Unsupported CRUD operation: {crud}")
