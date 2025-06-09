from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login  # , logout
from django.contrib import messages
from accounts.models import CustomUser, CustomerProfile
from django.db.models import Q
from django.urls import reverse
from accounts.tasks import generic_send_mail
from helpers.functions import generate_otp
from .tasks import log_action
from helpers.decorator import view_permission, is_staff_user  # edit_permission
from django.http import JsonResponse
from .utils import decode_token, create_token, mask_email

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
            print("=== payload: ", payload)
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

    context = {"customer": customer}
    log_action.delay(
        user_id=request.user.id,
        action=f"View Customer Detail: {customer}",
    )

    return render(
        request,
        "customers/customer_detail.html",
        context=context,
    )
