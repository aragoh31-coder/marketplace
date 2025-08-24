from django.apps import AppConfig


class VendorsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vendors"
    
    def ready(self):
        # Initialize BBCode methods for Vendor model
        from .utils import add_bbcode_methods_to_vendor
        add_bbcode_methods_to_vendor()
