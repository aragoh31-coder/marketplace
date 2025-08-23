import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic import FormView

from apps.security.forms import SecureLoginForm, SecureRegistrationForm
from apps.security.models import log_security_event
from wallets.models import WalletAddress

logger = logging.getLogger(__name__)


@method_decorator([csrf_protect, never_cache], name="dispatch")
class SecureLoginView(FormView):
    """Enhanced login view with security features"""

    template_name = "accounts/login.html"
    form_class = SecureLoginForm
    success_url = reverse_lazy("core:home")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get("password")

        user = authenticate(self.request, username=username, password=password)

        if user:
            log_security_event(
                user,
                "login",
                {
                    "session_id": self.get_session_id(),
                    "user_agent": self.request.META.get("HTTP_USER_AGENT", ""),
                    "timestamp": timezone.now(),
                },
            )

            log_security_event(
                user,
                "login_attempt",
                {
                    "success": True,
                    "session_id": self.get_session_id(),
                    "user_agent": self.request.META.get("HTTP_USER_AGENT", ""),
                },
                risk_score=0,
            )

            # Store session info instead of IP
            self.request.session["login_session_id"] = self.get_session_id()
            self.request.session["login_time"] = timezone.now().timestamp()

            login(self.request, user)

            if user.pgp_fingerprint and user.pgp_login_enabled:
                return redirect("accounts:pgp_verify")

            messages.success(self.request, f"Welcome back, {user.username}!")
            return redirect(self.get_success_url())

        else:
            log_security_event(
                None,
                "login_failed",
                {
                    "username": username,
                    "session_id": self.get_session_id(),
                    "user_agent": self.request.META.get("HTTP_USER_AGENT", ""),
                },
                risk_score=20,
            )

            messages.error(self.request, "Invalid username or password.")
            return self.form_invalid(form)

    def get_session_id(self):
        """Get or create session ID for tracking (Tor-compatible)"""
        if not hasattr(self.request, 'session') or not self.request.session.session_key:
            self.request.session.create()
        return self.request.session.session_key
    
    def get_client_ip(self):
        """DEPRECATED: Returns generic value for Tor compatibility"""
        return "tor-user"


@method_decorator([csrf_protect, never_cache], name="dispatch")
class SecureRegistrationView(FormView):
    """Enhanced registration view with security features"""

    template_name = "accounts/register.html"
    form_class = SecureRegistrationForm
    success_url = reverse_lazy("accounts:login")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        user = form.save()

        log_security_event(
            user,
            "registration",
            {
                "session_id": self.get_session_id(),
                "user_agent": self.request.META.get("HTTP_USER_AGENT", ""),
                "email": user.email,
            },
            risk_score=10,
        )

        from wallets.models import Wallet

        Wallet.objects.create(user=user)

        messages.success(self.request, "Registration successful! You can now log in to your account.")

        return super().form_valid(form)

    def get_session_id(self):
        """Get or create session ID for tracking (Tor-compatible)"""
        if not hasattr(self.request, 'session') or not self.request.session.session_key:
            self.request.session.create()
        return self.request.session.session_key
    
    def get_client_ip(self):
        """DEPRECATED: Returns generic value for Tor compatibility"""
        return "tor-user"
