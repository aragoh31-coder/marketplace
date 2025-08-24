import re
from django.utils.html import escape
from django.utils.safestring import mark_safe


class BBCodeParser:
    """
    BBCode parser for vendor profiles and product descriptions.
    Converts BBCode to HTML safely without requiring JavaScript.
    """
    
    def __init__(self):
        self.tags = {
            # Text formatting
            'b': ('<strong>', '</strong>'),
            'i': ('<em>', '</em>'),
            'u': ('<u>', '</u>'),
            's': ('<s>', '</s>'),
            
            # Text size
            'big': ('<span style="font-size: 1.2em;">', '</span>'),
            'small': ('<span style="font-size: 0.9em;">', '</span>'),
            
            # Lists
            'list': ('<ul>', '</ul>'),
            'olist': ('<ol>', '</ol>'),
            '*': ('<li>', '</li>'),
            
            # Alignment
            'center': ('<div style="text-align: center;">', '</div>'),
            'right': ('<div style="text-align: right;">', '</div>'),
            'left': ('<div style="text-align: left;">', '</div>'),
            
            # Quotes and code
            'quote': ('<blockquote class="bbcode-quote">', '</blockquote>'),
            'code': ('<pre class="bbcode-code">', '</pre>'),
            
            # Tables
            'table': ('<table class="bbcode-table">', '</table>'),
            'tr': ('<tr>', '</tr>'),
            'td': ('<td>', '</td>'),
            'th': ('<th>', '</th>'),
        }
    
    def parse(self, text):
        """Parse BBCode text and return safe HTML"""
        if not text:
            return ''
        
        # Escape HTML to prevent XSS
        text = escape(text)
        
        # Convert newlines to <br> tags
        text = text.replace('\n', '<br>')
        
        # Process color tags
        text = self._process_color_tags(text)
        
        # Process size tags
        text = self._process_size_tags(text)
        
        # Process URL tags
        text = self._process_url_tags(text)
        
        # Process simple tags
        for tag, (open_html, close_html) in self.tags.items():
            # Handle [tag] and [/tag]
            text = text.replace(f'[{tag}]', open_html)
            text = text.replace(f'[/{tag}]', close_html)
            
            # Handle [TAG] and [/TAG] (case insensitive)
            text = text.replace(f'[{tag.upper()}]', open_html)
            text = text.replace(f'[/{tag.upper()}]', close_html)
        
        return mark_safe(text)
    
    def _process_color_tags(self, text):
        """Process [color=X] tags"""
        # Allow only safe color values
        safe_colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'black', 'white', 'gray']
        
        def replace_color(match):
            color = match.group(1).lower()
            if color in safe_colors or (color.startswith('#') and len(color) == 7):
                return f'<span style="color: {color};">'
            return '<span>'
        
        text = re.sub(r'\[color=([^\]]+)\]', replace_color, text, flags=re.IGNORECASE)
        text = re.sub(r'\[/color\]', '</span>', text, flags=re.IGNORECASE)
        
        return text
    
    def _process_size_tags(self, text):
        """Process [size=X] tags"""
        def replace_size(match):
            size = match.group(1)
            try:
                size_int = int(size)
                if 1 <= size_int <= 7:
                    # Map 1-7 to reasonable em sizes
                    em_size = 0.7 + (size_int * 0.2)
                    return f'<span style="font-size: {em_size}em;">'
            except ValueError:
                pass
            return '<span>'
        
        text = re.sub(r'\[size=([^\]]+)\]', replace_size, text, flags=re.IGNORECASE)
        text = re.sub(r'\[/size\]', '</span>', text, flags=re.IGNORECASE)
        
        return text
    
    def _process_url_tags(self, text):
        """Process [url] and [url=X] tags"""
        # Simple [url]link[/url]
        text = re.sub(
            r'\[url\](https?://[^\[\]]+)\[/url\]',
            r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
            text,
            flags=re.IGNORECASE
        )
        
        # [url=link]text[/url]
        text = re.sub(
            r'\[url=(https?://[^\]]+)\]([^\[]+)\[/url\]',
            r'<a href="\1" target="_blank" rel="noopener noreferrer">\2</a>',
            text,
            flags=re.IGNORECASE
        )
        
        return text
    
    def get_preview_html(self):
        """Get HTML for BBCode reference"""
        return """
        <div class="bbcode-help">
            <h4>BBCode Reference</h4>
            <ul>
                <li><strong>Bold:</strong> [b]text[/b]</li>
                <li><strong>Italic:</strong> [i]text[/i]</li>
                <li><strong>Underline:</strong> [u]text[/u]</li>
                <li><strong>Strike:</strong> [s]text[/s]</li>
                <li><strong>Color:</strong> [color=red]text[/color]</li>
                <li><strong>Size:</strong> [size=3]text[/size] (1-7)</li>
                <li><strong>Center:</strong> [center]text[/center]</li>
                <li><strong>Quote:</strong> [quote]text[/quote]</li>
                <li><strong>Code:</strong> [code]text[/code]</li>
                <li><strong>URL:</strong> [url=http://example.com]link[/url]</li>
                <li><strong>List:</strong> [list][*]item 1[*]item 2[/list]</li>
            </ul>
        </div>
        """


# Vendor model extension methods
def add_bbcode_methods_to_vendor():
    """Add BBCode parsing methods to the Vendor model"""
    from .models import Vendor
    
    def get_parsed_profile_header(self):
        parser = BBCodeParser()
        return parser.parse(self.profile_header)
    
    def get_parsed_terms(self):
        parser = BBCodeParser()
        return parser.parse(self.terms_conditions)
    
    def get_parsed_shipping_info(self):
        parser = BBCodeParser()
        return parser.parse(self.shipping_info)
    
    def get_parsed_description(self):
        parser = BBCodeParser()
        return parser.parse(self.description)
    
    # Add methods to Vendor model
    Vendor.get_parsed_profile_header = get_parsed_profile_header
    Vendor.get_parsed_terms = get_parsed_terms
    Vendor.get_parsed_shipping_info = get_parsed_shipping_info
    Vendor.get_parsed_description = get_parsed_description