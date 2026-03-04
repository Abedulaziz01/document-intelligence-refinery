"""
PDF Utility Functions
Helper functions for analyzing PDF documents
"""

import pdfplumber
from typing import Tuple, Dict, Any, Optional
import re


def analyze_pdf_with_pdfplumber(pdf_path: str) -> Dict[str, Any]:
    """
    Analyze a PDF using pdfplumber to extract metrics
    
    Returns a dictionary with:
    - page_count: number of pages
    - total_chars: total characters in document
    - avg_char_density: average characters per page
    - image_count: number of images
    - image_to_page_ratio: ratio of image area to page area
    - has_text: whether text was found
    - fonts_found: list of fonts used
    """
    result = {
        'page_count': 0,
        'total_chars': 0,
        'avg_char_density': 0.0,
        'image_count': 0,
        'image_to_page_ratio': 0.0,
        'has_text': False,
        'fonts_found': [],
        'pages_with_text': 0,
        'pages_with_images': 0
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            result['page_count'] = len(pdf.pages)
            
            total_image_area = 0
            total_page_area = 0
            
            for page in pdf.pages:
                # Get page dimensions
                width = page.width or 612  # Default to letter size if None
                height = page.height or 792
                page_area = width * height
                total_page_area += page_area
                
                # Extract text
                text = page.extract_text() or ""
                if text:
                    result['has_text'] = True
                    result['pages_with_text'] += 1
                    result['total_chars'] += len(text)
                
                # Check for images
                images = page.images
                if images:
                    result['pages_with_images'] += 1
                    result['image_count'] += len(images)
                    
                    # Calculate image area
                    for img in images:
                        img_width = img.get('width', 0)
                        img_height = img.get('height', 0)
                        total_image_area += (img_width * img_height)
                
                # Extract font information
                if hasattr(page, 'chars') and page.chars:
                    fonts = set()
                    for char in page.chars:
                        if 'fontname' in char:
                            fonts.add(char['fontname'])
                    result['fonts_found'].extend(list(fonts))
            
            # Calculate ratios
            if result['page_count'] > 0:
                result['avg_char_density'] = result['total_chars'] / result['page_count']
                
            if total_page_area > 0:
                result['image_to_page_ratio'] = total_image_area / total_page_area
                
    except Exception as e:
        print(f"Error analyzing PDF: {e}")
    
    return result


def detect_origin_type(pdf_analysis: Dict[str, Any]) -> str:
    """
    Detect if document is native digital or scanned
    
    Rules:
    - If has_text AND image_to_page_ratio < 0.3: native_digital
    - If no_text OR image_to_page_ratio > 0.7: scanned_image
    - Otherwise: mixed
    """
    has_text = pdf_analysis['has_text']
    image_ratio = pdf_analysis['image_to_page_ratio']
    pages_with_text = pdf_analysis['pages_with_text']
    total_pages = pdf_analysis['page_count']
    
    # Calculate text coverage ratio
    text_coverage = pages_with_text / total_pages if total_pages > 0 else 0
    
    if has_text and image_ratio < 0.3 and text_coverage > 0.8:
        return "native_digital"
    elif (not has_text) or image_ratio > 0.7 or text_coverage < 0.2:
        return "scanned_image"
    else:
        return "mixed"


def detect_layout_complexity(pdf_analysis: Dict[str, Any]) -> str:
    """
    Detect layout complexity based on heuristics
    
    Returns: single_column, multi_column, table_heavy, figure_heavy, mixed
    """
    # This is a simplified version - you can make it more sophisticated
    image_ratio = pdf_analysis['image_to_page_ratio']
    image_count = pdf_analysis['image_count']
    
    # Heuristic rules
    if image_ratio > 0.5:
        return "figure_heavy"
    elif image_count > 10 and image_ratio > 0.3:
        return "mixed"
    elif pdf_analysis['total_chars'] > 10000:  # Lots of text
        return "single_column"  # Simplified - real detection needs column analysis
    else:
        return "mixed"


def detect_domain_hint(filename: str, text_sample: str = "") -> str:
    """
    Detect document domain based on filename and text content
    
    Returns: financial, legal, technical, medical, general
    """
    filename_lower = filename.lower()
    text_lower = text_sample.lower()
    
    # Financial keywords
    financial_keywords = ['financial', 'revenue', 'profit', 'loss', 'balance sheet', 
                         'income statement', 'cash flow', 'audit', 'tax', 'expense',
                         'fiscal', 'annual report', 'earnings']
    
    # Legal keywords
    legal_keywords = ['legal', 'law', 'court', 'plaintiff', 'defendant', 'contract',
                     'agreement', 'terms', 'conditions', 'liability', 'statute']
    
    # Technical keywords
    technical_keywords = ['technical', 'specification', 'manual', 'guide', 'reference',
                         'api', 'code', 'software', 'hardware', 'system']
    
    # Medical keywords
    medical_keywords = ['medical', 'patient', 'clinical', 'health', 'diagnosis',
                       'treatment', 'hospital', 'doctor', 'nurse', 'symptoms']
    
    # Check filename first
    for keyword in financial_keywords:
        if keyword in filename_lower:
            return "financial"
    
    for keyword in legal_keywords:
        if keyword in filename_lower:
            return "legal"
    
    for keyword in technical_keywords:
        if keyword in filename_lower:
            return "technical"
    
    for keyword in medical_keywords:
        if keyword in filename_lower:
            return "medical"
    
    # If no match in filename, check text sample (first 1000 chars)
    if text_sample:
        text_preview = text_lower[:1000]
        for keyword in financial_keywords:
            if keyword in text_preview:
                return "financial"
        for keyword in legal_keywords:
            if keyword in text_preview:
                return "legal"
        for keyword in technical_keywords:
            if keyword in text_preview:
                return "technical"
        for keyword in medical_keywords:
            if keyword in text_preview:
                return "medical"
    
    return "general"


def estimate_extraction_cost(origin_type: str, layout_complexity: str) -> str:
    """
    Determine which extraction strategy to use based on classification
    
    Returns: fast_text_sufficient, needs_layout_model, needs_vision_model
    """
    if origin_type == "scanned_image":
        return "needs_vision_model"
    elif origin_type == "mixed" and layout_complexity in ["multi_column", "table_heavy"]:
        return "needs_layout_model"
    elif origin_type == "native_digital" and layout_complexity == "single_column":
        return "fast_text_sufficient"
    else:
        return "needs_layout_model"


def extract_first_page_text(pdf_path: str) -> str:
    """Extract text from first page for domain detection"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) > 0:
                return pdf.pages[0].extract_text() or ""
    except:
        pass
    return ""