from django import forms
from django.contrib.auth.forms import AuthenticationForm


class SecondaryAuthForm(forms.Form):
    """Secondary password authentication form for admin panel"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter secondary password',
            'autocomplete': 'off'
        }),
        label='Secondary Password',
        help_text='Enter the admin panel secondary password'
    )


class AdminPGPChallengeForm(forms.Form):
    """PGP challenge verification form for admin panel"""
    signed_challenge = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Paste your signed PGP challenge response here...',
            'style': 'font-family: monospace; font-size: 12px;'
        }),
        label='Signed Challenge Response',
        help_text='Sign the challenge with your PGP key and paste the signed message here'
    )


class AdminLoginForm(AuthenticationForm):
    """Enhanced admin login form"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Admin Username',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        })
    )
