import asyncio
from typing import Dict, Literal, Type
from pydantic import BaseModel, EmailStr, Field
from langchain_core.tools import BaseTool
from langchain_core.runnables import RunnableConfig, ensure_config

from loguru import logger

from src.services.verification.mail import EmailService
from src.library.config import settings


class EscalationInput(BaseModel):
    customer_name: str = Field(..., description="Name of the customer")
    issue_summary: str = Field(..., description="Brief summary of the customer's issue")
    is_urgent: bool = Field(
        default=False, description="Whether this is an urgent escalation"
    )
    customer_sentiment: Literal["angry", "frustrated", "neutral"] = Field(
        "neutral", description="The sentiment of the customer"
    )


class EscalationTool(BaseTool):
    name: str = "escalation_to_human_tool"
    description: str = """Escalates customer service issues to a human agent. 
    Requires customer details and context. Will send an email notification to the assigned agent.
    Use when:
    - Customer explicitly requests human assistance
    - Issue is too complex for AI handling
    - Customer shows significant frustration
    - Sensitive account/financial matters need human oversight"""

    escalate_to: EmailStr
    email_sender: EmailService = EmailService(
        smtp_server=settings.mail_server,
        smtp_port=settings.mail_port,
        sender_email=settings.mail_username,
        password=settings.mail_password,
    )
    args_schema: Type[BaseModel] = EscalationInput

    def _format_email_content(self, input_data: Dict) -> str:
        urgency_badge = "URGENT: " if input_data["is_urgent"] else ""
        sentiment_indicator = (
            "⚠️ Angry Customer"
            if input_data["customer_sentiment"].lower() in ["angry", "frustrated"]
            else ""
        )

        return f"""
        <html>
        <body style="font-family: 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
            <div style="background: linear-gradient(135deg, #6e8efb, #a777e3); padding: 20px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="color: white; margin: 0; font-weight: 600;">{urgency_badge}Customer Escalation {sentiment_indicator}</h2>
                <div style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 30px; display: inline-block; margin-top: 10px;">
                    <span style="color: white; font-weight: 500;">Platform: {input_data["platform"].value}</span>
                </div>
            </div>
            
            <div style="background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 25px;">
                <h3 style="color: #6e8efb; margin-top: 0; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px;">Customer Details</h3>
                <ul style="list-style-type: none; padding: 0;">
                    <li style="padding: 8px 0; border-bottom: 1px solid #f5f5f5;"><strong style="color: #555;">Name:</strong> <span style="color: #333;">{input_data["customer_name"]}</span></li>
                    <li style="padding: 8px 0; border-bottom: 1px solid #f5f5f5;"><strong style="color: #555;">Phone:</strong> <span style="color: #333;">{input_data["customer_phone"] or "Not provided"}</span></li>
                    <li style="padding: 8px 0;"><strong style="color: #555;">Sentiment:</strong> <span style="color: #333; background: {input_data["customer_sentiment"].lower() in ["angry", "frustrated"] and "#ffeaea" or "#e5f8e5"}; padding: 3px 8px; border-radius: 4px;">{input_data["customer_sentiment"]}</span></li>
                </ul>
            </div>
            
            <div style="background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 25px;">
                <h3 style="color: #6e8efb; margin-top: 0; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px;">Issue Summary</h3>
                <p style="color: #444; line-height: 1.7;">{input_data["issue_summary"]}</p>
            </div>
            
            <div style="background: #f0f7ff; padding: 15px; border-radius: 8px; border-left: 4px solid #6e8efb;">
                <p style="color: #555; margin: 0; font-size: 14px;">
                    This escalation was initiated by the AI assistant. Please follow up with the customer as soon as possible.
                </p>
            </div>
        </body>
        </html>
        """

    async def _arun(
        self,
        customer_name: str,
        issue_summary: str,
        is_urgent: bool = False,
        customer_sentiment: str = "neutral",
        config: RunnableConfig | None = None,
    ) -> str:
        try:
            config = ensure_config(config)
            customer_phone = config.get("configurable", {}).get("user_phone")
            if not customer_name or not customer_phone:
                raise ValueError("Customer name, and phone are required to escalate")
            platform = config.get("configurable", {}).get("platform")
            if not platform:
                raise ValueError("Platform is required to escalate")
            input_data = {
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "issue_summary": issue_summary,
                "is_urgent": is_urgent,
                "customer_sentiment": customer_sentiment,
                "platform": platform,
            }
            html_content = self._format_email_content(input_data)
            urgency_prefix = "URGENT: " if is_urgent else ""
            subject = f"{urgency_prefix}Customer Escalation - {customer_name}"
            message = self.email_sender.create_message(
                to_email=self.escalate_to, subject=subject, template=html_content
            )
            success = await self.email_sender._send_email(
                to_email=self.escalate_to, message=message
            )

            if success:
                return f"Successfully escalated to human agent. A notification has been sent to {self.escalate_to}"
            else:
                raise Exception("Failed to send escalation email")

        except Exception as e:
            logger.error(f"Escalation failed: {str(e)}")
            return f"Failed to escalate: {str(e)}"

    def _run(self, *args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(*args, **kwargs))
