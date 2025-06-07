from celery import shared_task
from django.conf import settings
from loguru import logger
from twilio.rest import Client
from django.core.mail import EmailMultiAlternatives
from jinja2 import Environment, FileSystemLoader
import os
from typing import Dict


@shared_task
def generic_send_mail(recipient, title, payload: Dict[str, str] = {}):
    from_email = settings.DEFAULT_FROM_EMAIL
    env = Environment(
        loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates"))
    )
    template = env.get_template("generic_email.html")
    html_message = template.render(payload)
    logger.info(f"sending email to {recipient}")
    try:
        email = EmailMultiAlternatives(
            subject=title,
            body=html_message,
            from_email=from_email,
            to=[recipient],
        )
        email.attach_alternative(html_message, "text/html")
        email.send()
        return "Mail Sent"
    except Exception as e:
        logger.warning(f"An error ocurred sending email {str(e)}")


# @celery_app.task
@shared_task
def generic_send_sms(to, body):
    # return ""
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    number = settings.TWILIO_SMS_NUMBER

    # Initialize the Twilio client
    client = Client(account_sid, auth_token)

    try:
        # Send the WhatsApp message
        client.messages.create(
            body=str(body),
            from_=str(number),
            to=str(to),
        )

        logger.info("Message sent successfully!")
    except Exception as e:
        logger.warning(f"An error occurred sending otp {e}")


@shared_task
def count_visit(user_id):
    # user = CustomUser.objects.get(id=user_id)
    # if not DigitalPlatformVisits.objects.filter(
    #     user=user, date__date=datetime.now().date()
    # ).exists():
    #     DigitalPlatformVisits.objects.create(user=user)
    pass
