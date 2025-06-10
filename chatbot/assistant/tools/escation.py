from typing import Dict, Literal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from langchain_core.runnables import RunnableConfig, ensure_config
from loguru import logger
from pydantic import BaseModel, EmailStr, Field

from chatbot.models import Escalation

from .base import GenericBaseTool


class EscalationInput(BaseModel):
    issue_summary: str = Field(..., description="Brief summary of the customer's issue")
    is_urgent: bool = Field(
        default=False, description="Whether this is an urgent escalation"
    )
    customer_sentiment: Literal["angry", "frustrated", "neutral", "positive"] = Field(
        "neutral", description="The sentiment of the customer"
    )


class EscalationTool(GenericBaseTool):
    name: str = "escalation_to_human_tool"
    description: str = """Escalates customer service issues to a human agent. 
    Requires customer details and context. Will send an email notification to the assigned agent.
    Use when:
    - Customer explicitly requests human assistance
    - Issue is too complex for AI handling
    - Customer shows significant frustration
    - Sensitive account/financial matters need human oversight"""

    escalate_to: EmailStr = settings.ESCALATE_TO

    def _format_email_content(self, input_data: Dict) -> str:
        urgency_badge = "URGENT: " if input_data["is_urgent"] else ""
        sentiment_indicator = (
            "⚠️ Customer requires attention"
            if input_data["customer_sentiment"].lower() in ["angry", "frustrated"]
            else ""
        )

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 20px;">
            <div style="background-color: #1e3a8a; color: white; padding: 20px; margin-bottom: 20px;">
                <h2 style="margin: 0;">{urgency_badge}Customer Escalation {sentiment_indicator}</h2>
                <p style="margin: 10px 0 0 0;">Consolidated Bank of Kenya - Digital Banking Platform</p>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 20px; margin-bottom: 20px;">
                <h3 style="color: #1e3a8a; margin-top: 0;">Customer Details</h3>
                <p><strong>Name:</strong> {input_data["customer_name"]}</p>
                <p><strong>Phone:</strong> {input_data["customer_phone"] or "Not provided"}</p>
                <p><strong>Sentiment:</strong> {input_data["customer_sentiment"]}</p>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 20px; margin-bottom: 20px;">
                <h3 style="color: #1e3a8a; margin-top: 0;">Issue Summary</h3>
                <p>{input_data["issue_summary"]}</p>
            </div>
            
            <div style="background-color: #e7f3ff; padding: 15px; border-left: 4px solid #1e3a8a;">
                <p style="margin: 0; font-size: 14px;">
                    This escalation was initiated by ConsoBot, the AI assistant. Please follow up with the customer as soon as possible.
                </p>
            </div>
        </body>
        </html>
        """

    def _run(
        self,
        issue_summary: str,
        is_urgent: bool = False,
        customer_sentiment: str = "neutral",
        config: RunnableConfig | None = None,
    ) -> str:
        try:
            config = ensure_config(config)
            user: Dict = self.get_user(config)

            UserModel = get_user_model()
            try:
                user_obj = UserModel.objects.get(id=user.get("id"))
            except UserModel.DoesNotExist:
                raise ValueError("User not found in database")

            Escalation.objects.create(
                user=user_obj,
                issue_summary=issue_summary,
                is_urgent=is_urgent,
                customer_sentiment=customer_sentiment,
                escalate_to=self.escalate_to,
            )

            input_data = {
                "customer_name": user_obj.first_name + " " + user_obj.last_name,
                "customer_phone": user_obj.phone_number,  # type: ignore
                "issue_summary": issue_summary,
                "is_urgent": is_urgent,
                "customer_sentiment": customer_sentiment,
            }

            html_content = self._format_email_content(input_data)
            urgency_prefix = "URGENT: " if is_urgent else ""
            subject = f"{urgency_prefix}Customer Escalation - {user.get('fullname')} - Consolidated Bank of Kenya"

            success = send_mail(
                subject=subject,
                message="",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.escalate_to],
                html_message=html_content,
                fail_silently=False,
            )

            if success:
                return f"Successfully escalated to human agent. A notification has been sent to {self.escalate_to}"
            else:
                raise Exception("Failed to send escalation email")

        except Exception as e:
            logger.error(f"Escalation failed: {str(e)}")
            return f"Failed to escalate: {str(e)}"
