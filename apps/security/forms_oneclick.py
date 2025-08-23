"""
Updated security forms using One-Click CAPTCHA
"""
import hashlib
import random
import time
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone

from captcha.forms import OneClickCaptchaMixin

User = get_user_model()


class NoJSOneClickCaptchaMixin(OneClickCaptchaMixin):
    """Enhanced mixin combining One-Click CAPTCHA with honeypot fields"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Honeypot fields (should remain empty)
        self.fields["website"] = forms.CharField(
            required=False, widget=forms.HiddenInput(), label="Website (leave blank)"
        )
        self.fields["email_address"] = forms.CharField(
            required=False, widget=forms.HiddenInput(), label="Email Address (leave blank)"
        )
        
        # Timestamp for form age validation
        self.fields["form_timestamp"] = forms.CharField(widget=forms.HiddenInput(), required=False)
        self.fields["form_timestamp"].initial = time.time()
        
        # Form hash for integrity
        self.fields["form_hash"] = forms.CharField(widget=forms.HiddenInput(), required=False)
        self.fields["form_hash"].initial = self._generate_form_hash()
    
    def _generate_form_hash(self):
        """Generate a unique hash for form integrity"""
        data = f"{time.time()}-{id(self)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _check_rate_limit(self, limit_key, max_attempts, time_window):
        """Check rate limiting"""
        if not self.request:
            return True
            
        # Get session ID for rate limiting (Tor-safe)
        session_id = getattr(self.request.session, 'session_key', 'anonymous')
        if not session_id:
            session_id = 'anonymous'
        
        cache_key = f"form_attempt:{limit_key}:{session_id}"
        attempts = cache.get(cache_key, 0)
        
        if attempts >= max_attempts:
            return False
            
        cache.set(cache_key, attempts + 1, time_window)
        return True
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Check honeypot fields
        if cleaned_data.get("website") or cleaned_data.get("email_address"):
            # Bot detected - fail silently
            raise ValidationError("")
        
        # Check form age (minimum 3 seconds)
        timestamp = cleaned_data.get("form_timestamp")
        if timestamp:
            try:
                form_age = time.time() - float(timestamp)
                if form_age < 3:
                    raise ValidationError("Please take your time to complete the form")
                if form_age > 3600:  # 1 hour
                    raise ValidationError("Form has expired. Please refresh and try again")
            except (ValueError, TypeError):
                raise ValidationError("Invalid form submission")
        
        return cleaned_data


class SecureLoginFormOneClick(NoJSOneClickCaptchaMixin, AuthenticationForm):
    """Login form with One-Click CAPTCHA"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update field order for better UX
        self.order_fields(['username', 'password'])
    
    def clean(self):
        # Check login rate limit
        username = self.cleaned_data.get("username", "")
        if username and not self._check_login_rate_limit(username):
            raise ValidationError(
                "Too many login attempts. Please try again later.",
                code="rate_limit_exceeded"
            )
        
        return super().clean()
    
    def _check_login_rate_limit(self, username):
        """Check login-specific rate limits"""
        # Per-username limit: 5 attempts per hour
        if not self._check_rate_limit(f"login:user:{username}", 5, 3600):
            return False
            
        # Per-session limit: 20 attempts per hour  
        if not self._check_rate_limit("login:session", 20, 3600):
            return False
            
        return True
    
    def get_captcha_html(self):
        """Get the HTML for the One-Click CAPTCHA"""
        return self.captcha_html()


class SecureRegistrationFormOneClick(NoJSOneClickCaptchaMixin, UserCreationForm):
    """Registration form with One-Click CAPTCHA"""
    
    class Meta:
        model = User
        fields = ("username", "password1", "password2")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add placeholders and help text
        self.fields['username'].help_text = "Letters, digits and @/./+/-/_ only"
        self.fields['password1'].help_text = "At least 8 characters"
    
    def clean(self):
        # Check registration rate limit
        if not self._check_registration_rate_limit():
            raise ValidationError(
                "Registration limit exceeded. Please try again later.",
                code="rate_limit_exceeded"
            )
        
        return super().clean()
    
    def _check_registration_rate_limit(self):
        """Check registration-specific rate limits"""
        # Per-session limit: 3 registrations per hour
        if not self._check_rate_limit("registration:session", 3, 3600):
            return False
            
        return True
    
    def save(self, commit=True):
        user = super().save(commit=commit)
        return user
    
    def get_captcha_html(self):
        """Get the HTML for the One-Click CAPTCHA"""
        return self.captcha_html()


class SecurityChallengeForm(forms.Form):
    """Form for security challenges with dual CAPTCHA (math + one-click)"""
    
    # Math challenge field
    math_answer = forms.CharField(
        label="Math Challenge",
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter answer',
            'autocomplete': 'off'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Generate math challenge
        if self.request:
            challenge = self._generate_math_challenge()
            self.fields['math_answer'].label = f"What is {challenge['question']}?"
            self.request.session['security_math_answer'] = challenge['answer']
            self.request.session['security_challenge_time'] = time.time()
    
    def _generate_math_challenge(self):
        """Generate a simple math problem"""
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        operations = [
            ('+', lambda x, y: x + y),
            ('-', lambda x, y: x - y if x > y else y - x),
        ]
        op_symbol, op_func = random.choice(operations)
        
        if op_symbol == '-' and b > a:
            a, b = b, a
            
        return {
            'question': f"{a} {op_symbol} {b}",
            'answer': str(op_func(a, b))
        }
    
    def clean_math_answer(self):
        """Validate math answer"""
        answer = self.cleaned_data.get('math_answer', '').strip()
        
        if not self.request:
            raise ValidationError("Invalid request")
            
        expected = self.request.session.get('security_math_answer')
        challenge_time = self.request.session.get('security_challenge_time', 0)
        
        # Check timeout (5 minutes)
        if time.time() - challenge_time > 300:
            raise ValidationError("Challenge expired. Please try again.")
            
        if answer != expected:
            raise ValidationError("Incorrect answer. Please try again.")
            
        # Clear the challenge
        self.request.session.pop('security_math_answer', None)
        self.request.session.pop('security_challenge_time', None)
        
        return answer


# Create form with both math and one-click CAPTCHA
class DualCaptchaSecurityForm(OneClickCaptchaMixin, SecurityChallengeForm):
    """Security form with both math challenge and One-Click CAPTCHA"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure proper field ordering
        self.order_fields(['math_answer'])
    
    def clean(self):
        """Validate both CAPTCHAs"""
        cleaned_data = super().clean()
        # Both validations will run from parent classes
        return cleaned_data
    
    def get_captcha_html(self):
        """Get combined HTML for both CAPTCHAs"""
        math_html = f'''
        <div class="math-captcha">
            <label for="id_math_answer">{self.fields['math_answer'].label}</label>
            <input type="text" name="math_answer" id="id_math_answer" 
                   placeholder="Enter answer" autocomplete="off" required>
        </div>
        '''
        
        oneclick_html = self.captcha_html()
        
        return f'''
        <div class="dual-captcha">
            <h4>🔐 Security Verification</h4>
            <p>Please complete both challenges:</p>
            
            <div class="captcha-section">
                <h5>1. Math Challenge</h5>
                {math_html}
            </div>
            
            <div class="captcha-section">
                <h5>2. Visual Challenge</h5>
                {oneclick_html}
            </div>
        </div>
        '''