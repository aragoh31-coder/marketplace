#!/usr/bin/env python3
"""
Script to optimize static files for production
"""
import os
import re
import gzip
import shutil
from pathlib import Path


def minify_css(content):
    """Simple CSS minification"""
    # Remove comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Remove unnecessary whitespace
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\s*([{}:;,])\s*', r'\1', content)
    # Remove trailing semicolons before }
    content = re.sub(r';\s*}', '}', content)
    # Remove unnecessary quotes
    content = re.sub(r'url\((["\'])([^"\']+)\1\)', r'url(\2)', content)
    return content.strip()


def optimize_css_file(file_path):
    """Optimize a single CSS file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Minify
    minified = minify_css(content)
    
    # Save minified version
    min_path = file_path.replace('.css', '.min.css')
    with open(min_path, 'w', encoding='utf-8') as f:
        f.write(minified)
    
    # Create gzipped version
    gz_path = min_path + '.gz'
    with open(min_path, 'rb') as f_in:
        with gzip.open(gz_path, 'wb', compresslevel=9) as f_out:
            f_out.write(f_in.read())
    
    # Calculate savings
    original_size = len(content)
    minified_size = len(minified)
    gz_size = os.path.getsize(gz_path)
    
    savings_percent = ((original_size - minified_size) / original_size) * 100
    gz_savings_percent = ((original_size - gz_size) / original_size) * 100
    
    return {
        'original': original_size,
        'minified': minified_size,
        'gzipped': gz_size,
        'savings': savings_percent,
        'gz_savings': gz_savings_percent
    }


def optimize_static_files():
    """Optimize all static files"""
    static_dir = Path('/workspace/static')
    css_files = list(static_dir.rglob('*.css'))
    
    # Skip already minified files
    css_files = [f for f in css_files if '.min.css' not in str(f)]
    
    total_original = 0
    total_minified = 0
    total_gzipped = 0
    
    print("🔧 Optimizing CSS files...\n")
    
    for css_file in css_files:
        print(f"Processing: {css_file.name}")
        result = optimize_css_file(str(css_file))
        
        total_original += result['original']
        total_minified += result['minified']
        total_gzipped += result['gzipped']
        
        print(f"  Original: {result['original']:,} bytes")
        print(f"  Minified: {result['minified']:,} bytes (-{result['savings']:.1f}%)")
        print(f"  Gzipped:  {result['gzipped']:,} bytes (-{result['gz_savings']:.1f}%)\n")
    
    if css_files:
        total_savings = ((total_original - total_minified) / total_original) * 100
        total_gz_savings = ((total_original - total_gzipped) / total_original) * 100
        
        print("📊 Total Optimization Results:")
        print(f"  Files processed: {len(css_files)}")
        print(f"  Original size: {total_original:,} bytes")
        print(f"  Minified size: {total_minified:,} bytes (-{total_savings:.1f}%)")
        print(f"  Gzipped size:  {total_gzipped:,} bytes (-{total_gz_savings:.1f}%)")
    else:
        print("No CSS files found to optimize.")


if __name__ == '__main__':
    optimize_static_files()