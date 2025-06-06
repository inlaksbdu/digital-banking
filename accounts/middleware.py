from django.http import HttpRequest
from django.utils import timezone

# import datetime

# from .models import UserAccount


class UserLastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request: HttpRequest):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        if request.user.is_authenticated:
            request.user.last_seen = timezone.now()
            request.user.save()
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
        return response


class CustomCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "*"
        return response
