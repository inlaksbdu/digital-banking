from django.http import HttpRequest
from rest_framework import serializers

from helpers.access_guradian import log_access_guardian
from .models import (
    CustomUser,
    AccessGuardian,
    CustomerProfile,
)
from helpers import exceptions
from helpers.functions import generate_otp
from dj_rest_auth.serializers import LoginSerializer
from django.db.models import Q
from datetime import datetime, timedelta
from django.core.exceptions import ObjectDoesNotExist
from accounts.tasks import generic_send_mail
from phonenumber_field.serializerfields import PhoneNumberField
from django.core.cache import cache
import user_agents
from t24.t24_requests import T24Requests
from .tasks import count_visit
from loguru import logger
from django.db import transaction
import secrets
from .utils import get_login_notification_data


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = (
            "id",
            "user_account",
            "profile_picture",
            "nationality",
            "gender",
            "date_of_birth",
            "id_number",
            "id_type",
            "id_front",
            "id_back",
            "place_of_issue",
            "date_of_issuance",
            "date_of_expiry",
            "t24_customer_id",
        )


class UserProfileSerializer(serializers.ModelSerializer):
    secure_pin_set = serializers.SerializerMethodField(read_only=True)
    customer_profile = CustomerProfileSerializer(read_only=True)

    def get_secure_pin_set(self, obj):
        return True if obj.secure_pin else False

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "username",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "fullname",
            "password_set",
            "secure_pin_set",
            "deactivated_account",
            "last_login",
            "last_login_ip",
            "customer_profile",
        )


class UserSerializer(serializers.ModelSerializer):
    secure_pin_set = serializers.SerializerMethodField(read_only=True)

    def get_secure_pin_set(self, obj):
        return True if obj.secure_pin else False

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "username",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "fullname",
            "password_set",
            "secure_pin_set",
            "deactivated_account",
            "last_login",
            "last_login_ip",
        )


class ShortUserInfoSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(source="customer_profile.profile_picture")

    class Meta:
        model = CustomUser
        fields = (
            "fullname",
            "email",
            "phone_number",
            "profile_picture",
        )


class CustomLoginSerializer(LoginSerializer):
    """
    Custom Login serializer to overide default dj-rest-auth login
    """

    def custom_validate(self, username):
        try:
            _username = CustomUser.objects.get(username=username)
            # print("=== username: ", _username)
            if not _username.is_active:
                # automatically generate and send otp to the user account.
                otp_generated = generate_otp(6)
                _username.otp = otp_generated
                _username.otp_expiry = datetime.now() + timedelta(minutes=5)
                _username.save()

                # send otp to the user's email
                message = "OTP for your account verification is {}.".format(
                    otp_generated
                )
                generic_send_mail.delay(
                    message=message,
                    recipient_list=_username.email,
                    title="Account Verification OTP",
                )
                # else if
                raise exceptions.InactiveAccountException()
        except ObjectDoesNotExist:
            return username

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def log_access_guardian(self, request, log_type, phone_number=""):
        try:
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            user_agent_string = request.META.get("HTTP_USER_AGENT", "")
            channel = request.META.get("HTTP_CHANNEL", "Other")
            agent = user_agents.parse(user_agent_string)
            if x_forwarded_for:
                ip = x_forwarded_for.split(",")[0]
            else:
                ip = request.META.get("REMOTE_ADDR")
            AccessGuardian.objects.create(
                log_type=log_type,
                phone_number=phone_number,
                device=channel,
                browser=agent.browser.family,
                browser_version=agent.browser.version_string,
                os=agent.os.family,
                os_version=agent.os.version_string,
                ip_address=ip,
            )
        except Exception:
            pass

    def validate(self, attrs):
        request: HttpRequest = self.context.get("request")
        username = attrs.get("username")
        email = attrs.get("email")
        password = attrs.get("password")

        attempt = cache.get(f"login-attempt/{username}")
        if attempt:
            attempt += 1
        else:
            attempt = 1
        cache.set(f"login-attempt/{username}", attempt, 60 * 5)
        if attempt > 5:
            self.log_access_guardian(
                request=request,
                log_type=AccessGuardian.LogTypes.LOGIN_ATTEMPT,
                phone_number=username,
            )
            raise exceptions.TooManyLoginAttemptsException()

        if not (username or email):
            raise exceptions.ProvideUsernameOrPasswordException()

        if username:
            user_qs = CustomUser.objects.filter(
                Q(username=username) | Q(email=username) | Q(phone_number=username),
            )
            if user_qs.exists():
                user = user_qs.first()
                if user.deactivated_account:
                    raise exceptions.AccountDeactivatedException()
                email = user.email
                attrs["email"] = user.email

            else:
                raise exceptions.UsernameDoesNotExistsException()
        elif email:
            user_qs = CustomUser.objects.filter(email=email)
            if user_qs.exists():
                user = user_qs.first()
                if user.deactivated_account:
                    raise exceptions.AccountDeactivatedException()
                username = user.username
                attrs["username"] = user.username
            else:
                raise exceptions.EmailDoesNotExistsException()

        _ = self.custom_validate(username)
        user: CustomUser = self.get_auth_user(username, email, password)

        if not user:
            raise exceptions.LoginException()

        try:
            user.last_login_ip = self.get_client_ip(request)
            user.save()
        except Exception:
            pass
        cache.delete(f"login-attempt/{username}")

        # count customer visit
        count_visit.delay(user_id=user.id)

        # send notificaiton for login
        login_notification_data = get_login_notification_data(
            request=request,
            user_id=user.id,
            security_center_base_url="https://cbkkenya.com/security",
        )

        payload = {
            "emailType": "login_notification",
            "subject": "New device sign in",
            **login_notification_data,
        }

        generic_send_mail.delay(
            recipient=user.email,
            title="Account Verification",
            payload=payload,
        )

        attrs = super().validate(attrs)
        return attrs


class SignUpNewCustomerValidationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_null=True)
    phone_number = PhoneNumberField(required=False)

    def validate(self, attrs):
        if not (attrs.get("email") or attrs.get("phone_number")):
            raise exceptions.ProvideEmailOrPhoneNumberException()
        phone_number = attrs.get("phone_number")
        email = attrs.get("email")
        # check if phone number existsF
        if phone_number:
            if CustomUser.objects.filter(phone_number=phone_number).exists():
                raise exceptions.PhoneNumberAlreadyInUseException()
        # check if email exists
        if email:
            if CustomUser.objects.filter(email=email).exists():
                raise exceptions.EmailAlreadyInUseException()

        return super().validate(attrs)


class SignUpNewCustomerVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    email_otp = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)
    phone_otp = serializers.CharField(required=False)

    def validate(self, attrs):
        email = attrs.get("email")
        email_otp = attrs.get("email_otp")
        phone = attrs.get("phone")
        phone_otp = attrs.get("phone_otp")

        if not (email and email_otp) and not (phone and phone_otp):
            raise serializers.ValidationError(
                "At least email+OTP or phone+OTP must be provided."
            )

        return attrs


class SignupSecurityQuestionSerializer(serializers.Serializer):
    question = serializers.IntegerField()
    answer = serializers.CharField()


class SignUpNewCustomerSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone_number = PhoneNumberField()
    nationality = serializers.CharField()
    gender = serializers.CharField()
    date_of_birth = serializers.DateField()
    profile_picture = serializers.ImageField()
    id_front = serializers.ImageField()
    id_back = serializers.ImageField(required=False, allow_null=True)
    id_number = serializers.CharField()
    date_of_issuance = serializers.DateField()
    date_of_expiry = serializers.DateField()
    place_of_issuance = serializers.CharField()
    security_questions = serializers.ListField(
        child=SignupSecurityQuestionSerializer(),
        required=False,
        allow_null=True,
    )
    password = serializers.CharField()
    secure_pin = serializers.CharField()
    verification_code = serializers.CharField()

    def validate_verification_code(self, verification_code):
        # check if verification code is correct
        email = self.initial_data.get("email")
        phone_number = self.initial_data.get("phone_number")

        cached_email_code = cache.get(
            f"account_verification/{email}/verifcode/new-customer/",
        )
        cached_phone_code = cache.get(
            f"account_verification/{phone_number}/verifcode/new-customer/",
        )

        if str(verification_code) not in [cached_email_code, cached_phone_code]:
            raise exceptions.GeneralException(
                detail="Sorry, the provied verification Code is Invalid."
            )
        return verification_code

    def validate_email(self, email):
        # check if email exists
        if CustomUser.objects.filter(email=email).exists():
            raise exceptions.EmailAlreadyInUseException()
        return email

    def validate_secure_pin(self, secure_pin):
        # check if secure is not more or less than 6 digits
        if len(secure_pin) != 6:
            raise exceptions.GeneralException(
                detail="Sorry, your PIN should be 6 digits."
            )
        # check if pin is not only numbers
        if not secure_pin.isnumeric():
            raise exceptions.GeneralException(
                detail="Sorry, your PIN should be only digits."
            )
        return secure_pin


class SignUpExistingCustomerEmailAccountValidationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    account_number = serializers.CharField()

    def validate_email(self, email):
        # check if email exists
        if CustomUser.objects.filter(email=email).exists():
            raise exceptions.EmailAlreadyInUseException()
        return email

    def validate_account_number(self, account_number):
        # check if account number exists in core banking
        check_account_number = T24Requests.get_account_details(account_number)
        if not check_account_number:
            raise exceptions.AccountNumberNotExist()

        logger.info(check_account_number)
        account_details = check_account_number[0]
        customer_phone_number = account_details.get("customerNo")

        # GET INFO WITH PHONE NUMBER
        customer_info = T24Requests.get_customer_info_with_phone(customer_phone_number)

        # get customer email and compare with entered email
        customer_email = customer_info.get("customerEmail")

        # UNCOMMENT IF YOU WANT BY PASS ACCOUNT EMAIL CHECK
        # if str(customer_email).lower() != str(self.initial_data.get("email")).lower():
        #     raise exceptions.GeneralException(
        #         detail="Sorry, the email entered does not match the account number."
        #     )
        account_number = {
            "account_number": account_number,
            "phone_number": customer_phone_number,
            "customer_email": customer_email,
        }
        return account_number


class SignUpExistingCustomerVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField()


class SignUpExistingCustomerSerializer(serializers.Serializer):
    email = serializers.EmailField()
    account_number = serializers.CharField()
    security_questions = serializers.ListField(
        child=SignupSecurityQuestionSerializer(),
        required=False,
        allow_null=True,
    )
    password = serializers.CharField()
    secure_pin = serializers.CharField()
    verification_code = serializers.CharField()

    def validate_verification_code(self, verification_code):
        # check if verification code is correct
        email = self.initial_data.get("email")
        verification_code = cache.get(f"account_verification/{email}/verifcode/")
        if str(verification_code) != str(self.initial_data.get("verification_code")):
            raise exceptions.GeneralException(
                detail="Sorry, the provied verification Code is Invalid."
            )
        return verification_code

    def validate_email(self, email):
        # check if email exists
        if CustomUser.objects.filter(email=email).exists():
            raise exceptions.EmailAlreadyInUseException()
        return email

    def validate_secure_pin(self, secure_pin):
        # check if secure is not more or less than 6 digits
        if len(secure_pin) != 6:
            raise exceptions.GeneralException(
                detail="Sorry, your PIN should be 6 digits."
            )
        # check if pin is not only numbers
        if not secure_pin.isnumeric():
            raise exceptions.GeneralException(
                detail="Sorry, your PIN should be only digits."
            )
        return secure_pin

    def validate_account_number(self, account_number):
        # check if account number exists in core banking
        check_account_number = T24Requests.get_account_details(account_number)
        if not check_account_number:
            raise exceptions.AccountNumberNotExist()

        logger.info(check_account_number)
        account_details = check_account_number[0]
        customer_phone_number = account_details.get("customerNo")

        # GET INFO WITH PHONE NUMBER
        customer_info = T24Requests.get_customer_info_with_phone(customer_phone_number)

        # get customer email and compare with entered email
        customer_email = customer_info.get("customerEmail")
        # if str(customer_email).lower() != str(self.initial_data.get("email")).lower():
        #     raise exceptions.GeneralException(
        #         detail="Sorry, the email entered does not match the account number."
        #     )
        account_number = {
            "account_number": account_number,
            "phone_number": customer_phone_number,
            "customer_info": customer_info,
        }
        return account_number


class ResetPasswordOtpSerializer(serializers.Serializer):
    """
    this seriailzer sends an otp for password reset. this endpoints is
    used when the user has forggoten his/her password and wants to
    reset.
    """

    username = serializers.CharField()

    def validate_username(self, value):
        if value:
            user_qs = CustomUser.objects.filter(
                Q(email=value) | Q(username=value) | Q(phone_number=value)
            )
            if user_qs.exists():
                return user_qs.first()
            raise exceptions.AccountDoesNotExistException()
        return None

    @transaction.atomic
    def save(self):
        request: HttpRequest = self.context.get("request")
        user_account = self.validated_data.get("username")

        # generate otp code
        otp_generated = generate_otp(6)

        # set otp for password reset
        cache.set(f"password-reset/{user_account.id}", otp_generated, 60 * 5)

        attempt = cache.get(f"reset-password/{user_account.id}")
        if attempt:
            attempt += 1
        else:
            attempt = 1
        cache.set(f"reset-password/{user_account.id}", attempt, 60 * 5)

        if attempt > 3:
            log_access_guardian(
                request=request,
                log_type=str(AccessGuardian.LogTypes.PASSWORD_RESET),
                phone_number=str(user_account.phone_number),
            )
            raise exceptions.TooManyAttempt()
        try:
            notif_object = None
        except Exception:
            notif_object = None

        message = (
            str(notif_object.message).format(
                customer_name=user_account.first_name, otp_generated=otp_generated
            )
            if notif_object
            else (
                f"Hi {user_account.first_name}, Your account password Reset OTP."
                "\nDo not share this with anyone."
            )
        )
        payload = {
            "emailType": "password_reset_otp",
            "body": message,
            "otp": otp_generated,
            "subject": "Account Password Reset OTP",
        }
        generic_send_mail.delay(
            recipient=str(user_account.email),
            title="Account Password Reset OTP",
            payload=payload,
        )

        return user_account


class ResetPasswordSerializer(serializers.Serializer):
    """
    this is the serializer for reseting password by providing otp sent
    for password reset and proviving your new password.
    """

    username = serializers.CharField(max_length=100)
    otp = serializers.CharField(max_length=20)
    new_password = serializers.CharField()

    def validate_username(self, value):
        if value:
            user_qs = CustomUser.objects.filter(
                Q(email=value) | Q(username=value) | Q(phone_number=value)
            )
            if user_qs.exists():
                return user_qs.first()
            raise exceptions.AccountDoesNotExistException()
        return None

    def validate(self, attrs):
        username = attrs.get("username", "")
        otp = attrs.get("otp", "")

        if len(otp) != 6:
            raise exceptions.InvalidOTPException(detail="OTP length Invalid!")
        elif not username:
            raise exceptions.EmailOrUsernameRequiredException()

        user_account = username
        # check if token has expiered or not
        cached_otp = cache.get(f"password-reset/{user_account.id}/otp/{otp}")

        if not cached_otp:
            raise exceptions.InvalidOTPException()

        return attrs

    @transaction.atomic
    def save(self):
        username = self.validated_data.get("username")
        password = self.validated_data.get("new_password")
        user_account: CustomUser = username

        # change password for user
        user_account.set_password(password)
        user_account.save()
        return user_account


class VerifyResetPasswordOtpSerializer(serializers.Serializer):
    """
    this serializer checks and validate the otp sent for password reset
    """

    otp = serializers.CharField(max_length=6)
    username = serializers.CharField(max_length=100)

    def validate_username(self, value):
        if value:
            user_qs = CustomUser.objects.filter(
                Q(email=value) | Q(username=value) | Q(phone_number=value)
            )
            if user_qs.exists():
                return user_qs.first()
            raise exceptions.AccountDoesNotExistException()
        return None

    def validate(self, attrs):
        username = attrs.get("username", "")
        otp = attrs.get("otp", "")

        if len(otp) != 6:
            raise exceptions.InvalidOTPException(detail="OTP length Invalid!")
        elif not username:
            raise exceptions.EmailOrUsernameRequiredException()

        user_account: CustomUser = username
        # check if token has expiered or not
        cached_otp = cache.get(f"password-reset/{user_account.id}")

        if cached_otp != otp:
            raise exceptions.InvalidOTPException()

        # otp verified set cahced data
        cache.set(f"password-reset/{user_account.id}/otp/{cached_otp}", True, 60 * 5)

        return attrs

    @transaction.atomic
    def save(self):
        username = self.validated_data.get("username")
        user: CustomUser = username
        return user


class VerifyPINSerializer(serializers.Serializer):
    pin = serializers.CharField(max_length=100, required=True)


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = PhoneNumberField(allow_blank=False)
    # email = serializers.EmailField(required=False)
    otp = serializers.CharField(max_length=6, min_length=6, required=True)
    registration_token = serializers.SerializerMethodField(read_only=True)
    token: str = ""

    def get_registration_token(self, *args, **kwargs):
        return self.token

    def verify_otp(self, request) -> str:
        """Send email Generate OTP and key and saves them in user account,
        Sends email with an otp to user for Account Activation"""
        # email = self.validated_data["email"]
        phone_number = self.validated_data["phone_number"]
        otp = self.validated_data["otp"]

        print("== verify data: ", phone_number, otp)
        # get token details from cache for a maximum of 24 hours
        cache_otp_value = cache.get(f"otp/phone_number/{phone_number}")
        if cache_otp_value == otp:
            while True:
                token = secrets.token_urlsafe(16)
                if cache.add(
                    f"registration/token/{token}",
                    {"phone_number": str(phone_number)},
                    60 * 60 * 24,
                ):
                    self.token = token
                    break

        else:
            raise exceptions.InvalidOTPException()
        return self.token


class VerifyOldPasswordSerializer(serializers.Serializer):
    """
    this serializer checks and validate the old password
    """

    password = serializers.CharField(max_length=100)


class ForgotPINSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=100)
    security_answer = serializers.CharField(max_length=100)


class SetCusotmerPINSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["secure_pin"]
