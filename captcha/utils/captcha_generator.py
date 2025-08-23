from PIL import Image, ImageDraw, ImageFilter
import random
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
        radius_range=(20, 28),  # Larger circles for accessibility
        cut_angle=60,
        margin=25,          # More margin to prevent edge touches
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

        # Random cut angle (makes Pac-Man face different directions)
        cut_start = random.randint(0, 359)
        cut_end = (cut_start + self.cut_angle) % 360

        # Draw all circles
        for idx, (cx, cy, r) in enumerate(circles):
            # Draw circle with slight border for better visibility
            draw.ellipse(
                (cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1), 
                fill=(0, 0, 0, 50)  # Subtle shadow
            )
            draw.ellipse(
                (cx - r, cy - r, cx + r, cy + r), 
                fill=circle_color
            )
            
            # Cut out slice only on target
            if idx == target_idx:
                # Make the cut more visible
                draw.pieslice(
                    (cx - r, cy - r, cx + r, cy + r), 
                    cut_start, 
                    cut_end, 
                    fill=bg_color
                )

        # Add subtle noise and distortions
        if self.use_noise:
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
        # Get token from session if not provided
        if not token:
            token = request.session.get('current_captcha_token')
        
        if not token:
            return False
            
        session_key = f'captcha_{token}'
        data = request.session.get(session_key)
        
        if not data:
            return False

        # Check timeout
        if time.time() - data['timestamp'] > self.timeout_seconds:
            # Expired
            if session_key in request.session:
                del request.session[session_key]
            return False

        # Check attempt limit (prevent brute force)
        if data['attempts'] >= 3:
            # Too many attempts
            if session_key in request.session:
                del request.session[session_key]
            return False

        # Validate click position
        dx = click_x - data['x']
        dy = click_y - data['y']
        dist_sq = dx * dx + dy * dy
        
        # Allow slight margin of error (2 pixels)
        is_valid = dist_sq <= (data['r'] + 2) ** 2
        
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