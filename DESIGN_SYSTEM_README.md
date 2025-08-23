# Django Design System

A comprehensive, modular design system for Django applications that makes it easy to modify the entire design without JavaScript. This system provides centralized theme management, reusable CSS components, and powerful template tags.

## 🚀 Features

- **Centralized Theme Management**: All design values stored in one place
- **No JavaScript Required**: Pure CSS and Django template-based
- **Modular Components**: Reusable CSS classes and components
- **Dynamic CSS Variables**: Automatically generated from theme configuration
- **Admin Interface**: Visual theme editor in Django admin
- **Command Line Tools**: Easy theme updates via management commands
- **Template Tags**: Powerful theming helpers for templates
- **Responsive Design**: Built-in responsive utilities and breakpoints
- **Glassmorphism Effects**: Modern visual effects with CSS variables

## 📁 Project Structure

```
core/
├── design_system.py          # Main design system module
├── templatetags/
│   └── design_system.py     # Template tags for theming
├── management/
│   └── commands/
│       └── update_design.py # Management command for themes
└── admin.py                 # Admin interface for design system

static/
├── css/
│   ├── design-system.css    # Main CSS with components
│   └── variables.css        # CSS variables (auto-generated)

templates/
├── base_design_system.html  # Example base template
└── admin/
    └── design_system_change_list.html  # Admin interface template
```

## 🎨 Theme Configuration

The design system uses a hierarchical theme structure:

```python
THEME = {
    'name': 'premium_dark',
    'version': '1.0.0',
    'colors': {
        'primary': '#00ff88',
        'secondary': '#7c3aed',
        # ... more colors
    },
    'typography': {
        'font_family': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        'font_size_base': '16px',
        # ... more typography settings
    },
    'spacing': {
        'xs': '0.25rem',
        'sm': '0.5rem',
        # ... more spacing values
    },
    'components': {
        'button': {
            'padding': '0.75rem 1.5rem',
            'border_radius': '0.5rem',
        },
        # ... more component settings
    }
}
```

## 🛠️ Usage

### 1. Basic Setup

Add the design system to your Django project:

```python
# settings.py
INSTALLED_APPS = [
    # ... other apps
    'core',  # Make sure core app is included
]

# The design system will automatically load
```

### 2. Using Template Tags

Load the design system in your templates:

```html
{% load design_system %}

<!-- Generate CSS variables -->
<style>
    {% design_css_variables %}
</style>

<!-- Use theme values -->
<div style="color: {% theme_color 'primary' %}">
    This text uses the primary theme color
</div>

<!-- Generate gradients -->
<div class="card" style="background: {% theme_background_gradient 'primary' 'secondary' %}">
    Gradient background
</div>

<!-- Glassmorphism effects -->
<div class="card" {% theme_glassmorphism 'strong' %}>
    Strong glassmorphism effect
</div>
```

### 3. Using CSS Classes

The design system provides utility classes:

```html
<!-- Layout -->
<div class="container">
    <div class="row">
        <div class="col-6 col-md-4">
            Content
        </div>
    </div>
</div>

<!-- Spacing -->
<div class="p-lg m-xl">
    Large padding and margin
</div>

<!-- Components -->
<button class="btn btn-primary btn-lg">
    Large Primary Button
</button>

<div class="card glass">
    <div class="card-header">
        <h3 class="card-title">Card Title</h3>
    </div>
    <div class="card-body">
        Card content
    </div>
</div>

<!-- Typography -->
<h1 class="text-gradient-primary">Gradient Text</h1>
<p class="text-secondary font-medium">Medium weight secondary text</p>
```

### 4. Management Commands

Update themes from the command line:

```bash
# Show current theme
python manage.py update_design --show-current

# Update a specific color
python manage.py update_design --update-color primary #ff0000

# Update spacing
python manage.py update_design --update-spacing md 2rem

# Update typography
python manage.py update_design --update-typography font-size-base 18px

# Load theme from file
python manage.py update_design --theme-file themes/custom.json

# Reset to default
python manage.py update_design --reset
```

### 5. Admin Interface

Access the visual theme editor at `/admin/`:

- **Colors**: Visual color picker with live preview
- **Spacing**: Update spacing values with validation
- **Typography**: Modify font settings
- **Components**: Adjust component-specific settings
- **Import/Export**: Share themes between projects

## 🎯 Customization Examples

### Changing the Primary Color

```bash
python manage.py update_design --update-color primary #ff6b6b
```

### Creating a Light Theme

```json
{
    "name": "light_theme",
    "colors": {
        "bg_primary": "#ffffff",
        "bg_secondary": "#f8f9fa",
        "text_primary": "#212529",
        "text_secondary": "#6c757d"
    }
}
```

Save as `themes/light.json` and load:

```bash
python manage.py update_design --theme-file themes/light.json
```

### Custom Component Settings

```json
{
    "components": {
        "button": {
            "padding": "1rem 2rem",
            "border_radius": "1rem"
        },
        "card": {
            "padding": "2rem",
            "backdrop_blur": "20px"
        }
    }
}
```

## 🔧 Advanced Usage

### Custom Template Tags

Create your own design system template tags:

```python
# myapp/templatetags/custom_design.py
from django import template
from core.design_system import get_design_system

register = template.Library()

@register.simple_tag
def custom_theme_value(category, name):
    design_system = get_design_system()
    return design_system.theme[category][name]
```

### Dynamic Theme Switching

```python
# views.py
from core.design_system import get_design_system

def switch_theme(request, theme_name):
    design_system = get_design_system()
    
    if theme_name == 'dark':
        theme_data = {
            'colors': {
                'bg_primary': '#0a0f1b',
                'text_primary': '#f1f5f9'
            }
        }
    elif theme_name == 'light':
        theme_data = {
            'colors': {
                'bg_primary': '#ffffff',
                'text_primary': '#212529'
            }
        }
    
    design_system.update_theme(theme_data)
    return redirect('home')
```

### Theme Inheritance

Themes can inherit from base themes:

```python
# Custom theme that extends the default
custom_theme = {
    'name': 'custom_dark',
    'colors': {
        'primary': '#ff6b6b',  # Override primary color
        'accent': '#4ecdc4'    # Override accent color
    }
    # All other settings inherit from default
}
```

## 📱 Responsive Design

The design system includes responsive utilities:

```html
<!-- Responsive columns -->
<div class="col-12 col-md-6 col-lg-4">
    Responsive content
</div>

<!-- Responsive display -->
<div class="d-none d-md-block">
    Hidden on mobile, visible on medium+
</div>

<!-- Responsive spacing -->
<div class="p-md p-lg-lg">
    Medium padding on small screens, large on large screens
</div>
```

## 🎨 Available Components

### Buttons
- `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-accent`
- `.btn-danger`, `.btn-warning`, `.btn-success`, `.btn-info`
- `.btn-outline`, `.btn-sm`, `.btn-lg`

### Cards
- `.card`, `.card-header`, `.card-body`, `.card-footer`
- `.glass`, `.glass-strong`, `.glass-light`

### Forms
- `.form-group`, `.form-label`, `.form-control`, `.form-text`

### Alerts
- `.alert`, `.alert-success`, `.alert-warning`, `.alert-danger`, `.alert-info`

### Navigation
- `.navbar`, `.navbar-brand`, `.navbar-nav`, `.nav-link`

### Utilities
- `.text-primary`, `.text-secondary`, `.text-dim`, `.text-muted`
- `.font-normal`, `.font-medium`, `.font-semibold`, `.font-bold`
- `.shadow`, `.shadow-lg`, `.rounded`, `.rounded-lg`
- `.animate-fade-in`, `.animate-slide-left`, `.animate-pulse`

## 🚀 Performance

- **Caching**: Theme data is cached for 1 hour
- **CSS Variables**: Efficient CSS variable usage
- **Minimal JavaScript**: Only essential interactive features
- **Optimized CSS**: Modular CSS with minimal redundancy

## 🔒 Security

- **Admin Only**: Theme changes restricted to admin users
- **Input Validation**: All theme values are validated
- **CSRF Protection**: All forms include CSRF tokens
- **File Upload Security**: JSON file validation

## 🤝 Contributing

To extend the design system:

1. Add new theme categories in `design_system.py`
2. Create corresponding template tags
3. Add CSS utilities in `design-system.css`
4. Update the admin interface
5. Document new features

## 📚 Examples

See `templates/base_design_system.html` for a complete example of using the design system in a base template.

## 🆘 Troubleshooting

### Theme Not Updating
- Clear Django cache: `python manage.py clearcache`
- Check file permissions for theme files
- Verify admin user permissions

### CSS Variables Not Working
- Ensure `{% load design_system %}` is in your template
- Check that `design-system.css` is loaded
- Verify static files are collected: `python manage.py collectstatic`

### Admin Interface Not Loading
- Check that `core` app is in `INSTALLED_APPS`
- Verify admin site is properly configured
- Check for template errors in Django logs

## 📄 License

This design system is part of your Django project and follows the same license terms.

---

**Happy Theming! 🎨✨**