import time
import hashlib
import random
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.contrib.auth.models import User


class NoJSCaptchaMixin:
    """Mixin for forms that need NoJS CAPTCHA protection"""
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        self.fields['website'] = forms.CharField(
            required=False,
            widget=forms.HiddenInput(),
            label='Website (leave blank)'
        )
        self.fields['email_address'] = forms.CharField(
            required=False,
            widget=forms.HiddenInput(),
            label='Email Address (leave blank)'
        )
        
        self.fields['form_timestamp'] = forms.CharField(
            widget=forms.HiddenInput(),
            required=False
        )
        self.fields['form_timestamp'].initial = time.time()
        
        challenge = self._generate_math_challenge()
        self.fields['math_challenge'] = forms.CharField(
            label=f'Security Question: {challenge["question"]}',
            max_length=10,
            required=True,
            help_text='Please solve this simple math problem'
        )
        
        if self.request and hasattr(self.request, 'session'):
            self.request.session['math_answer'] = challenge['answer']
            self.request.session['captcha_generated'] = time.time()
        
        self.fields['form_hash'] = forms.CharField(
            widget=forms.HiddenInput(),
            required=False
        )
        self.fields['form_hash'].initial = self._generate_form_hash()
    
    def _generate_math_challenge(self):
        """Generate a simple math challenge"""
        try:
            num1 = random.randint(1, 10)
            num2 = random.randint(1, 10)
            operation = random.choice(['+', '-'])
            
            if operation == '+':
                answer = num1 + num2
                question = f"{num1} + {num2}"
            else:
                answer = num1 - num2
                question = f"{num1} - {num2}"
            
            return {
                'question': question,
                'answer': str(answer)
            }
        except:
            return {
                'question': '2 + 2',
                'answer': '4'
            }
    
    def _generate_form_hash(self):
        """Generate form hash for validation"""
        try:
            timestamp = str(int(time.time()))
            user_agent = ''
            if self.request:
                user_agent = self.request.META.get('HTTP_USER_AGENT', '')
            
            hash_string = f"{timestamp}:{user_agent}"
            form_hash = hashlib.sha256(hash_string.encode()).hexdigest()[:16]
            
            if self.request and hasattr(self.request, 'session'):
                self.request.session['form_hash'] = form_hash
            
            return form_hash
        except:
            return 'default_hash'
    
    def get_client_ip(self, request):
        """Get client IP address"""
        if not request:
            return '127.0.0.1'
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip
    
    def clean_website(self):
        """Honeypot field should be empty"""
        website = self.cleaned_data.get('website')
        if website:
            raise ValidationError('Bot detected')
        return website
    
    def clean_email_address(self):
        """Honeypot field should be empty"""
        email_address = self.cleaned_data.get('email_address')
        if email_address:
            raise ValidationError('Bot detected')
        return email_address
    
    def clean_form_timestamp(self):
        """Validate form submission timing"""
        timestamp = self.cleaned_data.get('form_timestamp')
        if not timestamp:
            raise ValidationError('Invalid form submission')
        
        try:
            form_time = float(timestamp)
            current_time = time.time()
            
            if current_time - form_time < 3:
                raise ValidationError('Form submitted too quickly')
            
            if current_time - form_time > 1800:
                raise ValidationError('Form expired')
                
        except (ValueError, TypeError):
            raise ValidationError('Invalid timestamp')
        
        return timestamp
    
    def clean_math_challenge(self):
        """Validate math challenge answer"""
        answer = self.cleaned_data.get('math_challenge')
        
        if not self.request or not hasattr(self.request, 'session'):
            raise ValidationError('Session required')
        
        expected_answer = self.request.session.get('math_answer')
        captcha_time = self.request.session.get('captcha_generated')
        
        if not expected_answer:
            raise ValidationError('Challenge expired')
        
        if captcha_time and time.time() - captcha_time > 600:  # 10 minutes
            raise ValidationError('Challenge expired')
        
        if str(answer).strip() != str(expected_answer).strip():
            raise ValidationError('Incorrect answer')
        
        if 'math_answer' in self.request.session:
            del self.request.session['math_answer']
        if 'captcha_generated' in self.request.session:
            del self.request.session['captcha_generated']
        
        return answer
    
    def clean_form_hash(self):
        """Validate form hash"""
        form_hash = self.cleaned_data.get('form_hash')
        
        if not self.request or not hasattr(self.request, 'session'):
            return form_hash
        
        expected_hash = self.request.session.get('form_hash')
        if expected_hash and form_hash != expected_hash:
            raise ValidationError('Invalid form hash')
        
        return form_hash
    
    def clean(self):
        """Additional validation and rate limiting"""
        cleaned_data = super().clean()
        
        if self.request:
            if not self._check_rate_limit():
                raise ValidationError('Too many attempts. Please try again later.')
        
        return cleaned_data
    
    def _check_rate_limit(self):
        """Check rate limiting"""
        if not self.request:
            return True
        
        try:
            current_time = time.time()
            ip = self.get_client_ip(self.request)
            cache_key = f"form_submissions:{ip}"
            
            submissions = cache.get(cache_key, [])
            submissions = [ts for ts in submissions if current_time - ts < 3600]
            
            if len(submissions) >= 10:
                return False
            
            submissions.append(current_time)
            cache.set(cache_key, submissions, 3600)
            
            return True
        except:
            return True


class SecureLoginForm(NoJSCaptchaMixin, AuthenticationForm):
    """Enhanced login form with security features"""
    
    def __init__(self, request=None, *args, **kwargs):
        kwargs['request'] = request
        super().__init__(request, *args, **kwargs)
        
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.request:
            if not self._check_login_rate_limit():
                raise ValidationError('Too many login attempts. Please try again later.')
        
        return cleaned_data
    
    def _check_login_rate_limit(self):
        """Check login-specific rate limiting"""
        if not self.request:
            return True
        
        try:
            current_time = time.time()
            ip = self.get_client_ip(self.request)
            username = self.cleaned_data.get('username', '')
            
            ip_key = f"login_attempts_ip:{ip}"
            ip_attempts = cache.get(ip_key, [])
            ip_attempts = [ts for ts in ip_attempts if current_time - ts < 3600]
            
            if len(ip_attempts) >= 20:  # 20 attempts per hour per IP
                return False
            
            user_key = f"login_attempts_user:{username}"
            user_attempts = cache.get(user_key, [])
            user_attempts = [ts for ts in user_attempts if current_time - ts < 3600]
            
            if len(user_attempts) >= 5:  # 5 attempts per hour per user
                return False
            
            ip_attempts.append(current_time)
            user_attempts.append(current_time)
            cache.set(ip_key, ip_attempts, 3600)
            cache.set(user_key, user_attempts, 3600)
            
            return True
        except:
            return True


class SecureRegistrationForm(NoJSCaptchaMixin, UserCreationForm):
    """Enhanced registration form with security features"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
    
    def clean_email(self):
        """Ensure email is unique"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Email address already in use.')
        return email
    
    def clean(self):
        """Additional validation and rate limiting"""
        cleaned_data = super().clean()
        
        if self.request:
            if not self._check_registration_rate_limit():
                raise ValidationError('Too many registration attempts. Please try again later.')
        
        return cleaned_data
    
    def _check_registration_rate_limit(self):
        """Check registration-specific rate limiting"""
        if not self.request:
            return True
        
        try:
            current_time = time.time()
            ip = self.get_client_ip(self.request)
            
            cache_key = f"registration_attempts:{ip}"
            attempts = cache.get(cache_key, [])
            attempts = [ts for ts in attempts if current_time - ts < 3600]
            
            if len(attempts) >= 3:  # 3 registrations per hour per IP
                return False
            
            attempts.append(current_time)
            cache.set(cache_key, attempts, 3600)
            
            return True
        except:
            return True
    
    def save(self, commit=True):
        """Save user with email"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


def captcha_context(request):
    """Context processor for CAPTCHA data"""
    return {
        'captcha_enabled': True,
        'security_enabled': True
    }
