"""
Django Design System Module
A centralized system for managing the entire application design without JavaScript.
"""

from django.conf import settings
from django.core.cache import cache
from django.utils.safestring import mark_safe
import json
import os
from pathlib import Path


class DesignSystem:
    """
    Centralized design system for managing application appearance.
    """
    
    # Default theme configuration
    DEFAULT_THEME = {
        'name': 'premium_dark',
        'version': '1.0.0',
        'description': 'Premium dark theme with modern glassmorphism design',
        
        # Color palette
        'colors': {
            'primary': '#00ff88',
            'primary_dim': '#00cc6a',
            'secondary': '#7c3aed',
            'accent': '#06b6d4',
            'danger': '#ef4444',
            'warning': '#f59e0b',
            'success': '#10b981',
            'info': '#3b82f6',
            
            # Background colors
            'bg_primary': '#0a0f1b',
            'bg_secondary': '#0f172a',
            'bg_tertiary': '#1e293b',
            'bg_card': 'rgba(15, 23, 42, 0.6)',
            'bg_overlay': 'rgba(10, 15, 27, 0.8)',
            
            # Text colors
            'text_primary': '#f1f5f9',
            'text_secondary': '#94a3b8',
            'text_dim': '#64748b',
            'text_muted': '#475569',
            
            # Border and shadow
            'border': 'rgba(148, 163, 184, 0.1)',
            'border_strong': 'rgba(148, 163, 184, 0.2)',
            'shadow': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
            'glow': '0 0 40px rgba(0, 255, 136, 0.3)',
            'glow_strong': '0 0 60px rgba(0, 255, 136, 0.5)',
        },
        
        # Typography
        'typography': {
            'font_family': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            'font_size_base': '16px',
            'font_size_small': '14px',
            'font_size_large': '18px',
            'font_size_h1': '2.5rem',
            'font_size_h2': '2rem',
            'font_size_h3': '1.5rem',
            'font_size_h4': '1.25rem',
            'font_weight_normal': '400',
            'font_weight_medium': '500',
            'font_weight_semibold': '600',
            'font_weight_bold': '700',
            'font_weight_black': '900',
            'line_height': '1.6',
            'letter_spacing': '0.025em',
        },
        
        # Spacing system
        'spacing': {
            'xs': '0.25rem',
            'sm': '0.5rem',
            'md': '1rem',
            'lg': '1.5rem',
            'xl': '2rem',
            '2xl': '3rem',
            '3xl': '4rem',
            '4xl': '6rem',
        },
        
        # Border radius
        'border_radius': {
            'none': '0',
            'sm': '0.25rem',
            'md': '0.5rem',
            'lg': '0.75rem',
            'xl': '1rem',
            '2xl': '1.5rem',
            'full': '9999px',
        },
        
        # Transitions and animations
        'transitions': {
            'fast': 'all 0.15s cubic-bezier(0.4, 0, 0.2, 1)',
            'normal': 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            'slow': 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
            'bounce': 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
            'ease_in': 'cubic-bezier(0.4, 0, 0.2, 1)',
            'ease_out': 'cubic-bezier(0.4, 0, 0.2, 1)',
        },
        
        # Component-specific settings
        'components': {
            'header': {
                'height': '80px',
                'backdrop_blur': '20px',
                'border_bottom': '1px solid rgba(148, 163, 184, 0.1)',
            },
            'card': {
                'padding': '1.5rem',
                'backdrop_blur': '10px',
                'border': '1px solid rgba(148, 163, 184, 0.1)',
            },
            'button': {
                'padding': '0.75rem 1.5rem',
                'border_radius': '0.5rem',
                'font_weight': '500',
            },
            'input': {
                'padding': '0.75rem 1rem',
                'border_radius': '0.5rem',
                'border': '1px solid rgba(148, 163, 184, 0.2)',
            },
        },
        
        # Layout settings
        'layout': {
            'max_width': '1400px',
            'container_padding': '2rem',
            'grid_gap': '2rem',
            'sidebar_width': '280px',
        },
        
        # Breakpoints
        'breakpoints': {
            'xs': '480px',
            'sm': '640px',
            'md': '768px',
            'lg': '1024px',
            'xl': '1280px',
            '2xl': '1536px',
        },
    }
    
    def __init__(self):
        self.theme = self.load_theme()
        self.cache_key = 'design_system_theme'
    
    def load_theme(self):
        """Load theme from cache or file, fallback to default."""
        cached_theme = cache.get(self.cache_key)
        if cached_theme:
            return cached_theme
        
        # Try to load custom theme file
        custom_theme_path = Path(settings.BASE_DIR) / 'core' / 'themes' / 'custom_theme.json'
        if custom_theme_path.exists():
            try:
                with open(custom_theme_path, 'r') as f:
                    custom_theme = json.load(f)
                    # Merge with default theme
                    merged_theme = self.merge_themes(self.DEFAULT_THEME, custom_theme)
                    cache.set(self.cache_key, merged_theme, 3600)  # Cache for 1 hour
                    return merged_theme
            except Exception:
                pass
        
        # Fallback to default theme
        cache.set(self.cache_key, self.DEFAULT_THEME, 3600)
        return self.DEFAULT_THEME
    
    def merge_themes(self, base_theme, custom_theme):
        """Recursively merge custom theme with base theme."""
        merged = base_theme.copy()
        
        for key, value in custom_theme.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self.merge_themes(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def get_color(self, color_name, fallback=None):
        """Get a color value from the theme."""
        return self.theme['colors'].get(color_name, fallback or '#000000')
    
    def get_spacing(self, size, fallback=None):
        """Get a spacing value from the theme."""
        return self.theme['spacing'].get(size, fallback or '1rem')
    
    def get_border_radius(self, size, fallback=None):
        """Get a border radius value from the theme."""
        return self.theme['border_radius'].get(size, fallback or '0.5rem')
    
    def get_transition(self, type_name, fallback=None):
        """Get a transition value from the theme."""
        return self.theme['transitions'].get(type_name, fallback or 'all 0.3s ease')
    
    def get_component_setting(self, component, setting, fallback=None):
        """Get a component-specific setting from the theme."""
        return self.theme['components'].get(component, {}).get(setting, fallback)
    
    def generate_css_variables(self):
        """Generate CSS variables string from the current theme."""
        css_vars = []
        
        # Color variables
        for name, value in self.theme['colors'].items():
            css_vars.append(f'--{name.replace("_", "-")}: {value};')
        
        # Typography variables
        for name, value in self.theme['typography'].items():
            css_vars.append(f'--{name.replace("_", "-")}: {value};')
        
        # Spacing variables
        for name, value in self.theme['spacing'].items():
            css_vars.append(f'--spacing-{name}: {value};')
        
        # Border radius variables
        for name, value in self.theme['border_radius'].items():
            css_vars.append(f'--radius-{name}: {value};')
        
        # Transition variables
        for name, value in self.theme['transitions'].items():
            css_vars.append(f'--transition-{name}: {value};')
        
        # Component variables
        for component, settings in self.theme['components'].items():
            for name, value in settings.items():
                css_vars.append(f'--{component}-{name.replace("_", "-")}: {value};')
        
        # Layout variables
        for name, value in self.theme['layout'].items():
            css_vars.append(f'--layout-{name.replace("_", "-")}: {value};')
        
        # Breakpoint variables
        for name, value in self.theme['breakpoints'].items():
            css_vars.append(f'--breakpoint-{name}: {value};')
        
        return '\n            '.join(css_vars)
    
    def get_theme_info(self):
        """Get theme information for display purposes."""
        return {
            'name': self.theme['name'],
            'version': self.theme['version'],
            'description': self.theme['description'],
            'color_count': len(self.theme['colors']),
            'component_count': len(self.theme['components']),
        }
    
    def update_theme(self, new_theme_data):
        """Update the current theme with new data."""
        updated_theme = self.merge_themes(self.theme, new_theme_data)
        self.theme = updated_theme
        
        # Save to custom theme file
        custom_theme_path = Path(settings.BASE_DIR) / 'core' / 'themes'
        custom_theme_path.mkdir(exist_ok=True)
        
        with open(custom_theme_path / 'custom_theme.json', 'w') as f:
            json.dump(new_theme_data, f, indent=2)
        
        # Clear cache
        cache.delete(self.cache_key)
        
        return True
    
    def reset_to_default(self):
        """Reset theme to default values."""
        self.theme = self.DEFAULT_THEME.copy()
        
        # Remove custom theme file
        custom_theme_path = Path(settings.BASE_DIR) / 'core' / 'themes' / 'custom_theme.json'
        if custom_theme_path.exists():
            custom_theme_path.unlink()
        
        # Clear cache
        cache.delete(self.cache_key)
        
        return True


# Global design system instance
design_system = DesignSystem()


def get_design_system():
    """Get the global design system instance."""
    return design_system


def get_theme_colors():
    """Get all theme colors as a dictionary."""
    return design_system.theme['colors']


def get_theme_spacing():
    """Get all theme spacing values as a dictionary."""
    return design_system.theme['spacing']


def get_theme_typography():
    """Get all theme typography values as a dictionary."""
    return design_system.theme['typography']