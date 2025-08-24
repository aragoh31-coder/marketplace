from django import forms
from .models import Order


class CreateOrderForm(forms.Form):
    """Form for creating an order from cart"""
    CURRENCY_CHOICES = [
        ('BTC', 'Bitcoin (BTC)'),
        ('XMR', 'Monero (XMR)'),
    ]
    
    currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        widget=forms.RadioSelect,
        initial='BTC'
    )
    
    shipping_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Enter encrypted shipping address (PGP recommended)',
            'class': 'form-control'
        }),
        required=False,
        help_text='Encrypt sensitive information with vendor\'s PGP key'
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        label='I understand that all sales are final once funds are released'
    )


class DisputeForm(forms.Form):
    """Form for raising a dispute"""
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 8,
            'placeholder': 'Describe the issue in detail...',
            'class': 'form-control'
        }),
        required=True,
        min_length=50,
        help_text='Minimum 50 characters. Be specific about the problem.'
    )
    
    
class DisputeResponseForm(forms.Form):
    """Form for responding to a dispute"""
    response = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 6,
            'placeholder': 'Your response to the dispute...',
            'class': 'form-control'
        }),
        required=True
    )
    
    
class DisputeMessageForm(forms.Form):
    """Form for adding messages to dispute chat"""
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Add a message to the dispute...',
            'class': 'form-control'
        }),
        required=True
    )