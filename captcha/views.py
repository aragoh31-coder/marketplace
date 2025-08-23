from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .utils.captcha_generator import OneClickCaptcha

# Initialize the captcha service
captcha_service = OneClickCaptcha(
    width=300,
    height=150,
    count=6,
    use_noise=True,
    timeout_seconds=300  # 5 minutes
)


@never_cache
def generate_captcha_image(request):
    """Generate and return a CAPTCHA image."""
    try:
        # Check if we should reuse existing CAPTCHA (e.g., after form error)
        reuse_token = request.GET.get('token')
        if reuse_token and f'captcha_{reuse_token}' in request.session:
            # Reuse existing CAPTCHA data
            token = reuse_token
            data = request.session[f'captcha_{token}']
            
            # Regenerate the same image
            from PIL import Image, ImageDraw, ImageFilter
            import random
            
            # Create new image with same parameters
            img = Image.new('RGB', (captcha_service.width, captcha_service.height), (255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            # Draw the target circle (with cut)
            x, y, r = data['x'], data['y'], data['r']
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(100, 150, 200))
            draw.pieslice((x-r, y-r, x+r, y+r), 30, 90, fill=(255, 255, 255))
            
            # Add some random circles for distraction
            for _ in range(4):
                rx = random.randint(20, captcha_service.width - 20)
                ry = random.randint(20, captcha_service.height - 20)
                rr = random.randint(15, 25)
                draw.ellipse((rx-rr, ry-rr, rx+rr, ry+rr), fill=(150, 200, 150))
            
            # Apply some blur
            img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
            
            # Convert to bytes
            from io import BytesIO
            buf = BytesIO()
            img.save(buf, format='PNG')
            img_bytes = buf.getvalue()
        else:
            # Generate new CAPTCHA
            img_bytes, token = captcha_service.generate(request)
        
        response = HttpResponse(img_bytes, content_type='image/png')
        # Prevent caching
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['X-Captcha-Token'] = token  # Include token in header for reference
        
        return response
    except Exception as e:
        # Return a default error image
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (300, 150), (255, 200, 200))
        draw = ImageDraw.Draw(img)
        draw.text((50, 65), "Error generating CAPTCHA", fill=(200, 0, 0))
        
        from io import BytesIO
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        return HttpResponse(buf.getvalue(), content_type='image/png')


@require_http_methods(["POST"])
def validate_captcha_click(request):
    """Validate a captcha click position."""
    try:
        # Get click coordinates from form submission
        click_x = int(request.POST.get('captcha_x', -1))
        click_y = int(request.POST.get('captcha_y', -1))
        token = request.POST.get('captcha_token', '')
        
        if click_x < 0 or click_y < 0:
            return JsonResponse({
                'valid': False,
                'error': 'Invalid coordinates'
            })
        
        # Validate the click
        is_valid = captcha_service.validate(request, click_x, click_y, token)
        
        return JsonResponse({
            'valid': is_valid,
            'message': 'Correct!' if is_valid else 'Wrong circle, please try again.'
        })
        
    except (TypeError, ValueError) as e:
        return JsonResponse({
            'valid': False,
            'error': 'Invalid input'
        })
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'error': 'Server error'
        })


def captcha_demo(request):
    """Demo page for testing the CAPTCHA."""
    return render(request, 'captcha/demo.html')
