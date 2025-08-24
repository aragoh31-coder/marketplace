#!/usr/bin/env python3
"""
Minify and optimize static files for production
"""
import os
import sys
import gzip
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def minify_css(content):
    """Simple CSS minification"""
    # Remove comments
    import re
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Remove unnecessary whitespace
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\s*([{}:;,])\s*', r'\1', content)
    
    # Remove last semicolon before closing brace
    content = re.sub(r';\s*}', '}', content)
    
    # Remove unnecessary quotes
    content = re.sub(r'url\("([^"]+)"\)', r'url(\1)', content)
    content = re.sub(r"url\('([^']+)'\)", r'url(\1)', content)
    
    return content.strip()


def optimize_static_files():
    """Optimize all static files"""
    static_root = Path(__file__).parent.parent / 'static'
    
    if not static_root.exists():
        print(f"Static directory not found: {static_root}")
        return
    
    print(f"Optimizing static files in: {static_root}")
    
    # Process CSS files
    css_files = list(static_root.glob('**/*.css'))
    
    for css_file in css_files:
        if css_file.name.endswith('.min.css'):
            continue
            
        print(f"Processing: {css_file.relative_to(static_root)}")
        
        # Read original
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Minify
        minified = minify_css(content)
        
        # Save minified version
        min_file = css_file.with_suffix('.min.css')
        with open(min_file, 'w', encoding='utf-8') as f:
            f.write(minified)
        
        # Create gzipped version
        gz_file = min_file.with_suffix('.min.css.gz')
        with open(min_file, 'rb') as f_in:
            with gzip.open(gz_file, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Calculate savings
        original_size = len(content)
        minified_size = len(minified)
        gz_size = gz_file.stat().st_size
        
        print(f"  Original: {original_size:,} bytes")
        print(f"  Minified: {minified_size:,} bytes ({(1 - minified_size/original_size)*100:.1f}% reduction)")
        print(f"  Gzipped:  {gz_size:,} bytes ({(1 - gz_size/original_size)*100:.1f}% reduction)")
        
    print(f"\nProcessed {len(css_files)} CSS files")


def create_static_manifest():
    """Create a manifest of static files for cache busting"""
    static_root = Path(__file__).parent.parent / 'static'
    manifest_file = static_root / 'manifest.json'
    
    import json
    import hashlib
    
    manifest = {}
    
    for file_path in static_root.glob('**/*'):
        if file_path.is_file() and not file_path.name.startswith('.'):
            relative_path = file_path.relative_to(static_root)
            
            # Calculate file hash for cache busting
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()[:8]
            
            manifest[str(relative_path)] = {
                'hash': file_hash,
                'size': file_path.stat().st_size
            }
    
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nCreated static manifest with {len(manifest)} files")


if __name__ == '__main__':
    print("Static File Optimization Tool")
    print("="*50)
    
    optimize_static_files()
    create_static_manifest()
    
    print("\nOptimization complete!")