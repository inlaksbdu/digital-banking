from django.conf import settings
import requests
import json

# from cbs import models
from django.utils import timezone
from datatable import models as data_tables
from unidecode import unidecode
from loguru import logger
from cbs.models import BankAccount

credentials = settings.T24_CREDENTIALS
base_url = settings.T24_BASE_URL

models = None


class T24Requests:
    """
    ths makes  requests to T2424
    """

    @staticmethod
    def health_check():
        url = f"{base_url}/party/getGtCustomerInfo"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        params = {"customerNumber": str(208)}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            return True
        return False

    @staticmethod
    def verify_phone_number(phone_number):
        """
        verify if customer exist in t2 with same information
        """
        url = f"{base_url}/party/getGtCustomerInfo"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        params = {"mobileNumber": phone_number}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            response = json.loads(response.text)
            body = response["body"]
            return True if body else False

        logger.error("=== ERROR: [Verify Phone] ", response.text)
        return False

    @staticmethod
    def get_customer_info_with_phone(phone_number):
        url = f"{base_url}/party/getGtCustomerInfo"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        formated_phone_number = str(phone_number).replace("+", "")
        params = {"mobileNumber": str(formated_phone_number)}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            logger.info("==== response is 200")
            response = json.loads(response.text)
            body = response["body"]
            return body[0] if body else None

        logger.error("=== ERROR: [Get Customer Info] ", response.text)
        return None

    @staticmethod
    def get_customer_accounts(customer_number):
        url = f"{base_url}/party/getGtiAccountDetails"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        params = {"customerNumber": customer_number}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            response = json.loads(response.text)
            body = response["body"]
            return body if body else None
        logger.error("=== ERROR: [Get Customer Accounts] ", response.text)
        return None

    @staticmethod
    def get_account_details(account_number):
        url = f"{base_url}/party/getGtiAccountDetails"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        params = {"accountNumber": account_number}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            response = json.loads(response.text)
            body = response["body"]
            return body if body else None
        logger.error("=== ERROR: [Get Account Details] ", response.text)
        return None

    @staticmethod
    def update_account_details(account_number):
        url = f"{base_url}/party/getGtiAccountDetails"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        params = {"accountNumber": account_number}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            response = json.loads(response.text)
            body = response["body"]
            try:
                account = body[0]
                logger.info("=== updading accounts: ", account)

                accounts = BankAccount.objects.filter(account_number=account_number)
                for account_object in accounts:
                    account_object.account_balance = (
                        account["workingBalance"]
                        if "workingBalance" in account
                        else account_object.account_balance
                    )
                    account_object.account_restricted = (
                        True if "postingRestrict" in account else False
                    )
                    account_object.save()
                    logger.info("=== account updated")

            except Exception as e:
                logger.error("=== ERROR: [Updating Account Balance] ", e)
                pass
            return body if body else None
        logger.error("=== ERROR: [Update Account Detail] ", response.text)
        return None

    # @staticmethod
    # def get_customer_accounts(customerNumber):
    #     url = f"{base_url}/party/getGtiAccountDetails"
    #     headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
    #     params = {"customerNumber": customerNumber}
    #     response = requests.get(url, headers=headers, params=params)

    #     if response.status_code == 200:
    #         response = json.loads(response.text)
    #         body = response["body"]
    #         try:
    #             return body
    #         except Exception as e:
    #             logger.info("=== ERROR: [Updating Account Balance] ", e)
    #         return body if body else None
    #     logger.info("=== ERROR: [Update Account Detail] ", response.text)
    #     return None

    @staticmethod
    def check_balance(account_number):
        url = f"{base_url}/party/getGtiAccountDetails"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        params = {"accountNumber": account_number}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            response = json.loads(response.text)
            body = response["body"]
            try:
                account = body[0]
                account_balance = (
                    account["workingBalance"] if "workingBalance" in account else 0
                )
                return True, account_balance
            except Exception:
                return False, None
        return False, None

    @staticmethod
    def onboard_customer_v2(user_account):
        customer_profile = user_account.customer_profile
        print("============= printing user account ========")
        print(user_account)
        print(customer_profile)
        try:
            account_category = data_tables.AccountCategory.objects.get(category=6220)
            current_date = timezone.now().strftime("%Y-%m-%d")
            mnemonic = (
                user_account.first_name[:2]
                + user_account.last_name[:2]
                + str(customer_profile.date_of_birth).replace("-", "")
                + str(user_account.id)
            ).upper()
            url = f"{base_url}/party/createNewCustomer"
            headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
            payload = {
                "firstName": unidecode(user_account.first_name),
                "surName": unidecode(user_account.last_name),
                "otherName": "",
                "fullName": unidecode(user_account.fullname.upper()),
                "fullName2": unidecode(user_account.fullname.upper()),
                "shortName": unidecode(user_account.fullname.upper()),
                "mnemonic": unidecode(mnemonic).upper().replace(" ", ""),
                "accountOfficer": "2",
                "target": "5",
                "customerStatus": "19",
                "nationality": "ST",
                "residence": "ST",
                "dateofBirth": str(customer_profile.date_of_birth),
                "dateofIncorp": str(customer_profile.date_of_birth),
                "language": "1",
                "mobileNumber": str(user_account.phone_number).replace("+", ""),
                "mobileNumber2": str(user_account.phone_number).replace("+", ""),
                "customerEmail": user_account.email,
                "resident": "Y",
                "street": "Sao Tome",
                "extensions": {},
            }
            logger.info("==== user payload for account ====")
            logger.info(payload)
            response = requests.post(
                url,
                headers=headers,
                json=json.dumps({"body": payload}),
            )

            logger.info("==== response after account ====")
            print(response.text)
            if response.status_code == 200:
                response = json.loads(response.text)
                header = response["header"]
                customer_id = header["id"]
                customer_code = str(customer_id) + account_category.category[-2:]
                # create an account for customer
                account_url = (
                    f"{base_url}/party/createGtiNewAccountCreation/{customer_code}"
                )
                headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
                payload = {
                    "customerNo": str(customer_id),
                    "category": str(account_category.category),
                    "currency": "STN",
                    "accountName1": user_account.fullname.upper(),
                    "accountShortName": user_account.fullname.upper(),
                    "accountOfficer": "2",
                    "openingDate": str(current_date),
                    "channel": "Mobile",
                    "extensions": {},
                }
                logger.info("====== account payload ====")
                logger.info(payload)
                account_request_response = requests.post(
                    account_url, headers=headers, json=json.dumps({"body": payload})
                )
                logger.info("====== account response ====")
                logger.info(account_request_response.status_code)
                logger.info(account_request_response.text)
                if account_request_response.status_code == 200:
                    acc_req_response = json.loads(account_request_response.text)
                    body = acc_req_response["body"]
                    header = acc_req_response["header"]
                    account_number = header["id"]
                    # create Bank Account for the customer

                    BankAccount.objects.create(
                        user=user_account,
                        account_number=account_number,
                        account_name=user_account.fullname.upper(),
                        account_category=(
                            body["category"] if "category" in body else "None"
                        ),
                        account_restricted=True if "postingRestrict" in body else False,
                        currency=body["currency"],
                    )
                    customer_profile.t24_customer_id = customer_id
                    customer_profile.mnemonic = mnemonic
                    customer_profile.save()
                    try:
                        T24Requests.subscribe_to_credit_alert(
                            account_number, customer_id
                        )
                        T24Requests.subscribe_to_debit_alert(
                            account_number, customer_id
                        )
                    except:
                        pass
                    return body if body else None
                logger.error(
                    "=== ERROR: [Account Creation V2] ",
                    getattr(response, "text", response),
                )
                return None
            logger.error(
                "=== ERROR: [Customer Creation V2] ",
                getattr(response, "text", response),
            )
            return None
        except Exception as e:
            logger.error(e)
            return logger.error("==== error creating customer account")

    @staticmethod
    def get_exchange_rate():
        url = f"{base_url}/party/getExchangeRates"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            response = json.loads(response.text)
            body = response["body"]
            return body if body else None
        logger.error("=== ERROR: [Get exchange Rate] ", response.text)
        return None

    @staticmethod
    def create_standing_order(standing_order):
        url = f"{base_url}/party/createFixedStandingOrder/{standing_order.source_account.account_number}"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        # do some magic for the frequecy
        formated_start_date = str(standing_order.start_date).replace("-", "")
        frequeency = "{formated_start_date} e{year}Y e{month}M e{week}W e{day}D e0F"
        # check for the selected interval
        if standing_order.select_interval == "Weekly":
            frequeency = frequeency.format(
                formated_start_date=formated_start_date,
                day=0,
                week=standing_order.start_date.day,
                month=0,
                year=0,
            )

        elif standing_order.select_interval == "Monthly":
            frequeency = frequeency.format(
                formated_start_date=formated_start_date,
                day=0,
                week=0,
                month=1,
                year=0,
            )
        elif standing_order.select_interval == "Half Yearly":
            frequeency = frequeency.format(
                formated_start_date=formated_start_date,
                day=0,
                week=0,
                month=6,
                year=0,
            )

        elif standing_order.select_interval == "Yearly":
            frequeency = frequeency.format(
                formated_start_date=formated_start_date,
                day=0,
                week=0,
                month=0,
                year=1,
            )

        logger.info("=== standing order date: ", standing_order.end_date)
        payload = {
            "currency": standing_order.source_account.currency,
            "amount": str(standing_order.amount),
            "commenceDateandFreq": frequeency,
            "endDate": (
                str(standing_order.end_date).replace("-", "")
                if standing_order.end_date
                else ""
            ),
            "benefAccountNo": standing_order.recipient_account,
            "statementReference": standing_order.purpose_of_transaction,
            "paymentDetails": standing_order.purpose_of_transaction,
        }
        response = requests.post(
            url, headers=headers, json=json.dumps({"body": payload})
        )

        if response.status_code == 200:
            response = json.loads(response.text)
            body = response["body"]
            return body if body else None
        logger.error("=== ERROR: [Creating Standing Order] ", response.text)
        return None

    @staticmethod
    def create_additional_account(user, account_request):
        current_date = timezone.now().strftime("%Y-%m-%d")
        customer_id = user.t24_customer_id
        customer_code = str(customer_id) + account_request.account_type.category[-2:]
        # create an account for customer
        account_url = f"{base_url}/party/createGtiNewAccountCreation/{customer_code}"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        payload = {
            "customerNo": str(customer_id),
            "category": account_request.account_type.category,
            "currency": "STN",
            "accountName1": user.fullname.upper(),
            "accountShortName": user.fullname.upper(),
            "accountOfficer": "2",
            "openingDate": str(current_date),
            "channel": "Mobile",
            "extensions": {},
        }

        account_request_response = requests.post(
            account_url, headers=headers, json=json.dumps({"body": payload})
        )
        if account_request_response.status_code == 200:
            acc_req_response = json.loads(account_request_response.text)
            body = acc_req_response["body"]
            header = acc_req_response["header"]
            account_number = header["id"]
            # create Bank Account for the customer
            BankAccount.objects.create(
                user=user,
                account_number=account_number,
                account_name=user.fullname.upper(),
                account_category=body["accountShortName"],
                currency=body["currency"],
                account_restricted=True if "postingRestrict" in body else False,
            )
            user.save()
            T24Requests.subscribe_to_credit_alert(account_number, customer_id)
            T24Requests.subscribe_to_debit_alert(account_number, customer_id)
            return body if body else None
        logger.error(
            "=== ERROR: [Addtional Account Creation] ", account_request_response.text
        )
        return None

    @staticmethod
    def subscribe_to_credit_alert(account_number, customer_id):
        # create an account for customer
        account_url = f"{base_url}/party/createAlertRequestDebit"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        payload = {
            "event": "",
            "contractRef": account_number,
            "subscribe": "YES",
            "whatsappAlert": "YES",
            "estatement": "YES",
            "alertLanguage": "PT",
            "customerId": customer_id,
            "recordStatus": "",
            "authoriser": "",
            "companyCode": "",
            "extensions": {},
        }
        response = requests.post(
            account_url, headers=headers, json=json.dumps({"body": payload})
        )
        if response.status_code == 200:
            alert_response = json.loads(response.text)
            body = alert_response["body"]
            return body if body else None
        logger.error("=== ERROR: [SUB TO CREDIT ALERT] ", response.text)
        return None

    @staticmethod
    def subscribe_to_debit_alert(account_number, customer_id):
        # create an account for customer
        account_url = f"{base_url}/party/createAlertRequestCredit"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        payload = {
            "event": "",
            "contractRef": account_number,
            "subscribe": "YES",
            "whatsappAlert": "YES",
            "estatement": "YES",
            "alertLanguage": "PT",
            "customerId": customer_id,
            "recordStatus": "",
            "authoriser": "",
            "companyCode": "",
            "extensions": {},
        }
        response = requests.post(
            account_url, headers=headers, json=json.dumps({"body": payload})
        )
        if response.status_code == 200:
            alert_response = json.loads(response.text)
            body = alert_response["body"]
            return body if body else None
        logger.error("=== ERROR: [SUB TO DEBIT ALERT] ", response.text)
        return None

    @staticmethod
    def get_account_statements(account_number, start_date, end_date):
        account_url = f"{base_url}/party/getAccountStatement?accountNo={account_number}&startDate={start_date}&endDate={end_date}"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}

        response = requests.get(account_url, headers=headers)
        if response.status_code == 200:
            alert_response = json.loads(response.text)
            body = alert_response["body"]
            return body if body else []
        logger.error("=== ERROR: [ACCOUNT STATEMENT] ", response.text)
        return None

    @staticmethod
    def get_customer_dob_phone(phone_number):
        url = f"{base_url}/party/getGtCustomerInfo"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        formated_phone_number = str(phone_number).replace("+", "")
        params = {"mobileNumber": str(formated_phone_number)}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            logger.info("==== response is 200")
            response = json.loads(response.text)
            body = response["body"]
            return body[0] if body else None

        logger.error("=== ERROR: [Get Customer Info] ", response.text)
        return None

    @staticmethod
    def create_standing_order_parperless(standing_order):
        url = (
            f"{base_url}/party/createFixedStandingOrder/{standing_order.source_account}"
        )
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        # do some magic for the frequecy
        formated_start_date = str(standing_order.start_date).replace("-", "")
        frequeency = "{formated_start_date} e{year}Y e{month}M e{week}W e{day}D e0F"
        # check for the selected interval
        if standing_order.interval == "Weekly":
            frequeency = frequeency.format(
                formated_start_date=formated_start_date,
                day=0,
                week=standing_order.start_date.day,
                month=0,
                year=0,
            )

        elif standing_order.interval == "Monthly":
            frequeency = frequeency.format(
                formated_start_date=formated_start_date,
                day=0,
                week=0,
                month=1,
                year=0,
            )
        elif standing_order.interval == "Half Yearly":
            frequeency = frequeency.format(
                formated_start_date=formated_start_date,
                day=0,
                week=0,
                month=6,
                year=0,
            )

        elif standing_order.interval == "Yearly":
            frequeency = frequeency.format(
                formated_start_date=formated_start_date,
                day=0,
                week=0,
                month=0,
                year=1,
            )

        logger.info("=== standing order date: ", standing_order.end_date)
        payload = {
            "currency": standing_order.source_account,
            "amount": str(standing_order.amount),
            "commenceDateandFreq": frequeency,
            "endDate": (
                str(standing_order.end_date).replace("-", "")
                if standing_order.end_date
                else ""
            ),
            "benefAccountNo": standing_order.recipient_account,
            "statementReference": standing_order.purpose_of_transaction,
            "paymentDetails": standing_order.purpose_of_transaction,
        }
        response = requests.post(
            url, headers=headers, json=json.dumps({"body": payload})
        )

        if response.status_code == 200:
            response = json.loads(response.text)
            body = response["body"]
            return body if body else None
        logger.error("=== ERROR: [Creating Standing Order] ", response.text)
        return None

    @staticmethod
    def paperless_get_customer_info(url):
        url = f"{base_url}/{url}"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            logger.info("=== response is 200")
            response = json.loads(response.text)
            body = response["body"]
            return body if body else None
        logger.error("=== ERROR: [PAPERLESS Get Customer Info] ", response.text)
        return None

    @staticmethod
    def get_loans(url):
        url = f"{base_url}/{url}"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            response = json.loads(response.text)
            body = response["body"]
            return body if body else None
        logger.error("=== ERROR: [GET Loans] ", response.text)
        return None

    @staticmethod
    def reverse_transfer(reference_id):
        url = f"{base_url}/party/reversegtiFundsTransfer/{reference_id}"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        response = requests.delete(url, headers=headers)

        if response.status_code == 200:
            response = json.loads(response.text)
            return response if response else None
        logger.error("=== ERROR: [REVERSE ACCOUNT TRANSFER] ", response.text)
        return None

    @staticmethod
    def commit_cash_deposit(body, reference):
        url = f"{base_url}/party/createCashDepositLocal/{reference}"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        response = requests.post(url, headers=headers, json=json.dumps({"body": body}))

        logger.info("=== icoming body ===")
        logger.info(body)

        logger.info("=== t24 response ===")
        logger.info(response.text)

        if response.status_code == 200:
            response_body = json.loads(response.text)

            return True, response_body
        return False, response.text

    @staticmethod
    def commit_cash_withdrawal(body, reference):
        url = f"{base_url}/party/createCashWithdrawalLocal/{reference}"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}
        response = requests.post(url, headers=headers, json=json.dumps({"body": body}))

        logger.info("=== t24 response ===")
        logger.info(response.text)

        if response.status_code == 200:
            response_body = json.loads(response.text)

            return True, response_body
        return False, response.text

    @staticmethod
    def sync_account_statement(account_number, start_date, end_date):
        account_url = f"{base_url}/party/getAccountStatement?accountNo={account_number}&startDate={start_date}&endDate={end_date}&page_size=200"
        headers = {"Content-Type": "application/json", "companyId": "ST0010002"}

        response = requests.get(account_url, headers=headers)
        if response.status_code == 200:
            alert_response = json.loads(response.text)
            body = alert_response["body"]
            return body if body else []
        logger.error("=== ERROR: [ACCOUNT STATEMENT] ", response.text)
        return None
