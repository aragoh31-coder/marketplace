from django import forms
from .models import Vendor
from products.models import Product

class VendorApplicationForm(forms.ModelForm):
    terms_accepted = forms.BooleanField(
        required=True,
        label='I accept the vendor terms and conditions'
    )
    
    class Meta:
        model = Vendor
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Describe your business and what you plan to sell...',
                'class': 'form-input'
            }),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'category', 
            'price_btc', 'price_xmr', 'stock_quantity'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={
                'rows': 10,
                'class': 'form-input'
            }),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'price_btc': forms.NumberInput(attrs={
                'step': '0.00000001',
                'min': '0',
                'class': 'form-input',
                'placeholder': 'Price in BTC'
            }),
            'price_xmr': forms.NumberInput(attrs={
                'step': '0.0001',
                'min': '0',
                'class': 'form-input',
                'placeholder': 'Price in XMR'
            }),
            'stock_quantity': forms.NumberInput(attrs={
                'min': '0',
                'class': 'form-input'
            }),
        }

class VendorSettingsForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = [
            'description', 'response_time'
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 5,
                'class': 'form-input'
            }),
            'response_time': forms.DurationField(widget=forms.TextInput(attrs={
                'placeholder': 'e.g., 1 day, 2 hours',
                'class': 'form-input'
            })),
        }
