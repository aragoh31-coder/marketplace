from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import password_validation
from .models import User
import gnupg


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['default_currency', 'default_shipping_country']
        widgets = {
            'default_currency': forms.Select(attrs={'class': 'form-control'}),
            'default_shipping_country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., United States, Germany, etc.'
            }),
        }


class PGPKeyForm(forms.Form):
    pgp_public_key = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': '-----BEGIN PGP PUBLIC KEY BLOCK-----\n...\n-----END PGP PUBLIC KEY BLOCK-----'
        }),
        required=False
    )
    enable_pgp_login = forms.BooleanField(
        required=False,
        label="Enable PGP-based login challenge",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_pgp_public_key(self):
        key = self.cleaned_data.get('pgp_public_key')
        if key:
            if not ('-----BEGIN PGP PUBLIC KEY BLOCK-----' in key and '-----END PGP PUBLIC KEY BLOCK-----' in key):
                raise forms.ValidationError("Invalid PGP public key format")
            
            from .pgp_service import PGPService
            pgp_service = PGPService()
            import_result = pgp_service.import_public_key(key)
            
            if not import_result['success']:
                raise forms.ValidationError(f"Invalid PGP key: {import_result['error']}")
            
            self.fingerprint = import_result['fingerprint']
            self.key_info = pgp_service.get_key_info(import_result['fingerprint'])
        return key


class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current password'
        })
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password'
        })
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )


class DeleteAccountForm(forms.Form):
    confirm_delete = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Type DELETE to confirm'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    
    def clean_confirm_delete(self):
        confirm = self.cleaned_data.get('confirm_delete')
        if confirm != 'DELETE':
            raise forms.ValidationError('Please type DELETE to confirm')
        return confirm
