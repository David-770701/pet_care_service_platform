from functools import wraps
from typing import Optional

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(role: str, message: Optional[str] = None, redirect_url: str = 'home'):
    """Require login plus one application role."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if getattr(request.user, 'role', None) != role:
                if message:
                    messages.error(request, message)
                return redirect(redirect_url)
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
