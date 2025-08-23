from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path
from django.contrib import messages
from django.utils.html import format_html
from .design_system import get_design_system
import json


@admin.register(admin.models.LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    # to disable the 'add' action
    def has_add_permission(self, request):
        return False

    # to disable the 'delete' action
    def has_delete_permission(self, request, obj=None):
        return False

    # to disable the 'change' action
    def has_change_permission(self, request, obj=None):
        return False


class DesignSystemAdmin(admin.ModelAdmin):
    """Admin interface for managing the design system."""
    
    change_list_template = 'admin/design_system_change_list.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('update-theme/', self.update_theme, name='update-theme'),
            path('reset-theme/', self.reset_theme, name='reset-theme'),
            path('export-theme/', self.export_theme, name='export-theme'),
            path('import-theme/', self.import_theme, name='import-theme'),
        ]
        return custom_urls + urls
    
    def update_theme(self, request):
        """Handle theme updates from the admin interface."""
        if request.method == 'POST':
            try:
                design_system = get_design_system()
                
                # Parse the form data
                theme_data = {}
                
                # Colors
                colors = {}
                for key, value in request.POST.items():
                    if key.startswith('color_'):
                        color_name = key.replace('color_', '')
                        colors[color_name] = value
                if colors:
                    theme_data['colors'] = colors
                
                # Spacing
                spacing = {}
                for key, value in request.POST.items():
                    if key.startswith('spacing_'):
                        spacing_name = key.replace('spacing_', '')
                        spacing[spacing_name] = value
                if spacing:
                    theme_data['spacing'] = spacing
                
                # Typography
                typography = {}
                for key, value in request.POST.items():
                    if key.startswith('typography_'):
                        typography_name = key.replace('typography_', '')
                        typography[typography_name] = value
                if typography:
                    theme_data['typography'] = typography
                
                if theme_data:
                    design_system.update_theme(theme_data)
                    messages.success(request, 'Theme updated successfully!')
                else:
                    messages.warning(request, 'No changes were made.')
                
            except Exception as e:
                messages.error(request, f'Error updating theme: {str(e)}')
        
        return HttpResponseRedirect('../')
    
    def reset_theme(self, request):
        """Reset theme to default values."""
        try:
            design_system = get_design_system()
            design_system.reset_to_default()
            messages.success(request, 'Theme reset to default values successfully!')
        except Exception as e:
            messages.error(request, f'Error resetting theme: {str(e)}')
        
        return HttpResponseRedirect('../')
    
    def export_theme(self, request):
        """Export current theme as JSON."""
        try:
            design_system = get_design_system()
            theme_data = design_system.theme
            
            response = HttpResponseRedirect('../')
            response['Content-Type'] = 'application/json'
            response['Content-Disposition'] = 'attachment; filename="theme_export.json"'
            response.content = json.dumps(theme_data, indent=2)
            
            return response
        except Exception as e:
            messages.error(request, f'Error exporting theme: {str(e)}')
            return HttpResponseRedirect('../')
    
    def import_theme(self, request):
        """Import theme from JSON file."""
        if request.method == 'POST' and request.FILES.get('theme_file'):
            try:
                design_system = get_design_system()
                
                theme_file = request.FILES['theme_file']
                theme_data = json.loads(theme_file.read().decode('utf-8'))
                
                design_system.update_theme(theme_data)
                messages.success(request, 'Theme imported successfully!')
                
            except json.JSONDecodeError:
                messages.error(request, 'Invalid JSON file format.')
            except Exception as e:
                messages.error(request, f'Error importing theme: {str(e)}')
        
        return HttpResponseRedirect('../')
    
    def changelist_view(self, request, extra_context=None):
        """Custom changelist view to show design system interface."""
        design_system = get_design_system()
        theme_info = design_system.get_theme_info()
        
        extra_context = extra_context or {}
        extra_context.update({
            'theme_info': theme_info,
            'colors': design_system.theme['colors'],
            'spacing': design_system.theme['spacing'],
            'typography': design_system.theme['typography'],
            'components': design_system.theme['components'],
            'layout': design_system.theme['layout'],
            'transitions': design_system.theme['transitions'],
            'border_radius': design_system.theme['border_radius'],
            'breakpoints': design_system.theme['breakpoints'],
        })
        
        return super().changelist_view(request, extra_context)


# Register the design system admin
admin.site.register(DesignSystemAdmin)