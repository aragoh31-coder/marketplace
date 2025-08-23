"""
Design System Template Tags
Template tags for easy theming and design system usage.
"""

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

from core.design_system import get_design_system

register = template.Library()


@register.simple_tag
def design_css_variables():
    """Generate CSS variables from the design system theme."""
    from django.utils.html import escape
    design_system = get_design_system()
    css_vars = design_system.generate_css_variables()
    # SECURITY: Escape CSS variables to prevent XSS
    return mark_safe(f":root {{\n            {escape(css_vars)}\n        }}")


@register.simple_tag
def theme_color(color_name, fallback=None):
    """Get a specific color from the theme."""
    design_system = get_design_system()
    return design_system.get_color(color_name, fallback)


@register.simple_tag
def theme_spacing(size, fallback=None):
    """Get a specific spacing value from the theme."""
    design_system = get_design_system()
    return design_system.get_spacing(size, fallback)


@register.simple_tag
def theme_border_radius(size, fallback=None):
    """Get a specific border radius value from the theme."""
    design_system = get_design_system()
    return design_system.get_border_radius(size, fallback)


@register.simple_tag
def theme_transition(type_name, fallback=None):
    """Get a specific transition value from the theme."""
    design_system = get_design_system()
    return design_system.get_transition(type_name, fallback)


@register.simple_tag
def theme_component_setting(component, setting, fallback=None):
    """Get a component-specific setting from the theme."""
    design_system = get_design_system()
    return design_system.get_component_setting(component, setting, fallback)


@register.simple_tag
def theme_info():
    """Get theme information for display purposes."""
    design_system = get_design_system()
    return design_system.get_theme_info()


@register.inclusion_tag("design_system/theme_colors.html")
def theme_colors_display():
    """Display all theme colors in a visual format."""
    design_system = get_design_system()
    return {"colors": design_system.theme["colors"], "theme_name": design_system.theme["name"]}


@register.inclusion_tag("design_system/theme_spacing.html")
def theme_spacing_display():
    """Display all theme spacing values in a visual format."""
    design_system = get_design_system()
    return {"spacing": design_system.theme["spacing"], "theme_name": design_system.theme["name"]}


@register.simple_tag
def design_system_version():
    """Get the current design system version."""
    design_system = get_design_system()
    return design_system.theme["version"]


@register.simple_tag
def design_system_name():
    """Get the current design system name."""
    design_system = get_design_system()
    return design_system.theme["name"]


@register.simple_tag
def design_system_description():
    """Get the current design system description."""
    design_system = get_design_system()
    return design_system.theme["description"]


@register.simple_tag
def inline_css_variables():
    """Generate inline CSS variables for immediate use."""
    from django.utils.html import escape
    design_system = get_design_system()
    css_vars = design_system.generate_css_variables()
    # SECURITY: Escape CSS variables to prevent XSS
    return mark_safe(f"<style>:root {{\n            {escape(css_vars)}\n        }}</style>")


@register.simple_tag
def theme_css_class(base_class, variant=None):
    """Generate CSS classes based on theme variants."""
    design_system = get_design_system()

    if variant and variant in design_system.theme.get("variants", {}):
        return f"{base_class} {base_class}--{variant}"

    return base_class


@register.simple_tag
def theme_style(property_name, value_key, fallback=None):
    """Generate inline styles based on theme values."""
    design_system = get_design_system()

    if property_name == "color":
        value = design_system.get_color(value_key, fallback)
    elif property_name == "spacing":
        value = design_system.get_spacing(value_key, fallback)
    elif property_name == "border-radius":
        value = design_system.get_border_radius(value_key, fallback)
    elif property_name == "transition":
        value = design_system.get_transition(value_key, fallback)
    else:
        value = fallback

    if value:
        from django.utils.html import escape
        # SECURITY: Escape property name and value to prevent XSS
        return mark_safe(f'style="{escape(property_name)}: {escape(str(value))};"')

    return ""


@register.simple_tag
def theme_background_gradient(color1, color2, direction="135deg"):
    """Generate a background gradient using theme colors."""
    design_system = get_design_system()
    c1 = design_system.get_color(color1, color1)
    c2 = design_system.get_color(color2, color2)

    return f"linear-gradient({direction}, {c1} 0%, {c2} 100%)"


@register.simple_tag
def theme_box_shadow(intensity="normal"):
    """Generate a box shadow based on theme settings."""
    design_system = get_design_system()

    if intensity == "strong":
        return design_system.theme["colors"].get("shadow", "0 20px 25px -5px rgba(0, 0, 0, 0.1)")
    elif intensity == "light":
        return "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
    else:
        return design_system.theme["colors"].get("shadow", "0 10px 15px -3px rgba(0, 0, 0, 0.1)")


@register.simple_tag
def theme_animation(name, duration="normal", timing="ease"):
    """Generate CSS animation properties based on theme."""
    design_system = get_design_system()

    if duration == "fast":
        duration_val = "0.15s"
    elif duration == "slow":
        duration_val = "0.5s"
    else:
        duration_val = "0.3s"

    transition = design_system.get_transition(timing, "cubic-bezier(0.4, 0, 0.2, 1)")

    return f"{name} {duration_val} {transition}"


@register.simple_tag
def theme_responsive_class(base_class, breakpoint):
    """Generate responsive CSS classes based on theme breakpoints."""
    design_system = get_design_system()
    breakpoint_value = design_system.theme["breakpoints"].get(breakpoint, "768px")

    return f"{base_class} {base_class}--{breakpoint}"


@register.simple_tag
def theme_glassmorphism(intensity="normal"):
    """Generate glassmorphism CSS properties based on theme."""
    design_system = get_design_system()

    if intensity == "strong":
        backdrop_blur = "30px"
        background = "rgba(15, 23, 42, 0.8)"
    elif intensity == "light":
        backdrop_blur = "10px"
        background = "rgba(15, 23, 42, 0.4)"
    else:
        backdrop_blur = "20px"
        background = "rgba(15, 23, 42, 0.6)"

    from django.utils.html import escape
    # SECURITY: Escape background and backdrop-blur values to prevent XSS
    return mark_safe(f'style="background: {escape(background)}; backdrop-filter: blur({escape(backdrop_blur)});"')


@register.simple_tag
def theme_text_gradient(color1, color2, direction="135deg"):
    """Generate text gradient CSS properties using theme colors."""
    design_system = get_design_system()
    c1 = design_system.get_color(color1, color1)
    c2 = design_system.get_color(color2, color2)

    from django.utils.html import escape
    # SECURITY: Escape all values to prevent XSS
    return mark_safe(
        f'style="background: linear-gradient({escape(direction)}, {escape(c1)} 0%, {escape(c2)} 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;"'
    )
