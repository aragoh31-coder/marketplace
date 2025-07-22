from django import forms
from django.core.exceptions import ValidationError
from .models import Wallet, Transaction


class WithdrawalForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=20, 
        decimal_places=8,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount to withdraw',
            'step': '0.00000001'
        })
    )
    address = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter withdrawal address'
        })
    )
    currency = forms.ChoiceField(
        choices=[('BTC', 'Bitcoin'), ('XMR', 'Monero')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    honeypot_field = forms.CharField(
        required=False, 
        widget=forms.HiddenInput(),
        label=''
    )
    
    def clean_honeypot_field(self):
        honeypot = self.cleaned_data.get('honeypot_field')
        if honeypot:
            raise ValidationError('Bot detected')
        return honeypot
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError('Amount must be greater than 0')
        return amount


class DepositForm(forms.Form):
    currency = forms.ChoiceField(
        choices=[('BTC', 'Bitcoin'), ('XMR', 'Monero')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    honeypot_field = forms.CharField(
        required=False, 
        widget=forms.HiddenInput(),
        label=''
    )
    
    def clean_honeypot_field(self):
        honeypot = self.cleaned_data.get('honeypot_field')
        if honeypot:
            raise ValidationError('Bot detected')
        return honeypot


class TransactionForm(forms.ModelForm):
    honeypot_field = forms.CharField(
        required=False, 
        widget=forms.HiddenInput(),
        label=''
    )
    
    class Meta:
        model = Transaction
        fields = ['amount', 'transaction_type', 'currency']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_honeypot_field(self):
        honeypot = self.cleaned_data.get('honeypot_field')
        if honeypot:
            raise ValidationError('Bot detected')
        return honeypot
