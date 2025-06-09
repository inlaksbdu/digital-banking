from django.http.request import HttpRequest
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

# from accounts.models import CustomUser


def is_staff_user(f, *args, **kwargs):
    @wraps(f)
    def inner(request: HttpRequest, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return f(request, *args, **kwargs)
            messages.error(
                request,
                "Sorry, You don't have permission to access this page.",
            )
        else:
            messages.error(request, "Sorry you need to log in to perform this action.")
        return redirect("/")

    return inner


def edit_permission(view_perm, edit_perm):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # user_permissions = request.user.get_user_permissions()
            if not (
                request.user.has_perm(view_perm) and request.user.has_perm(edit_perm)
            ):
                messages.error(
                    request, "You do not have permission to access this page."
                )

                # Redirect back to the previous page
                return redirect(request.META.get("HTTP_REFERER"))
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def view_permission(perm):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            _ = request.user.get_user_permissions()
            if not request.user.has_perm(perm):
                messages.error(
                    request, "You do not have permission to access this page."
                )

                # Redirect back to the previous page
                return redirect(request.META.get("HTTP_REFERER"))
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def suerpuser_access(f, *args, **kwargs):
    @wraps(f)
    def inner(request: HttpRequest, *args, **kwargs):
        if request.user.is_superuser:
            return f(request, *args, **kwargs)
        else:
            messages.error(
                request,
                "Sorry, You don't have permission to access this page.",
            )
        return redirect("/staff-dashboard")

    return inner
