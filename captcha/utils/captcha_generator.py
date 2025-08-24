from PIL import Image, ImageDraw, ImageFilter, ImageFont
import random
import math
from io import BytesIO
import time
import hashlib


class OneClickCaptcha:
    """
    Advanced One-Click CAPTCHA generator for Tor-safe environments.
    No JavaScript required, fully server-side processing.
    """
    
    def __init__(
        self,
        width=300,          # Slightly larger for better touch targets
        height=150,
        count=6,
        radius_range=(25, 35),  # Even larger circles for easier clicking
        cut_angle=60,
        margin=30,          # More margin to prevent edge touches
        use_noise=True,
        max_attempts=1000,
        timeout_seconds=300,  # 5 minute timeout
    ):
        self.width = width
        self.height = height
        self.count = count
        self.radius_range = radius_range
        self.cut_angle = cut_angle
        self.margin = margin
        self.use_noise = use_noise
        self.max_attempts = max_attempts
        self.timeout_seconds = timeout_seconds

    def random_color(self):
        """Generate a non-blue dominant color to avoid bias."""
        # Use more varied colors for better contrast
        hue_choice = random.choice(['red', 'green', 'blue', 'purple', 'orange'])
        
        color_map = {
            'red': (random.randint(150, 220), random.randint(50, 100), random.randint(50, 100)),
            'green': (random.randint(50, 100), random.randint(150, 220), random.randint(50, 100)),
            'blue': (random.randint(50, 100), random.randint(50, 100), random.randint(150, 220)),
            'purple': (random.randint(150, 200), random.randint(50, 100), random.randint(150, 200)),
            'orange': (random.randint(200, 250), random.randint(100, 150), random.randint(0, 50)),
        }
        
        return color_map[hue_choice]

    def _draw_target_shape(self, draw, cx, cy, r, shape_type, color, bg_color):
        """Draw different target shapes for variety."""
        if shape_type == 'pacman':
            # Classic Pac-Man with random direction
            cut_start = random.randint(0, 359)
            cut_angle = random.randint(40, 80)
            cut_end = (cut_start + cut_angle) % 360
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
            draw.pieslice((cx - r, cy - r, cx + r, cy + r), cut_start, cut_end, fill=bg_color)
            
        elif shape_type == 'pizza':
            # Pizza slice (multiple cuts)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
            num_slices = random.randint(6, 8)
            for i in range(0, 360, 360 // num_slices):
                draw.line([(cx, cy), (cx + r * math.cos(math.radians(i)), 
                          cy + r * math.sin(math.radians(i)))], fill=bg_color, width=2)
            # Remove one slice
            slice_start = random.randint(0, 359)
            slice_angle = 360 // num_slices
            draw.pieslice((cx - r, cy - r, cx + r, cy + r), slice_start, 
                         slice_start + slice_angle, fill=bg_color)
                         
        elif shape_type == 'star':
            # Star shape
            points = []
            num_points = 5
            for i in range(num_points * 2):
                angle = i * math.pi / num_points
                if i % 2 == 0:
                    radius = r
                else:
                    radius = r * 0.5
                points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
            draw.polygon(points, fill=color)
            
        elif shape_type == 'donut':
            # Donut (circle with hole)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
            inner_r = r // 2
            draw.ellipse((cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r), fill=bg_color)
            
        elif shape_type == 'crescent':
            # Crescent moon
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
            offset = r // 3
            draw.ellipse((cx - r + offset, cy - r, cx + r + offset, cy + r), fill=bg_color)
            
        elif shape_type == 'diamond':
            # Diamond shape
            points = [
                (cx, cy - r),  # top
                (cx + r, cy),  # right
                (cx, cy + r),  # bottom
                (cx - r, cy)   # left
            ]
            draw.polygon(points, fill=color)

    def generate(self, request):
        """Generate a new CAPTCHA image and store the solution in session."""
        # Generate unique token for this captcha
        captcha_token = hashlib.sha256(
            f"{time.time()}{random.random()}".encode()
        ).hexdigest()[:16]
        
        # Randomize colors per session
        bg_color = (
            random.randint(240, 255), 
            random.randint(240, 255), 
            random.randint(240, 255)
        )
        circle_color = self.random_color()
        
        # Create image
        img = Image.new('RGB', (self.width, self.height), bg_color)
        draw = ImageDraw.Draw(img)

        circles = []
        attempts = 0

        # Generate non-overlapping circles with random radii
        while len(circles) < self.count and attempts < self.max_attempts:
            r = random.randint(*self.radius_range)
            x = random.randint(r + self.margin, self.width - r - self.margin)
            y = random.randint(r + self.margin, self.height - r - self.margin)

            # Check for overlaps with more spacing
            if all(
                ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 > (r + cr + 8)
                for cx, cy, cr in circles
            ):
                circles.append((x, y, r))
            else:
                attempts += 1

        if len(circles) < 3:  # Ensure minimum circles
            # Fallback with guaranteed positions
            circles = [
                (self.width // 4, self.height // 2, 22),
                (self.width // 2, self.height // 2, 22),
                (3 * self.width // 4, self.height // 2, 22),
            ]

        # Pick target circle
        target_idx = random.randrange(len(circles))
        tx, ty, tr = circles[target_idx]

        # Choose a random shape type for the target
        shape_types = ['pacman', 'pizza', 'star', 'donut', 'crescent', 'diamond']
        target_shape = random.choice(shape_types)

        # Draw all circles
        for idx, (cx, cy, r) in enumerate(circles):
            # Draw circle with slight border for better visibility
            draw.ellipse(
                (cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1), 
                fill=(0, 0, 0, 50)  # Subtle shadow
            )
            
            if idx == target_idx:
                # Draw the special target shape
                self._draw_target_shape(draw, cx, cy, r, target_shape, circle_color, bg_color)
            else:
                # Draw normal circle
                draw.ellipse(
                    (cx - r, cy - r, cx + r, cy + r), 
                    fill=circle_color
                )

        # Add enhanced noise and distortions for better bot protection
        if self.use_noise:
            # Add background texture first
            for _ in range(random.randint(15, 25)):
                shape_type = random.choice(['ellipse', 'rectangle'])
                x = random.randint(0, self.width)
                y = random.randint(0, self.height)
                size = random.randint(10, 30)
                noise_color = (
                    random.randint(200, 240),
                    random.randint(200, 240),
                    random.randint(200, 240)
                )
                
                if shape_type == 'ellipse':
                    draw.ellipse((x, y, x + size, y + size), fill=noise_color, outline=None)
                else:
                    draw.rectangle((x, y, x + size, y + size), fill=noise_color, outline=None)
            # Random dots with varying opacity
            for _ in range(random.randint(30, 60)):
                nx = random.randint(0, self.width - 1)
                ny = random.randint(0, self.height - 1)
                opacity = random.randint(20, 80)
                color = (
                    random.randint(0, 150),
                    random.randint(0, 150),
                    random.randint(0, 150),
                )
                # Blend with background
                existing = img.getpixel((nx, ny))
                new_color = tuple(
                    int(existing[i] * (1 - opacity/255) + color[i] * (opacity/255))
                    for i in range(3)
                )
                img.putpixel((nx, ny), new_color)

            # Faint curved lines for more natural noise
            for _ in range(random.randint(2, 4)):
                points = []
                for i in range(5):
                    x = int(self.width * i / 4)
                    y = random.randint(0, self.height)
                    points.append((x, y))
                
                # Draw smooth curve through points
                for i in range(len(points) - 1):
                    draw.line(
                        points[i:i+2],
                        fill=(
                            random.randint(200, 230), 
                            random.randint(200, 230), 
                            random.randint(200, 230)
                        ),
                        width=1
                    )

            # Apply slight blur to make it harder for bots
            img = img.filter(ImageFilter.SMOOTH_MORE)

        # Convert to bytes
        buf = BytesIO()
        img.save(buf, format='PNG', optimize=True)
        buf.seek(0)

        # Store solution in session with timeout
        request.session[f'captcha_{captcha_token}'] = {
            'x': tx,
            'y': ty,
            'r': tr,
            'shape': target_shape,
            'timestamp': time.time(),
            'attempts': 0,  # Track failed attempts
        }
        
        # Clean up old captcha data
        self._cleanup_old_captchas(request)
        
        # Store current token
        request.session['current_captcha_token'] = captcha_token

        return buf.getvalue(), captcha_token

    def validate(self, request, click_x, click_y, token=None):
        """Validate the clicked position against the stored solution."""
        import logging
        logger = logging.getLogger('captcha')
        
        # Get token from session if not provided
        if not token:
            token = request.session.get('current_captcha_token')
        
        logger.info(f"Validating CAPTCHA - Token: {token}, Click: ({click_x}, {click_y})")
        
        if not token:
            logger.warning("No token provided or found in session")
            return False
            
        session_key = f'captcha_{token}'
        data = request.session.get(session_key)
        
        if not data:
            logger.warning(f"No CAPTCHA data found for token: {token}")
            return False

        logger.info(f"CAPTCHA data - Target: ({data['x']}, {data['y']}), Radius: {data['r']}, Attempts: {data['attempts']}")

        # Check timeout
        if time.time() - data['timestamp'] > self.timeout_seconds:
            # Expired
            logger.warning("CAPTCHA expired")
            if session_key in request.session:
                del request.session[session_key]
            return False

        # Check attempt limit (prevent brute force)
        if data['attempts'] >= 3:
            # Too many attempts
            logger.warning("Too many CAPTCHA attempts")
            if session_key in request.session:
                del request.session[session_key]
            return False

        # Validate click position
        dx = click_x - data['x']
        dy = click_y - data['y']
        dist_sq = dx * dx + dy * dy
        
        # Allow generous margin of error (50% of radius + 5 pixels)
        # This makes it much more forgiving for users
        margin = int(data['r'] * 0.5) + 5
        is_valid = dist_sq <= (data['r'] + margin) ** 2
        
        logger.info(f"Click validation - Distance squared: {dist_sq}, Required: {(data['r'] + margin) ** 2}, Margin: {margin}, Valid: {is_valid}")
        
        if is_valid:
            # Success - clean up
            if session_key in request.session:
                del request.session[session_key]
            if 'current_captcha_token' in request.session:
                del request.session['current_captcha_token']
        else:
            # Failed attempt
            data['attempts'] += 1
            request.session[session_key] = data
            request.session.modified = True
        
        return is_valid

    def _cleanup_old_captchas(self, request):
        """Remove expired captcha data from session."""
        current_time = time.time()
        keys_to_delete = []
        
        for key in request.session.keys():
            if key.startswith('captcha_') and key != 'current_captcha_token':
                data = request.session.get(key)
                if isinstance(data, dict) and 'timestamp' in data:
                    if current_time - data['timestamp'] > self.timeout_seconds:
                        keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del request.session[key]
        
        if keys_to_delete:
            request.session.modified = True