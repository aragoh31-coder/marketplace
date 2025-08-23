"""
Django management command to update the design system.
Usage: python manage.py update_design
"""

import json
import os

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError

from core.design_system import get_design_system


class Command(BaseCommand):
    help = "Update the design system theme and regenerate CSS variables"

    def add_arguments(self, parser):
        parser.add_argument(
            "--theme-file",
            type=str,
            help="Path to a JSON theme file to load",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset to default theme",
        )
        parser.add_argument(
            "--show-current",
            action="store_true",
            help="Show current theme configuration",
        )
        parser.add_argument(
            "--update-color",
            nargs=2,
            metavar=("COLOR_NAME", "COLOR_VALUE"),
            help="Update a specific color (e.g., --update-color primary #ff0000)",
        )
        parser.add_argument(
            "--update-spacing",
            nargs=2,
            metavar=("SPACING_NAME", "SPACING_VALUE"),
            help="Update a specific spacing value (e.g., --update-spacing md 2rem)",
        )
        parser.add_argument(
            "--update-typography",
            nargs=2,
            metavar=("TYPOGRAPHY_NAME", "TYPOGRAPHY_VALUE"),
            help="Update a specific typography value (e.g., --update-typography font-size-base 18px)",
        )

    def handle(self, *args, **options):
        design_system = get_design_system()

        if options["show_current"]:
            self.show_current_theme(design_system)
            return

        if options["reset"]:
            self.reset_theme(design_system)
            return

        if options["theme_file"]:
            self.load_theme_file(design_system, options["theme_file"])
            return

        if options["update_color"]:
            color_name, color_value = options["update_color"]
            self.update_color(design_system, color_name, color_value)
            return

        if options["update_spacing"]:
            spacing_name, spacing_value = options["update_spacing"]
            self.update_spacing(design_system, spacing_name, spacing_value)
            return

        if options["update_typography"]:
            typography_name, typography_value = options["update_typography"]
            self.update_typography(design_system, typography_name, typography_value)
            return

        # If no specific action, show help
        self.stdout.write(self.style.WARNING("No action specified. Use --help to see available options."))

    def show_current_theme(self, design_system):
        """Display current theme configuration."""
        theme_info = design_system.get_theme_info()

        self.stdout.write(self.style.SUCCESS(f"Current Theme: {theme_info['name']}"))
        self.stdout.write(f"Version: {theme_info['version']}")
        self.stdout.write(f"Description: {theme_info['description']}")
        self.stdout.write(f"Colors: {theme_info['color_count']}")
        self.stdout.write(f"Components: {theme_info['component_count']}")

        # Show some key values
        self.stdout.write("\nKey Colors:")
        for color_name in ["primary", "secondary", "accent", "danger", "warning"]:
            color_value = design_system.get_color(color_name)
            self.stdout.write(f"  {color_name}: {color_value}")

        self.stdout.write("\nKey Spacing:")
        for spacing_name in ["xs", "sm", "md", "lg", "xl"]:
            spacing_value = design_system.get_spacing(spacing_name)
            self.stdout.write(f"  {spacing_name}: {spacing_value}")

    def reset_theme(self, design_system):
        """Reset theme to default values."""
        try:
            design_system.reset_to_default()
            self.stdout.write(self.style.SUCCESS("Theme reset to default values successfully!"))
        except Exception as e:
            raise CommandError(f"Failed to reset theme: {e}")

    def load_theme_file(self, design_system, theme_file_path):
        """Load theme from a JSON file."""
        if not os.path.exists(theme_file_path):
            raise CommandError(f"The theme file does not exist: {theme_file_path}")

        try:
            with open(theme_file_path, "r") as f:
                theme_data = json.load(f)

            design_system.update_theme(theme_data)
            self.stdout.write(self.style.SUCCESS(f"Theme loaded from {theme_file_path} successfully!"))
        except json.JSONDecodeError:
            raise CommandError(f"Invalid JSON in theme file: {theme_file_path}")
        except Exception as e:
            raise CommandError(f"Failed to load theme file: {e}")

    def update_color(self, design_system, color_name, color_value):
        """Update a specific color value."""
        try:
            # Validate color value (basic hex check)
            if not color_value.startswith("#") or len(color_value) not in [4, 7, 9]:
                raise ValueError(f"Invalid color format: {color_value}")

            update_data = {"colors": {color_name: color_value}}

            design_system.update_theme(update_data)
            self.stdout.write(self.style.SUCCESS(f"Color {color_name} updated to {color_value}"))
        except Exception as e:
            raise CommandError(f"Failed to update color: {e}")

    def update_spacing(self, design_system, spacing_name, spacing_value):
        """Update a specific spacing value."""
        try:
            # Validate spacing value (basic CSS unit check)
            valid_units = ["px", "rem", "em", "%", "vh", "vw"]
            if not any(unit in spacing_value for unit in valid_units):
                raise ValueError(f"Invalid spacing format: {spacing_value}")

            update_data = {"spacing": {spacing_name: spacing_value}}

            design_system.update_theme(update_data)
            self.stdout.write(self.style.SUCCESS(f"Spacing {spacing_name} updated to {spacing_value}"))
        except Exception as e:
            raise CommandError(f"Failed to update spacing: {e}")

    def update_typography(self, design_system, typography_name, typography_value):
        """Update a specific typography value."""
        try:
            update_data = {"typography": {typography_name: typography_value}}

            design_system.update_theme(update_data)
            self.stdout.write(self.style.SUCCESS(f"Typography {typography_name} updated to {typography_value}"))
        except Exception as e:
            raise CommandError(f"Failed to update typography: {e}")
