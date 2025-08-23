"""
Image optimization utilities for the marketplace
"""
from PIL import Image, ImageOps
from io import BytesIO
import os
import hashlib
from django.core.files.base import ContentFile
from django.conf import settings


class ImageOptimizer:
    """Optimize images for web delivery"""
    
    # Maximum dimensions for different image types
    MAX_DIMENSIONS = {
        'product': (800, 800),
        'thumbnail': (300, 300),
        'avatar': (200, 200),
        'banner': (1200, 400),
    }
    
    # JPEG quality settings
    QUALITY_SETTINGS = {
        'high': 85,
        'medium': 75,
        'low': 65,
        'thumbnail': 70,
    }
    
    @classmethod
    def optimize_image(cls, image_file, image_type='product', quality='medium'):
        """
        Optimize an image file for web delivery
        
        Args:
            image_file: Django UploadedFile or file-like object
            image_type: Type of image (product, thumbnail, avatar, banner)
            quality: Quality setting (high, medium, low)
            
        Returns:
            Optimized image as ContentFile
        """
        # Open image
        img = Image.open(image_file)
        
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create a white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1])
            img = background
        
        # Auto-orient based on EXIF data
        img = ImageOps.exif_transpose(img)
        
        # Resize if needed
        max_dims = cls.MAX_DIMENSIONS.get(image_type, (800, 800))
        img.thumbnail(max_dims, Image.Resampling.LANCZOS)
        
        # Save optimized image
        output = BytesIO()
        img.save(
            output,
            format='JPEG',
            quality=cls.QUALITY_SETTINGS.get(quality, 75),
            optimize=True,
            progressive=True
        )
        
        # Create ContentFile
        output.seek(0)
        return ContentFile(output.read())
    
    @classmethod
    def generate_thumbnail(cls, image_file, size=(300, 300)):
        """Generate a thumbnail from an image"""
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Create thumbnail
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Save thumbnail
        output = BytesIO()
        img.save(output, format='JPEG', quality=70, optimize=True)
        output.seek(0)
        
        return ContentFile(output.read())
    
    @classmethod
    def get_image_hash(cls, image_file):
        """Generate hash of image content for deduplication"""
        hasher = hashlib.sha256()
        for chunk in image_file.chunks():
            hasher.update(chunk)
        return hasher.hexdigest()
    
    @classmethod
    def estimate_file_size(cls, dimensions, quality=75):
        """Estimate compressed JPEG file size"""
        # Rough estimation formula
        width, height = dimensions
        pixels = width * height
        # Base calculation: pixels * 3 (RGB) * quality factor
        estimated_bytes = pixels * 3 * (quality / 100) * 0.1
        return int(estimated_bytes)


class LazyImageLoader:
    """Generate lazy loading HTML for images"""
    
    @staticmethod
    def get_lazy_image_html(image_url, alt_text="", css_class="", width=None, height=None):
        """Generate HTML for lazy loaded image"""
        # For Tor compatibility, we use a simple approach without JavaScript
        # Images will load normally but with proper sizing hints
        
        size_attrs = ""
        if width and height:
            size_attrs = f'width="{width}" height="{height}"'
        
        # Add loading="lazy" attribute for browsers that support it
        # This works without JavaScript in modern browsers
        return f'''<img src="{image_url}" 
                       alt="{alt_text}" 
                       class="{css_class}" 
                       loading="lazy" 
                       decoding="async"
                       {size_attrs}>'''
    
    @staticmethod
    def get_placeholder_style(width, height):
        """Get CSS for image placeholder"""
        aspect_ratio = height / width * 100
        return f"padding-bottom: {aspect_ratio:.2f}%;"