import json
import requests
from loguru import logger
from .models import OtherBank, NetworkProvider
from django.core.cache import cache
from django.conf import settings


payStackSecretKey = settings.PAYSTACK_SECRET_KEY
payStackBaseUrl = settings.PAYSTACK_BASE_URL


# @celery_app.task
def get_other_banks():
    cached_key = "get_other_banks"
    if cache.get(cached_key):
        return "Already fetched other bank accounts"
    cache.set(cached_key, True, 2678400)
    headers = {
        "Authorization": f"Bearer {payStackSecretKey}",
        "country": "ghana",
    }

    countries = ["ghana", "kenya", "nigeria"]
    for country in countries:
        base_url = f"{payStackBaseUrl}/bank?country={country}"
        # now make API request
        response = requests.get(base_url, headers=headers)
        logger.info(response)
        if response.status_code != 200:
            return logger.error("=== ERROR: [Get Other Banks] ", response.text)

        json_response = json.loads(response.text)

        data = json_response["data"]

        logger.info("=== data ===")
        logger.info(data)

        for bank in data:
            if (
                bank["type"] not in ["mobile_money", "mobile_money_business"]
                and not OtherBank.objects.filter(code=bank["code"]).exists()
            ):
                OtherBank.objects.create(
                    name=bank["name"],
                    country=bank["country"],
                    currency=bank["currency"],
                    code=bank["code"],
                    active=bank["active"],
                )

    return "Fetched other bank accounts"


def get_other_networks():
    cached_key = "get_other_networks"
    if cache.get(cached_key):
        return "Already fetched other networks accounts"
    cache.set(cached_key, True, 2678400)
    headers = {
        "Authorization": f"Bearer {payStackSecretKey}",
        "country": "ghana",
    }

    countries = ["ghana", "kenya", "nigeria"]
    for country in countries:
        base_url = f"{payStackBaseUrl}/bank?country={country}"
        # now make API request
        response = requests.get(base_url, headers=headers)
        logger.info(response)
        if response.status_code != 200:
            return logger.error("=== ERROR: [Get Other Networks] ", response.text)

        json_response = json.loads(response.text)

        data = json_response["data"]

        logger.info("=== data ===")
        logger.info(data)

        for bank in data:
            if (
                bank["type"] in ["mobile_money", "mobile_money_business"]
                and not NetworkProvider.objects.filter(code=bank["code"]).exists()
            ):
                NetworkProvider.objects.create(
                    name=bank["name"],
                    country=bank["country"],
                    currency=bank["currency"],
                    code=bank["code"],
                    active=bank["active"],
                )

    return "Fetched other bank accounts"


def resolve_phone_number(phone_number, network_provider_code):
    base_url = f"{payStackBaseUrl}/bank/resolve?account_number={phone_number}&bank_code={network_provider_code}"
    payStackSecretKey = "sk_test_86732f7cf3bb44201015c7c95f5e7c370444e308"
    headers = {"Authorization": f"Bearer {payStackSecretKey}"}
    response = requests.get(base_url, headers=headers)
    print(response.status_code)
    print(response)
    if response.status_code != 200:
        return None
    json_response = json.loads(response.text)
    print("=== json response: ", json_response)
    return json_response
