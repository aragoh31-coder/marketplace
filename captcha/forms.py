from django import forms
from django.core.exceptions import ValidationError
from .utils.captcha_generator import OneClickCaptcha


class OneClickCaptchaMixin:
    """
    Mixin to add One-Click CAPTCHA to any Django form.
    No JavaScript required - uses image input type for click coordinates.
    """
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Add hidden fields to store click coordinates
        self.fields['captcha_x'] = forms.IntegerField(
            required=False,
            widget=forms.HiddenInput()
        )
        self.fields['captcha_y'] = forms.IntegerField(
            required=False,
            widget=forms.HiddenInput()
        )
        self.fields['captcha_token'] = forms.CharField(
            required=False,
            widget=forms.HiddenInput()
        )
        
        if self.request and hasattr(self.request, 'session'):
            # Generate a new token for this form instance
            import hashlib
            import time
            token_data = f"{time.time()}-{id(self)}-{self.request.session.session_key or 'anon'}"
            token = hashlib.sha256(token_data.encode()).hexdigest()[:16]
            
            # Store it in session so the image generator can find it
            self.request.session['current_captcha_token'] = token
            self.request.session.modified = True
            
            if 'captcha_token' in self.fields:
                self.fields['captcha_token'].initial = token
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Debug logging
        import logging
        logger = logging.getLogger('captcha')
        logger.info(f"CAPTCHA Form data: {dict(self.data)}")
        logger.info(f"CAPTCHA Cleaned data: {cleaned_data}")
        
        if self.request:
            # Get click coordinates
            captcha_x = cleaned_data.get('captcha_x')
            captcha_y = cleaned_data.get('captcha_y')
            captcha_token = cleaned_data.get('captcha_token')
            
            # Check if this is from an image input (will have .x and .y in POST)
            if 'captcha.x' in self.data and 'captcha.y' in self.data:
                try:
                    captcha_x = int(self.data.get('captcha.x', 0))
                    captcha_y = int(self.data.get('captcha.y', 0))
                except (TypeError, ValueError):
                    captcha_x = captcha_y = None
            
            # Validate captcha
            if captcha_x is not None and captcha_y is not None:
                captcha_service = OneClickCaptcha()
                if not captcha_service.validate(self.request, captcha_x, captcha_y, captcha_token):
                    raise ValidationError(
                        'Invalid CAPTCHA. Please click on the shape that looks different from the others.',
                        code='invalid_captcha'
                    )
            else:
                raise ValidationError(
                    'Please complete the CAPTCHA by clicking on the shape that looks different.',
                    code='missing_captcha'
                )
        
        return cleaned_data
    
    def captcha_html(self):
        """Return HTML for the CAPTCHA widget."""
        token = self.fields['captcha_token'].initial or ''
        return f'''
        <div class="captcha-widget">
            <p class="captcha-instruction">
                🔐 Click the shape that looks different from the others:
            </p>
            <input type="image" 
                   name="captcha" 
                   src="/captcha/generate/" 
                   alt="Click the unique shape"
                   class="captcha-image"
                   style="border: 1px solid #ddd; border-radius: 4px; cursor: pointer;">
            <input type="hidden" name="captcha_token" value="{token}">
            <p class="captcha-help">
                <small>Look for: Pac-Man, pizza slice, star, donut, crescent, or diamond among circles.</small>
            </p>
        </div>
        '''


class OneClickCaptchaField(forms.Field):
    """
    A custom form field for the One-Click CAPTCHA.
    Can be added to any form as a regular field.
    """
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        kwargs['required'] = True
        kwargs['label'] = 'Security Check'
        super().__init__(*args, **kwargs)
    
    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs['class'] = 'captcha-field'
        return attrs
    
    def validate(self, value):
        """Validate is handled in the form's clean method."""
        pass