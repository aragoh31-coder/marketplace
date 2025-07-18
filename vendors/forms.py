from django import forms
from .models import Vendor
from products.models import Product
from core.security.image_security import SecureImageProcessor

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
    image = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'accept': 'image/jpeg,image/png,image/gif',
            'class': 'form-input'
        }),
        help_text='Max 5MB. JPEG, PNG, or GIF only.'
    )
    
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
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        
        if image:
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image file too large (max 5MB)")
            
            name = image.name.lower()
            if not any(name.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                raise forms.ValidationError("Invalid file type. Use JPEG, PNG, or GIF.")
        
        return image
    
    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        
        image = self.cleaned_data.get('image')
        if image and user:
            processor = SecureImageProcessor()
            success, filename, thumb_filename = processor.validate_and_process_image(
                image, user
            )
            
            if success:
                if instance.pk and (instance.image_filename or instance.thumbnail_filename):
                    processor.delete_images(
                        instance.image_filename, 
                        instance.thumbnail_filename
                    )
                
                instance.image_filename = filename
                instance.thumbnail_filename = thumb_filename
            else:
                self.add_error('image', filename)  # filename contains error message
                return None
        
        if commit:
            instance.save()
        
        return instance

class VendorSettingsForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 5,
                'class': 'form-input'
            }),
        }
