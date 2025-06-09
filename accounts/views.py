import json
from . import serializers
from .models import (
    CustomUser,
    UserSecurityQuestion,
    CustomerProfile,
)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from django.db import transaction
from django.contrib.auth.hashers import make_password, check_password
from django.core.cache import cache
from helpers import exceptions
from helpers.functions import generate_otp, generate_reference_id, parse_dob
from datatable import models as data_tables
from accounts.tasks import generic_send_sms, generic_send_mail
from loguru import logger
from t24.t24_requests import T24Requests
from cbs import models as cbs_models
from drf_spectacular.utils import extend_schema
from dj_rest_auth.app_settings import api_settings
from dj_rest_auth.views import sensitive_post_parameters_m
from rest_framework import permissions as rest_permissions
from django.utils.translation import gettext_lazy as _
from rest_framework.generics import GenericAPIView
from rest_framework.viewsets import ModelViewSet
from helpers.access_guradian import log_access_guardian


class UserProfileView(GenericAPIView):
    permission_classes = [rest_permissions.IsAuthenticated]
    serializer_class = serializers.UserProfileSerializer

    def get(self, request, *args, **kwargs):
        user = request.user
        serializer = serializers.UserProfileSerializer(
            user, context={"request": request}
        )
        return Response(data=serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Signup New Customer"])
class SignUpNewCustomerValidationView(CreateAPIView):
    serializer_class = serializers.SignUpNewCustomerValidationSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data.get("phone_number", None)
        email = serializer.validated_data.get("email", None)

        # AFTER VALIDATION SEND OTP TO EMAIL AND PHONE NUMBER
        if phone_number:
            phone_otp = generate_otp(6)
            cache.set(
                f"account_verification_otp/{phone_number}/new-customer/",
                phone_otp,
                60 * 5,
            )
            generic_send_sms.delay(
                body="OTP for your account verification is {}.".format(phone_otp),
                to=str(phone_number),
            )

        if email:
            email_otp = generate_otp(6)
            cache.set(
                f"account_verification_otp/{email}/new-customer/", email_otp, 60 * 5
            )
            payload = {
                "emailType": "account_verification_otp",
                "body": "OTP for your account verification is {}.".format(email),
                "otp": email_otp,
                "subject": "Account Verification OTP",
            }
            generic_send_mail.delay(
                recipient=email,
                title="Account Verification",
                payload=payload,
            )
        return Response(data=serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Signup New Customer"])
class SignUpNewCustomerVerifyView(CreateAPIView):
    serializer_class = serializers.SignUpNewCustomerVerifySerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        email = validated_data.get("email")
        email_otp = validated_data.get("email_otp")
        phone_number = validated_data.get("phone")
        phone_otp = validated_data.get("phone_otp")
        # check and verify otp
        # verify phone number first
        cahced_phone_otp = cache.get(
            f"account_verification_otp/{phone_number}/new-customer/"
        )
        if phone_number and (phone_otp != cahced_phone_otp):
            raise exceptions.InvalidOTPException()

        # verify email
        cahced_email_otp = cache.get(f"account_verification_otp/{email}/new-customer/")
        if email and (email_otp != cahced_email_otp):
            raise exceptions.InvalidOTPException()

        # set random string for verfication
        verification_code = generate_reference_id(10)
        cache.set(
            f"account_verification/{email}/verifcode/new-customer/",
            verification_code,
            60 * 60 * 1,
        )
        cache.set(
            f"account_verification/{phone_number}/verifcode/new-customer/",
            verification_code,
            60 * 60 * 1,
        )
        serializer.data["verification_code"] = verification_code

        data = {
            "email": email,
            "phone_number": phone_number,
            "verification_code": verification_code,
        }

        return Response(data={"status": True, "data": data}, status=status.HTTP_200_OK)


@extend_schema(tags=["Signup New Customer"])
class SignUpNewCustomerView(CreateAPIView):
    serializer_class = serializers.SignUpNewCustomerSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        security_questions = validated_data.get("security_questions", [])

        logger.info("=== singup data ===")
        logger.info(validated_data)

        # created a user and a customer profile
        user_account = CustomUser.objects.create(
            first_name=validated_data.get("first_name"),
            last_name=validated_data.get("last_name"),
            username=validated_data.get("email"),
            email=validated_data.get("email"),
            phone_number=validated_data.get("phone_number"),
            password_set=True,
            secure_pin=make_password(validated_data.get("secure_pin")),
        )
        user_account.set_password(validated_data.get("password"))

        # create customer profile
        customer_profile = CustomerProfile.objects.create(
            user_account=user_account,
            profile_picture=validated_data.get("profile_picture"),
            nationality=validated_data.get("nationality"),
            gender=validated_data.get("gender"),
            date_of_birth=validated_data.get("date_of_birth"),
            id_number=validated_data.get("id_number"),
            id_front=validated_data.get("id_front"),
            place_of_issue=validated_data.get("place_of_issue"),
            date_of_issuance=validated_data.get("date_of_issuance"),
            date_of_expiry=validated_data.get("date_of_expiry"),
        )
        back_image = validated_data.get("id_back")
        if back_image:
            customer_profile.id_back = back_image
        customer_profile.save()

        # create and setup user security questions
        for sec_qtn in security_questions:
            # try to get question object
            try:
                question = data_tables.SecurityQuestion.objects.filter(
                    id=sec_qtn.get("question")
                ).first()
                if question:
                    UserSecurityQuestion.objects.create(
                        user=user_account,
                        question=question,
                        answer_hash=make_password(sec_qtn.get("answer")),
                    )
            except Exception as e:
                logger.error(f"ERROR setting security questions {e}")

        user_account.save()

        # CREATE T24 CUSTOMER
        try:
            core_banking_user = T24Requests.onboard_customer_v2(
                user_account=user_account
            )
            logger.info(f"=== core banking resopnse {core_banking_user}")
            if not core_banking_user:
                raise exceptions.GeneralException(
                    detail="Error creating account, please try again."
                )
        except Exception as e:
            logger.error(f"Error creating account {e}")
            raise exceptions.GeneralException(
                detail="Error creating account, please try again."
            )

        # after account creation send email to customer
        payload = {
            "emailType": "account_created",
            "body": "Your account has been created successfully.",
            "subject": "Account Created",
        }
        generic_send_mail.delay(
            recipient=validated_data.get("email"),
            title="Account Created",
            payload=payload,
        )

        return Response(
            data={
                "status": True,
                "message": "Account Created Successfully, please login to continue.",
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Signup Existing Customer"])
class SignUpExistingEmailAccountValidationView(CreateAPIView):
    serializer_class = (
        serializers.SignUpExistingCustomerEmailAccountValidationSerializer
    )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        email = validated_data.get("email")

        # AFTER VALIDATION SEND OTP PHONE NUMBER
        if email:
            email_otp = generate_otp(6)
            logger.debug(f"=== OTP for Email {email}")
            payload = {
                "emailType": "account_verification_otp",
                "body": "OTP for your account verification is {}.".format(email),
                "otp": email_otp,
                "subject": "Account Verification OTP",
            }
            # set viery cache for 5 minutes
            cache.set(f"account_verification_otp/{email}/", email_otp, 60 * 5)
            generic_send_mail.delay(
                recipient=email,
                title="Account Verification",
                payload=payload,
            )
        return Response(data=serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Signup Existing Customer"])
class SignUpExistingVerifyView(CreateAPIView):
    serializer_class = serializers.SignUpExistingCustomerVerifySerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        email = validated_data.get("email")
        otp = validated_data.get("otp_code")

        # VERIFY EMAIL
        email_otp = cache.get(f"account_verification_otp/{email}/")
        if str(email_otp) != str(otp):
            raise exceptions.InvalidOTPException()
        verification_code = generate_reference_id(10)
        cache.set(
            f"account_verification/{email}/verifcode/", verification_code, 60 * 60 * 1
        )

        data = {
            "email": email,
            "verification_code": verification_code,
        }

        return Response(data={"status": True, "data": data}, status=status.HTTP_200_OK)


@extend_schema(tags=["Signup Existing Customer"])
class SignUpExistingCustomerView(CreateAPIView):
    serializer_class = serializers.SignUpExistingCustomerSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        logger.info(f"=== validated data is {validated_data}")
        customer_info = validated_data.get("account_number").get("customer_info")
        phone_number = customer_info["mobileNumber"]
        email = validated_data.get("email")
        security_questions = validated_data.get("security_questions", [])

        # all validations is done
        # created a user and a customer profile
        user_account = CustomUser.objects.create(
            fullname=customer_info.get("fullName"),
            email=email,
            username=email,
            phone_number=phone_number,
            password_set=True,
            secure_pin=make_password(validated_data.get("secure_pin")),
        )
        user_account.set_password(validated_data.get("password"))

        # create customer profile
        customer_profile = CustomerProfile.objects.create(
            user_account=user_account,
            t24_customer_id=customer_info.get("customerNumber"),
            nationality=customer_info.get("nationality"),
            mnemonic=customer_info.get("mnemonic"),
            date_of_birth=parse_dob(customer_info.get("dateOfBirth")),
        )
        customer_profile.extra_data = json.dumps(customer_info)
        customer_profile.save()

        # create and setup user security questions
        for sec_qtn in security_questions:
            # try to get question object
            try:
                question = data_tables.SecurityQuestion.objects.filter(
                    id=sec_qtn.get("question")
                ).first()
                if question:
                    UserSecurityQuestion.objects.create(
                        user=user_account,
                        question=question,
                        answer_hash=make_password(sec_qtn.get("answer")),
                    )
            except Exception as e:
                logger.error(f"ERROR setting security questions {e}")

        user_account.save()

        # get other bank accounts of the user
        other_bank_accounts = T24Requests.get_customer_accounts(
            customer_number=user_account.customer_profile.t24_customer_id
        )
        if other_bank_accounts:
            for account in other_bank_accounts:
                # check if account number already exists
                if not cbs_models.BankAccount.objects.filter(
                    account_number=account.get("accountNo")
                ).exists():
                    cbs_models.BankAccount.objects.create(
                        user=user_account,
                        account_number=account.get("accountNo"),
                        account_name=account.get("accountName"),
                        account_balance=account.get("workingBalance", 0),
                        account_category=account.get("accountCategory"),
                        currency=account.get("currency"),
                    )

        # after account creation send email to customer
        payload = {
            "emailType": "account_created",
            "body": "Your account has been created successfully.",
            "subject": "Account Created",
        }
        generic_send_mail.delay(
            recipient=email,
            title="Account Created",
            payload=payload,
        )

        return Response(
            data={
                "status": True,
                "message": "Account Created Successfully, please login to continue.",
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Password Change"])
class PasswordChangeView(GenericAPIView):
    """
    Calls Django Auth SetPasswordForm save method.

    Accepts the following POST parameters: new_password1, new_password2
    Returns the success/fail message.
    """

    serializer_class = api_settings.PASSWORD_CHANGE_SERIALIZER
    permission_classes = (rest_permissions.IsAuthenticated,)
    throttle_scope = "dj_rest_auth"

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user = self.request.user
        user.password_set = True
        user.save()
        return Response({"detail": _("New password has been saved.")})


@extend_schema(tags=["Password Reset"])
class ResetPasswordOtpView(CreateAPIView):
    """
    This view sends otp to users who wants to reset thier password.
    """

    permission_classes = (rest_permissions.AllowAny,)
    allowed_methods = ("POST", "OPTIONS", "HEAD")
    serializer_class = serializers.ResetPasswordOtpSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _ = serializer.save()
        return Response(
            {"status": True, "message": "OTP successfully sent"},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Password Reset"])
class ResetPasswordView(CreateAPIView):
    """
    This view sends otp to users who wants to reset thier password.
    """

    permission_classes = (rest_permissions.AllowAny,)
    allowed_methods = ("POST", "OPTIONS", "HEAD")
    serializer_class = serializers.ResetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _ = serializer.save()
        return Response(
            {"message": "You have successfully reset your password."},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Password Reset"])
class VerifyResetPasswordOTPView(CreateAPIView):
    """
    This view verifies the otp sent for password reset.
    """

    permission_classes = (rest_permissions.AllowAny,)
    allowed_methods = ("POST", "OPTIONS", "HEAD")
    serializer_class = serializers.VerifyResetPasswordOtpSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _ = serializer.save()
        return Response(
            {"message": "OTP successfully verified"},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Password Reset"])
class VerifyOldPasswrodViewset(CreateAPIView):
    """
    This view verifies the otp sent for password reset.
    """

    permission_classes = (rest_permissions.AllowAny,)
    allowed_methods = ("POST", "OPTIONS", "HEAD")
    serializer_class = serializers.VerifyOldPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data["password"]
        if not request.user.check_password(password):
            attempt = cache.get(f"password-verification/{request.user.id}")
            if attempt:
                attempt += 1
            else:
                attempt = 1

            cache.set(f"password-verification/{request.user.id}", attempt, 60 * 5)

            if attempt > 3:
                log_access_guardian(
                    request=request,
                    log_type=str(data_tables.AccessGuardian.LogTypes.PASSWORD_CHANGE),
                    phone_number=str(request.user.phone_number),
                )
                raise exceptions.TooManyAttempt()
            return Response(
                {"status": False, "message": "Invalid Password"},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"status": True, "message": "Password successfully Verified"},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Customer PIN"])
class VerifyOldPINViewset(CreateAPIView):
    """
    This view verifies the otp sent for password reset.
    """

    permission_classes = (rest_permissions.AllowAny,)
    allowed_methods = ("POST", "OPTIONS", "HEAD")
    serializer_class = serializers.VerifyPINSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        pin = serializer.validated_data["pin"]
        if not check_password(pin, user.secure_pin):
            attempt = cache.get(f"pin/attempt/{user.id}")
            if attempt:
                attempt += 1
            else:
                attempt = 1
            cache.set(f"pin/attempt/{user.id}", attempt, 60 * 5)
            message = "Invalid PIN"
            if attempt > 3:
                log_access_guardian(
                    request=request,
                    log_type=data_tables.AccessGuardian.LogTypes.INVALID_PIN,
                    phone_number=str(user.phone_number),
                )
                message = "Account Deactivated"

            return Response(
                {
                    "status": False,
                    "message": message,
                    "retries": attempt,
                },
                status=status.HTTP_200_OK,
            )
        cache.delete(f"pin/attempt/{user.id}")
        return Response(
            {"status": True},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Customer PIN"])
class ForgotPINView(CreateAPIView):
    """
    This view sends otp to users who wants to reset thier password.
    """

    permission_classes = (rest_permissions.IsAuthenticated,)
    allowed_methods = ("POST", "OPTIONS", "HEAD")
    serializer_class = serializers.ForgotPINSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data["password"]
        security_anser = serializer.validated_data["security_answer"]

        user = request.user
        if user.check_password(password) and (user.security_answer == security_anser):
            attempt = cache.delete(f"forgot-pin/{user.id}")
            return Response(
                {"status": True, "message": "Reset Your PIN"},
                status=status.HTTP_200_OK,
            )

        attempt = cache.get(f"forgot-pin/{user.id}")
        if attempt:
            attempt += 1
        else:
            attempt = 1

        cache.set(f"forgot-pin/{user.id}", attempt, 60 * 5)

        if attempt > 3:
            log_access_guardian(
                request=request,
                log_type=str(data_tables.AccessGuardian.LogTypes.FORGOT_PIN),
                phone_number=str(user.phone_number),
            )
            raise exceptions.TooManyAttempt()
        return Response(
            {"status": False, "message": "Invalid Password or Security Answer"},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Customer PIN"])
class UpdateUserViewset(ModelViewSet):
    serializer_class = serializers.SetCusotmerPINSerializer
    queryset = CustomUser.objects.all()
    http_method_names = ["patch"]
    permission_classes = [rest_permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            return None
        return queryset.filter(id=self.request.user.id)

    def perform_update(self, serializer):
        validated_data = serializer.validated_data

        if validated_data.get("secure_pin"):
            validated_data["secure_pin"] = make_password(validated_data["secure_pin"])

        serializer.save(**validated_data)
        return super().perform_update(serializer)
