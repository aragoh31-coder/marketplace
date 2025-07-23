
<create_file path="/home/ubuntu/repos/marketplace/apps/security/__init__.py"/>

<create_file path="/home/ubuntu/repos/marketplace/apps/security/forms.py">
import time
import hashlib
import random
from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class NoJSCaptchaMixin(forms.Form):
    """
    No-JavaScript CAPTCHA protection using:
    1. Honeypot fields (hidden from humans, bots fill them)
    2. Timestamp validation (prevents instant form submissions)
    3. Simple math challenges
    4. Form hash validation
    """
    
    website = forms.CharField(
        required=False,
        label='Website (leave blank)',
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'tabindex': '-1',
            'aria-hidden': 'true',
            'style': 'position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden;'
        })
    )
    
    email_address = forms.EmailField(
        required=False,
        label='Email Address (leave blank)',
        widget=forms.EmailInput(attrs={
            'autocomplete': 'off',
            'tabindex': '-1',
            'aria-hidden': 'true',
            'style': 'position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden;'
        })
    )
    
    form_timestamp = forms.FloatField(widget=forms.HiddenInput)
    
    math_challenge = forms.CharField(
        label='Security Check',
        help_text='Please solve this simple math problem to verify you are human',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter the answer',
            'autocomplete': 'off'
        })
    )
    
    form_hash = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        self.fields['form_timestamp'].initial = time.time()
        
        self._generate_math_challenge()
        
        self._generate_form_hash()

    def _generate_math_challenge(self):
        """Generate a simple math problem"""
        if self.request and hasattr(self.request, 'session'):
            num1 = random.randint(1, 10)
            num2 = random.randint(1, 10)
            operation = random.choice(['+', '-'])
            
            if operation == '+':
                answer = num1 + num2
                question = f"What is {num1} + {num2}?"
            else:
                if num1 < num2:
                    num1, num2 = num2, num1
                answer = num1 - num2
                question = f"What is {num1} - {num2}?"
            
            self.request.session['captcha_answer'] = answer
            self.request.session['captcha_generated'] = time.time()
            
            self.fields['math_challenge'].label = f"Security Check: {question}"

    def _generate_form_hash(self):
        """Generate form hash for replay protection"""
        if self.request:
            ip = self.get_client_ip()
            timestamp = str(int(time.time()))
            secret = getattr(settings, 'SECRET_KEY', 'default-secret')
            
            hash_string = f"{ip}-{timestamp}-{secret}"
            form_hash = hashlib.sha256(hash_string.encode()).hexdigest()[:16]
            
            self.fields['form_hash'].initial = form_hash
            
            if self.request and hasattr(self.request, 'session'):
                self.request.session['form_hash'] = form_hash

    def get_client_ip(self):
        """Get client IP address"""
        if not self.request:
            return '127.0.0.1'
        
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip

    def clean_website(self):
        """Honeypot validation - should be empty"""
        data = self.cleaned_data.get('website', '').strip()
        if data:
            raise ValidationError("Bot detected (honeypot field filled)")
        return data

    def clean_email_address(self):
        """Honeypot validation - should be empty"""
        data = self.cleaned_data.get('email_address', '').strip()
        if data:
            raise ValidationError("Bot detected (honeypot field filled)")
        return data

    def clean_form_timestamp(self):
        """Validate form submission timing"""
        timestamp = self.cleaned_data.get('form_timestamp')
        if not timestamp:
            raise ValidationError("Invalid form timestamp")
        
        current_time = time.time()
        time_diff = current_time - timestamp
        
        if time_diff < 3:
            raise ValidationError(
                "Form submitted too quickly. Please take time to read and fill the form."
            )
        
        if time_diff > 3600:
            raise ValidationError(
                "Form session expired. Please refresh the page and try again."
            )
        
        return timestamp

    def clean_math_challenge(self):
        """Validate math challenge answer"""
        user_answer = self.cleaned_data.get('math_challenge', '').strip()
        
        if not user_answer:
            raise ValidationError("Please solve the math problem")
        
        try:
            user_answer = int(user_answer)
        except ValueError:
            raise ValidationError("Please enter a number")
        
        if not self.request or not hasattr(self.request, 'session'):
            raise ValidationError("Session error - please try again")
        
        correct_answer = self.request.session.get('captcha_answer')
        if correct_answer is None:
            raise ValidationError("CAPTCHA session expired - please refresh and try again")
        
        if user_answer != correct_answer:
            self._generate_math_challenge()
            raise ValidationError("Incorrect answer. Please try the new problem above.")
        
        return user_answer

    def clean_form_hash(self):
        """Validate form hash to prevent replay attacks"""
        submitted_hash = self.cleaned_data.get('form_hash')
        
        if not self.request or not hasattr(self.request, 'session'):
            return submitted_hash
        
        session_hash = self.request.session.get('form_hash')
        
        if not session_hash or submitted_hash != session_hash:
            raise ValidationError("Invalid form submission")
        
        if 'form_hash' in self.request.session:
            del self.request.session['form_hash']
        
        return submitted_hash

    def clean(self):
        """Additional cross-field validation"""
        cleaned_data = super().clean()
        
        if self.request and hasattr(self, '_check_rate_limit'):
            self._check_rate_limit()
        
        return cleaned_data

    def _check_rate_limit(self):
        """Simple rate limiting based on IP"""
        if not self.request:
            return
        
        ip = self.get_client_ip()
        session_key = f"form_submissions_{ip}"
        
        if hasattr(self.request, 'session'):
            submissions = self.request.session.get(session_key, [])
            current_time = time.time()
            
            submissions = [ts for ts in submissions if current_time - ts < 3600]
            
            if len(submissions) >= 10:
                raise ValidationError("Too many form submissions. Please wait before trying again.")
            
            submissions.append(current_time)
            self.request.session[session_key] = submissions


from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class SecureLoginForm(NoJSCaptchaMixin, AuthenticationForm):
    """Enhanced login form with anti-bot protection"""
    
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        
        self.fields['username'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Username',
            'autocomplete': 'username'
        })
        
        self.fields['password'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        })

    def clean(self):
        cleaned_data = super().clean()
        
        if self.request:
            self._check_login_rate_limit()
        
        return cleaned_data

    def _check_login_rate_limit(self):
        """Enhanced rate limiting for login attempts"""
        ip = self.get_client_ip()
        username = self.cleaned_data.get('username', '')
        
        ip_key = f"login_attempts_ip_{ip}"
        user_key = f"login_attempts_user_{username}"
        
        if hasattr(self.request, 'session'):
            current_time = time.time()
            
            ip_attempts = self.request.session.get(ip_key, [])
            ip_attempts = [ts for ts in ip_attempts if current_time - ts < 3600]
            
            if len(ip_attempts) >= 20:
                raise ValidationError("Too many login attempts from this location. Please wait an hour.")
            
            user_attempts = self.request.session.get(user_key, [])
            user_attempts = [ts for ts in user_attempts if current_time - ts < 1800]
            
            if len(user_attempts) >= 5:
                raise ValidationError(f"Too many login attempts for {username}. Please wait 30 minutes.")
            
            ip_attempts.append(current_time)
            user_attempts.append(current_time)
            
            self.request.session[ip_key] = ip_attempts
            self.request.session[user_key] = user_attempts


class SecureRegistrationForm(NoJSCaptchaMixin, UserCreationForm):
    """Enhanced registration form with anti-bot protection"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Email address',
            'autocomplete': 'email'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['username'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Username',
            'autocomplete': 'username'
        })
        
        self.fields['password1'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Password',
            'autocomplete': 'new-password'
        })
        
        self.fields['password2'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password'
        })

    def clean_email(self):
        """Validate email is unique"""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        """Enhanced validation for registration"""
        cleaned_data = super().clean()
        
        if self.request:
            self._check_registration_rate_limit()
        
        return cleaned_data

    def _check_registration_rate_limit(self):
        """Rate limiting for registration attempts"""
        ip = self.get_client_ip()
        session_key = f"registration_attempts_{ip}"
        
        if hasattr(self.request, 'session'):
            current_time = time.time()
            attempts = self.request.session.get(session_key, [])
            
            attempts = [ts for ts in attempts if current_time - ts < 86400]
            
            if len(attempts) >= 3:
                raise ValidationError(
                    "Maximum registrations reached for this location. Please try again tomorrow."
                )
            
            attempts.append(current_time)
            self.request.session[session_key] = attempts

    def save(self, commit=True):
        """Save user with email"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


def captcha_context(request):
    """Add CAPTCHA-related context to templates"""
    return {
        'captcha_enabled': True,
        'show_security_notice': True,
    }
