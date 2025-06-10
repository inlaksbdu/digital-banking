import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login  # , logout
from django.contrib import messages
from accounts.models import CustomUser, CustomerProfile
from django.db.models import Q
from django.urls import reverse
from accounts.tasks import generic_send_mail, generic_send_sms
from helpers.functions import generate_otp, generate_reference_id
from .tasks import log_action
from helpers.decorator import view_permission, is_staff_user, edit_permission
from django.http import JsonResponse
from .utils import decode_token, create_token, mask_email
import uuid as django_uuid
from django.core.cache import cache
from django.contrib.auth.hashers import make_password, check_password
from . import forms
from cbs import models as cbsmodel
from django.db import transaction

# Create your views here.


def staff_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("dashboard:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")

        user_query = CustomUser._default_manager.filter(
            Q(username__iexact=username)
            | Q(email__iexact=username)
            | Q(phone_number__iexact=username)
        )

        if user_query:
            # get first user from user query
            get_user = user_query.first()
            # log user in with username and password
            user: CustomUser = authenticate(
                username=get_user.username, password=password
            )

            if user is None:
                messages.error(request, "Invalid Credentials Provided")
                return redirect("dashboard:loginview")

            otp = generate_otp(6)
            token = create_token(username, password, otp)

            print("=== decode the token: ")
            decoded_token = decode_token(token)
            print(decoded_token)

            # send email with otp
            payload = {
                "emailType": "account_login",
                "body": "OTP for your account Login for is {}.".format(username),
                "otp": otp,
                "subject": "Account Login 2FA",
            }
            generic_send_mail.delay(
                recipient=username,
                title="Account Login 2FA",
                payload=payload,
            )

            # login(request, user=user)
            return redirect(f"{reverse('dashboard:verify-2fa-otp')}?token={token}")
        else:
            messages.error(request, "Invalid Credentials Provided")
    return render(request, "account/staff_login.html")


def verify_otp_view(request):
    token = request.GET.get("token")
    if not token:
        return JsonResponse(
            {"error": "Token not provided in query parameters"}, status=400
        )

    decoded_token = decode_token(token=token)
    if not decoded_token.get("email"):
        messages.error(request, "Token Expired, Please login again")
        return redirect("dashboard:loginview")
    if request.method == "POST":
        otp = request.POST.get("otp")
        if not decoded_token.get("email"):
            messages.error(request, "Token Expired, Please login again")
            return redirect("dashboard:loginview")
        if decoded_token.get("otp") == otp:
            username = decoded_token["email"]
            password = decoded_token["password"]

            user_query = CustomUser._default_manager.filter(
                Q(username__iexact=username)
                | Q(email__iexact=username)
                | Q(phone_number__iexact=username)
            )

            if user_query:
                # get first user from user query
                get_user = user_query.first()
                user: CustomUser = authenticate(
                    username=get_user.username, password=password
                )
            login(request, user=user)
            return redirect("dashboard:loginview")
        messages.error(request, "Invalid OTP Provided")
    context = {"token": token, "user_email": mask_email(email=decoded_token["email"])}
    return render(request, "account/verify-otp.html", context=context)


@login_required
def index(request):
    return render(request, "index.html")


@login_required(login_url="/")
@is_staff_user
@view_permission("accounts.view_customuser")
def customers(request):
    log_action.delay(
        user_id=request.user.id,
        action="View Customers",
    )
    customers = CustomerProfile.objects.all()
    search_query = request.GET.get("sq")

    if search_query:
        customers = CustomerProfile.objects.filter(
            Q(user__fullname__icontains=search_query)
            | Q(user__email__iexact=search_query)
            | Q(user__phone_number__iexact=search_query)
            | Q(t24_customer_id__iexact=search_query),
        )

    context = {"customers": customers, "sq": search_query}

    return render(
        request,
        "customers/customers.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@view_permission("accounts.view_customuser")
def customer_detail(request, uuid):
    customer = CustomerProfile.objects.get(uuid=uuid)
    recent_transactions = cbsmodel.Transfer.objects.filter(
        user=customer.user_account,
    )[:15]

    context = {"customer": customer, "recent_transactions": recent_transactions}
    log_action.delay(
        user_id=request.user.id,
        action=f"View Customer Detail: {customer}",
    )

    return render(
        request,
        "customers/customer_detail.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@view_permission("accounts.change_customuser")
def send_temporary_password(request, uuid):
    customer = CustomUser.objects.get(uuid=uuid)
    log_action.delay(
        user_id=request.user.id,
        action=f"Sent Temporary Password to Customer: {customer}",
    )
    password = generate_reference_id(length=10)
    customer.set_password(password)
    customer.password_set = False
    customer.save()
    # send password to customer
    body = f"Hi {customer.first_name}, Your password reset request was successful please find your temporary password below.\n\n{password}"

    # send message to customer phone number
    # generic_send_sms.delay(str(customer.phone_number), body)

    payload = {
        "emailType": "reset_links",
        "body": body,
        "reset_link": password,
        "subject": "Send Tempoary Password",
    }
    generic_send_mail.delay(
        recipient=customer.email,
        title="Send Tempoary Password",
        payload=payload,
    )
    messages.success(request, "Temporary password sent successfully")
    return redirect("dashboard:customer-detail", customer.customer_profile.uuid)


@login_required(login_url="/")
@is_staff_user
@view_permission("accounts.change_customuser")
def send_password_reset_link(request, uuid):
    customer = CustomUser.objects.get(uuid=uuid)
    log_action.delay(
        user_id=request.user.id,
        action=f"Sent Password Reset Link to Customer: {customer}",
    )
    url = request.build_absolute_uri()
    domain = url.split("://")[1].split("/")[0]
    http = url.split("://")[0]
    reference = django_uuid.uuid4()
    cache.set(f"password-reset/{customer.uuid}", reference, 60 * 5)
    generated_link = (
        http
        + "://"
        + domain
        + f"/password/{customer.uuid}/reset-password/?ref="
        + str(reference)
    )

    body = f"Hi {customer.first_name}, Click on the link below to reset your password.\n\n{generated_link}"

    # generic_send_sms.delay(str(customer.phone_number), body)

    payload = {
        "emailType": "reset_links",
        "body": body,
        "reset_link": generated_link,
        "subject": "Password Reset Link",
    }
    generic_send_mail.delay(
        recipient=customer.email,
        title="Password Reset Link",
        payload=payload,
    )

    messages.success(request, "Password reset link sent successfully sent.")

    return redirect("dashboard:customer-detail", customer.customer_profile.uuid)


def customer_password_reest(request, uuid):
    customer = CustomUser.objects.get(uuid=uuid)
    reference = request.GET.get("ref")
    timed_ref = cache.get(f"password-reset/{customer.uuid}")
    link_expired = False
    if str(timed_ref) != str(reference):
        link_expired = True
        context = {"link_expired": link_expired}
        return render(
            request, "customers/customer_password_reset.html", context=context
        )

    status = False
    if request.method == "POST":
        form = forms.CustomerPasswordResetForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            pin = form.cleaned_data["pin"]
            new_password = form.cleaned_data["new_password"]
            # check user pin ins correcnt
            if not check_password(pin, customer.secure_pin):
                messages.error(request, "Incorrect PIN")
                url = reverse("dashboard:customer-reset-password", args=[customer.uuid])
                url_with_params = f"{url}?ref={reference}"
                return redirect(url_with_params)
            user = customer
            user.set_password(new_password)
            user.save()
            status = True
            messages.success(request, "Password reset successfully")

        else:
            messages.error(request, forms.erros)

    else:
        form = forms.CustomerPasswordResetForm()

    context = {
        "customer": customer,
        "status": status,
        "link_expired": link_expired,
        "password_reset_form": form,
    }

    return render(request, "customers/customer_password_reset.html", context=context)


@login_required(login_url="/")
@is_staff_user
@edit_permission("accounts.view_customuser", "accounts.change_customuser")
def deactivate_customer_account(request, uuid):
    customer = CustomUser.objects.get(uuid=uuid)
    log_action.delay(
        user_id=request.user.id,
        action=f"Visit customer deactivation screen: {customer}",
    )

    if request.method == "POST":
        form = forms.AccountDeactivationForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            reason = form.cleaned_data["reason"]
            password = form.cleaned_data["password"]

            # check user password is correct
            if not request.user.check_password(password):
                messages.error(request, "Incorrect password")
                return redirect(
                    "dashboard:customer-account-deactivation", customer.uuid
                )

            # deactivate account
            customer.deactivated_account = True
            customer.save()
            messages.success(request, "Customer account deactivated successfully")
            log_action.delay(
                user_id=request.user.id,
                action=f"Deactivated customer account: {customer}",
            )
            return redirect("dashboard:customer-detail", customer.customer_profile.uuid)
        else:
            print(form.errors)
    else:
        form = forms.AccountDeactivationForm()

    context = {
        "customer": customer,
        "form": form,
    }

    return render(
        request,
        "customers/account_deactivation.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@edit_permission("accounts.view_customuser", "accounts.change_customuser")
def activate_customer_account(request, uuid):
    customer = CustomUser.objects.get(uuid=uuid)
    log_action.delay(
        user_id=request.user.id,
        action=f"Visit customer deactivation screen: {customer}",
    )

    if request.method == "POST":
        form = forms.AccountDeactivationForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            reason = form.cleaned_data["reason"]
            password = form.cleaned_data["password"]

            # check user password is correct
            if not request.user.check_password(password):
                messages.error(request, "Incorrect password")
                return redirect("dashboard:customer-account-activation", customer.uuid)

            # deactivate account
            customer.deactivated_account = False
            customer.save()
            messages.success(request, "Customer account activated successfully")
            log_action.delay(
                user_id=request.user.id,
                action=f"Activated customer account: {customer}",
            )
            return redirect("dashboard:customer-detail", customer.customer_profile.uuid)
        else:
            print(form.errors)
    else:
        form = forms.AccountDeactivationForm()

    context = {
        "customer": customer,
        "form": form,
    }

    return render(
        request,
        "customers/account_deactivation.html",
        context=context,
    )


def customer_pin_reest(request, uuid):
    customer = CustomUser.objects.get(uuid=uuid)
    reference = request.GET.get("ref")
    timed_ref = cache.get(f"pin-reset/{customer.uuid}")
    link_expired = False
    if str(timed_ref) != str(reference):
        link_expired = True
        context = {"link_expired": link_expired}
        return render(request, "customers/customer_pin_reset.html", context=context)

    status = False
    if request.method == "POST":
        form = forms.CustomerPINResetForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            password = form.cleaned_data["password"]
            new_pin = form.cleaned_data["new_pin"]
            # check user pin ins correcnt
            if not customer.check_password(password):
                messages.error(request, "Invalid Password")
                url = reverse("dashboard:customer-reset-pin", args=[customer.uuid])
                url_with_params = f"{url}?ref={reference}"
                return redirect(url_with_params)
            user = customer
            user.secure_pin = make_password(new_pin)
            user.save()
            status = True
            messages.success(request, "PIN reset successfully")
        else:
            messages.error(request, forms.erros)

    else:
        form = forms.CustomerPINResetForm()

    context = {
        "customer": customer,
        "status": status,
        "link_expired": link_expired,
        "password_reset_form": form,
    }

    return render(request, "customers/customer_pin_reset.html", context=context)


@login_required(login_url="/")
@is_staff_user
@view_permission("accounts.change_customuser")
def send_pin_reset_link(request, uuid):
    customer = CustomUser.objects.get(uuid=uuid)
    log_action.delay(
        user_id=request.user.id,
        action=f"Sent PIN Reset Link to Customer: {customer}",
    )
    url = request.build_absolute_uri()
    domain = url.split("://")[1].split("/")[0]
    http = url.split("://")[0]
    reference = django_uuid.uuid4()
    cache.set(f"pin-reset/{customer.uuid}", reference, 60 * 5)
    generated_link = (
        http + "://" + domain + f"/pin-reset/{customer.uuid}/?ref=" + str(reference)
    )

    body = f"Hi {customer.first_name}, Click on the link below to reset your password.\n\n{generated_link}"

    # generic_send_sms.delay(str(customer.phone_number), body)
    messages.success(request, "PIN reset link sent successfully sent.")

    payload = {
        "emailType": "reset_links",
        "body": body,
        "reset_link": generated_link,
        "subject": "PIN Reset Link",
    }
    generic_send_mail.delay(
        recipient=customer.email,
        title="PIN Reset Link",
        payload=payload,
    )

    return redirect("dashboard:customer-detail", customer.customer_profile.uuid)


def customer_requests(request):
    digital_visits = {}
    digital_visits["Card"] = cbsmodel.CardRequest.objects.count()
    digital_visits["Cheque"] = cbsmodel.ChequeRequest.objects.count()
    digital_visits["Loans"] = cbsmodel.LoanRequest.objects.count()
    digital_visits["A/C Statement"] = cbsmodel.BankStatement.objects.filter(
        statement_type="Official Statement"
    ).count()

    loan_requests = cbsmodel.LoanRequest.objects.filter(
        status__in=["PENDING", "REVIEWING", "ACTION REQUIRED"],
    ).count()
    transfers = cbsmodel.Transfer.objects.filter(
        status=cbsmodel.Transfer.TransferStatus.PENDING,
        # transfer_type__in=["Other Bank Transfer", "International Transfer"],
    ).count()
    cheque_requests = cbsmodel.ChequeRequest.objects.filter(
        status__in=[
            "PENDING",
            "PROCESSING",
        ],
    ).count()
    card_requests = cbsmodel.CardRequest.objects.filter(
        status__in=[
            "PENDING",
            "PROCESSING",
        ],
    ).count()
    account_statements = cbsmodel.BankStatement.objects.filter(
        statement_type="Official Statement",
        status="Pending",
    ).count()

    # do the numbers here

    context = {
        "customer_visits": json.dumps(digital_visits),
        "loan_requests": loan_requests,
        "transfers": transfers,
        "cheque_requests": cheque_requests,
        "card_requests": card_requests,
        "account_statements": account_statements,
    }
    return render(request, "customer_request/requests.html", context=context)


@login_required(login_url="/")
@is_staff_user
@view_permission("cbs.view_bankstatement")
def bank_statement(request):
    log_action.delay(
        user_id=request.user.id,
        action="View Bank Statements",
    )
    bank_statements = cbsmodel.BankStatement.objects.filter(
        statement_type="Official Statement",
        status="Pending",
    )

    context = {"bank_statements": bank_statements}

    return render(
        request, "customer_request/bank_statement/bank_statements.html", context=context
    )


@login_required(login_url="/")
@is_staff_user
@view_permission("cbs.view_bankstatement")
def bank_statement_hisotry(request):
    log_action.delay(
        user_id=request.user.id,
        action="View Bank Statements History",
    )
    bank_statements = cbsmodel.BankStatement.objects.filter(
        status__in=["Success", "Failed"],
    )

    context = {"bank_statements": bank_statements}

    return render(
        request,
        "customer_request/bank_statement/bank_statements_history.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@edit_permission("cbs.view_bankstatement", "cbs.change_bankstatement")
def bank_statement_detail(request, uuid):
    bank_statement = cbsmodel.BankStatement.objects.get(uuid=uuid)
    log_action.delay(
        user_id=request.user.id,
        action=f"View Bank Statement Detail: {str(bank_statement)}",
    )

    if request.method == "POST":
        form = forms.ChangeBankStatementStatus(
            data=request.POST, instance=bank_statement
        )
        if form.is_valid():
            instnace = form.save()
            messages.success(request, "Status updated successfully")
            body = instnace.comments
            generic_send_sms.delay(str(bank_statement.user.phone_number), body)
            log_action.delay(
                user_id=request.user.id,
                action=f"Changed Bank Statement Status, with comments: {body}",
            )
        else:
            messages.error(request, form.errors)

    context = {
        "bank_statement": bank_statement,
        "change_status_form": forms.ChangeBankStatementStatus(instance=bank_statement),
    }

    return render(
        request,
        "customer_request/bank_statement/bank_statement_detail.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@view_permission("cbs.view_loanrequest")
def loan_requests(request):
    log_action.delay(
        user_id=request.user.id,
        action="View Lona requests",
    )
    loan_requests = cbsmodel.LoanRequest.objects.filter(
        status__in=["PENDING", "REVIEWING", "ACTION REQUIRED"],
    )

    context = {"loan_requests": loan_requests}

    return render(
        request, "customer_request/loan_request/laon_requests.html", context=context
    )


@login_required(login_url="/")
@is_staff_user
@view_permission("cbs.view_loanrequest")
def loan_requests_history(request):
    log_action.delay(
        user_id=request.user.id,
        action="View Load Request History",
    )
    loan_requests = cbsmodel.LoanRequest.objects.filter(
        status__in=["REJECTED", "APPROVED"],
    )

    context = {"loan_requests": loan_requests}

    return render(
        request,
        "customer_request/loan_request/laon_requests_history.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@edit_permission("cbs.view_loanrequest", "cbs.change_loanrequest")
def loan_request_detail(request, uuid):
    loan_request = cbsmodel.LoanRequest.objects.get(uuid=uuid)
    log_action.delay(
        user_id=request.user.id,
        action=f"View Loan Request Detail: {str(loan_request)}",
    )
    if loan_request.status == cbsmodel.LoanRequest.ReqeustStatus.PENDING:
        loan_request.status = cbsmodel.LoanRequest.ReqeustStatus.REVIEWING
        loan_request.save()

    if request.method == "POST":
        form = forms.ChangeLoanrequestStatus(data=request.POST, instance=loan_request)
        if form.is_valid():

            instnace = form.save()
            messages.success(request, "Status updated successfully")
            body = instnace.comments
            generic_send_sms.delay(str(loan_request.user.phone_number), body)
            log_action.delay(
                user_id=request.user.id,
                action=f"Changed Loan Request Status, with comments: {body}",
            )
        else:
            messages.error(request, form.errors)

    context = {
        "loan_request": loan_request,
        "change_status_form": forms.ChangeLoanrequestStatus(instance=loan_request),
    }

    return render(
        request,
        "customer_request/loan_request/laon_requests_detail.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@view_permission("cbs.view_transfer")
def transfers(request):
    log_action.delay(
        user_id=request.user.id,
        action="View Transfers Requests",
    )
    transfers = cbsmodel.Transfer.objects.all()

    context = {"transfers": transfers}

    return render(
        request,
        "customer_request/transfers/transfer_requests.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@edit_permission("cbs.view_transfer", "cbs.change_transfer")
def transfer_requests_detail(request, uuid):
    transfer = cbsmodel.Transfer.objects.get(uuid=uuid)
    log_action.delay(
        user_id=request.user.id,
        action=f"View Transfers Requests Detail: {transfer}",
    )

    if request.method == "POST":
        form = forms.ChangeTransferRequestStatus(data=request.POST, instance=transfer)
        if form.is_valid():
            instnace = form.save()
            messages.success(request, "Status updated successfully")
            body = instnace.comments
            generic_send_sms.delay(str(transfer.user.phone_number), body)
            if body:
                log_action.delay(
                    user_id=request.user.id,
                    action=f"Changed Transfer request status, with reason: {body}",
                )
        else:
            messages.error(request, form.errors)

    context = {
        "transfer": transfer,
        "change_status_form": forms.ChangeTransferRequestStatus(instance=transfer),
    }

    return render(
        request,
        "customer_request/transfers/transfer_request_detail.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@view_permission("cbs.view_transfer")
def transfer_requests_history(request):
    log_action.delay(
        user_id=request.user.id,
        action="View Transfers Requests History",
    )
    transfers = cbsmodel.Transfer.objects.filter(
        status__in=["Success", "Failed"],
        transfer_type__in=["Other Bank Transfer", "International Transfer"],
    )

    context = {"transfers": transfers}

    return render(
        request,
        "customer_request/transfers/transfer_request_history.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@view_permission("cbs.view_chequerequest")
def cheque_requests(request):
    log_action.delay(
        user_id=request.user.id,
        action="View Cheque Requests",
    )
    cheque_requests = cbsmodel.ChequeRequest.objects.filter(
        status__in=[
            "PENDING",
            "PROCESSING",
        ],
    )

    context = {"cheque_requests": cheque_requests}

    return render(
        request,
        "customer_request/cheque_requests/cheque_requests.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@view_permission("cbs.view_chequerequest")
def cheque_request_history(request):
    log_action.delay(
        user_id=request.user.id,
        action="View Cheque Request History",
    )
    cheque_requests = cbsmodel.ChequeRequest.objects.filter(
        status__in=["COMPLETED", "REJECTED", "FAILED"],
    )

    context = {"cheque_requests": cheque_requests}

    return render(
        request,
        "customer_request/cheque_requests/cheque_requests_history.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@edit_permission("cbs.view_chequerequest", "cbs.change_chequerequest")
def cheque_request_detail(request, uuid):
    cheque_request = cbsmodel.ChequeRequest.objects.get(uuid=uuid)
    log_action.delay(
        user_id=request.user.id,
        action=f"View Cheque Request Detail: {str(cheque_request)}",
    )

    if request.method == "POST":
        form = forms.ChequeRequestStatusChange(
            data=request.POST, instance=cheque_request
        )
        if form.is_valid():

            instnace = form.save()
            messages.success(request, "Status updated successfully")
            body = instnace.comments
            generic_send_sms.delay(str(cheque_request.user.phone_number), body)
            log_action.delay(
                user_id=request.user.id,
                action=f"Changed Cheque Request detail, with comments: {body}",
            )
        else:
            messages.error(request, form.errors)

    context = {
        "cheque_request": cheque_request,
        "change_status_form": forms.ChequeRequestStatusChange(instance=cheque_request),
    }

    return render(
        request,
        "customer_request/cheque_requests/cheque_requests_detail.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@view_permission("cbs.view_cardservice")
def card_request(request):
    log_action.delay(
        user_id=request.user.id,
        action="View Card Services Requests",
    )
    card_requests = cbsmodel.CardRequest.objects.filter(
        status__in=[
            "PENDING",
            "PROCESSING",
        ],
    )

    context = {"card_requests": card_requests}

    return render(
        request,
        "customer_request/card_services/card_service_requests.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@view_permission("cbs.view_cardservice")
def card_request_history(request):
    log_action.delay(
        user_id=request.user.id,
        action="View Card Service Request History",
    )
    card_requests = cbsmodel.CardRequest.objects.filter(
        status__in=["COMPLETED", "REJECTED", "FAILED"],
    )

    context = {"card_requests": card_requests}

    return render(
        request,
        "customer_request/card_services/card_service_requests_history.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@edit_permission("cbs.view_cardservice", "cbs.change_cardservice")
def card_request_detail(request, uuid):
    card_request = cbsmodel.CardRequest.objects.get(uuid=uuid)
    log_action.delay(
        user_id=request.user.id,
        action=f"View Card Service Request Detail: {str(card_request)}",
    )

    if request.method == "POST":
        form = forms.CardRequestStatusChange(data=request.POST, instance=card_request)
        if form.is_valid():

            instnace = form.save()
            messages.success(request, "Status updated successfully")
            body = instnace.comments
            generic_send_sms.delay(str(card_request.user.phone_number), body)
            log_action.delay(
                user_id=request.user.id,
                action=f"Changed Card Service Request detail, with comments: {body}",
            )
        else:
            messages.error(request, form.errors)

    context = {
        "card_request": card_request,
        "change_status_form": forms.CardRequestStatusChange(instance=card_request),
    }

    return render(
        request,
        "customer_request/card_services/card_service_requests_detail.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@view_permission("cbs.view_payment")
def payments(request):
    log_action.delay(
        user_id=request.user.id,
        action="View Payments",
    )
    payments = cbsmodel.Payment.objects.filter()

    context = {"payments": payments}

    return render(
        request,
        "payments/payments.html",
        context=context,
    )


@login_required(login_url="/")
@is_staff_user
@view_permission("cbs.view_payment")
def payments_detail(request, uuid):
    payment = cbsmodel.Payment.objects.get(uuid=uuid)
    log_action.delay(
        user_id=request.user.id,
        action=f"View Payments Detail: {payment}",
    )

    context = {"payment": payment}
    return render(
        request,
        "payments/payment_detail.html",
        context=context,
    )


"""

CUTOMER ONBOARDING

- New Cusomter onboarding
    - Verify Phone Number
    - Verify Email
    - Fill the Form
    - Complate Registration

- Existing Customer Signup
    - Verify Email
    - Verify Customer Account
    - Fill the Form
    - Complate Registration

"""


# password = phone number
# otp = generated
# email = phone number


def verify_phone_number(request):
    token = request.GET.get("token")
    inputed_phone_number = None
    form = forms.NewCustomerVerifyPhoneForm()

    # check check outsie if there is token
    if token:
        decoded_token = decode_token(token=token)
        if not decoded_token.get("email"):
            # token has expired
            messages.error(request, "Token Expired, please resend token")
            return redirect("dashboard:onboarding-verify-phone")

        inputed_phone_number = decoded_token.get("email")

    if request.method == "POST":
        # check if there is a token verify otp
        if token:
            decoded_token = decode_token(token=token)
            if not decoded_token.get("email"):
                # token has expired
                messages.error(request, "Token Expired, please resend token")
                return redirect("dashboard:onboarding-verify-phone")

            inputed_phone_number = decoded_token.get("email")
            saved_otp = decoded_token.get("otp")
            entered_otp = request.POST.get("otp")

            if saved_otp == entered_otp:
                messages.success(request, "OTP verified successfully")
                # save phone number in cache
                cache.set(
                    "_customer_onboarding_phone_number",
                    inputed_phone_number,
                    60 * 60 * 24,
                )

                return redirect("dashboard:onboarding-verify-email")
            else:
                messages.error(request, "OTP verification failed")

        else:
            form = forms.NewCustomerVerifyPhoneForm(request.POST)
            if form.is_valid():
                phone_number = form.cleaned_data["phone_number"]
                print("==== phone number: ", phone_number)
                generated_otp = generate_otp(6)
                token = create_token(
                    email=str(phone_number), password="", otp=generated_otp
                )

                # send an sms with the OTP
                body = """
Dear Customer, Your OTP Code for Account Onboarding is {otp}.
Please do not share this code with anyone.

Thank you.
                """.format(
                    otp=generated_otp
                )

                generic_send_sms.delay(to=str(phone_number), body=body)

                # prepare and send OTP to the phone number
                messages.success(request, "OTP sent to your phone number")
                return redirect(
                    f"{reverse('dashboard:onboarding-verify-phone')}?token={token}"
                )

    context = {"form": form, "token": token, "phone_number": inputed_phone_number}
    return render(
        request, "customer_onboarding/verify_phone_number.html", context=context
    )


def verify_email(request):
    token = request.GET.get("token")
    inputed_email = None
    form = forms.NewCustomerVerifyEmailForm()

    # check check outsie if there is token
    if token:
        decoded_token = decode_token(token=token)
        if not decoded_token.get("email"):
            # token has expired
            messages.error(request, "OTP Token Expired, please resend otp")
            return redirect("dashboard:onboarding-verify-email")

        inputed_email = decoded_token.get("email")

    if request.method == "POST":
        # check if there is a token verify otp
        if token:
            decoded_token = decode_token(token=token)
            if not decoded_token.get("email"):
                # token has expired
                messages.error(request, "Token Expired, please resend token")
                return redirect("dashboard:onboarding-verify-email")

            inputed_email = decoded_token.get("email")
            saved_otp = decoded_token.get("otp")
            entered_otp = request.POST.get("otp")

            if saved_otp == entered_otp:
                messages.success(request, "OTP verified successfully")
                cache.set("_customer_email", inputed_email, 60 * 60 * 24)
                return redirect("dashboard:onboarding-new-customer-kyc")
            else:
                messages.error(request, "Invlaid OTP")

        else:
            form = forms.NewCustomerVerifyEmailForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data["email"]
                generated_otp = generate_otp(6)
                token = create_token(email=str(email), password="", otp=generated_otp)

                # send an sms with the OTP
                body = """
Dear Customer, Your OTP Code for Account Onboarding is {otp}.
Please do not share this code with anyone.

Thank you.
""".format(
                    otp=generated_otp
                )

                # send email
                payload = {
                    "emailType": "account_verification_otp",
                    "body": body,
                    "otp": generated_otp,
                    "subject": "Account Verification OTP",
                }
                generic_send_mail.delay(
                    recipient=email,
                    title="Account Verification",
                    payload=payload,
                )

                # prepare and send OTP to the phone number
                messages.success(request, "OTP sent to customer's email address")
                return redirect(
                    f"{reverse('dashboard:onboarding-verify-email')}?token={token}"
                )

    context = {"form": form, "token": token, "inputed_email": inputed_email}
    return render(request, "customer_onboarding/verify_email.html", context=context)


@transaction.atomic
def customer_onboarding_kyc(request):
    token = request.GET.get("token")
    inputed_email = None
    form = forms.SignUpNewCustomerForm()

    if form.is_valid():
        first_name = form.cleaned_data["first_name"]
        last_name = form.cleaned_data["last_name"]
        nationality = form.cleaned_data["nationality"]
        gender = form.cleaned_data["gender"]
        date_of_birth = form.cleaned_data["date_of_birth"]
        profile_picture = form.cleaned_data["profile_picture"]
        id_front = form.cleaned_data["id_front"]
        id_back = form.cleaned_data["id_back"]
        id_number = form.cleaned_data["id_number"]
        date_of_issuance = form.cleaned_data["date_of_issuance"]
        date_of_expiry = form.cleaned_data["date_of_expiry"]
        place_of_issuance = form.cleaned_data["place_of_issuance"]
        phone_number = cache.get("_customer_onboarding_phone_number")
        email = cache.get("_customer_email")

        # create user_account and customer profile
        password = generate_reference_id(length=10)
        pin = generate_otp(length=6)
        user_account = CustomUser.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            secure_pin=make_password("123456"),
            phone_number=phone_number,
        )
        user_account.set_password(password)
        user_account.secure_pin = make_password(pin)
        user_account.save()

        customer_profile = CustomerProfile.objects.create(
            user_account=user_account,
            national_id=id_number,
            nationality=nationality,
            gender=gender,
            date_of_birth=date_of_birth,
            profile_picture=profile_picture,
            id_front=id_front,
            id_back=id_back,
            place_of_issue=place_of_issuance,
            date_of_issuance=date_of_issuance,
            date_of_expiry=date_of_expiry,
        )

    # create and send password and mobile pin to the user via email
    context = {"form": form, "token": token, "inputed_email": inputed_email}
    return render(request, "customer_onboarding/cutomer_kyc.html", context=context)
