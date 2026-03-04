"""
Confidence Scoring Utilities
Calculate confidence scores for extraction results
"""

from src.models.extracted_document import ExtractedDocument


def calculate_text_confidence(extracted_doc: ExtractedDocument) -> float:
    """
    Calculate confidence for fast text extraction
    
    Factors:
    - Text density
    - Table extraction success
    - Page coverage
    """
    if not extracted_doc.text_blocks and not extracted_doc.tables:
        return 0.0
    
    score = 0.0
    factors = 0
    
    # Factor 1: Text presence
    if extracted_doc.text_blocks:
        text_score = min(1.0, len(extracted_doc.text_blocks) / extracted_doc.page_count)
        score += text_score * 0.4  # 40% weight
        factors += 0.4
    
    # Factor 2: Table detection
    if extracted_doc.tables:
        table_score = min(1.0, len(extracted_doc.tables) / extracted_doc.page_count)
        score += table_score * 0.3  # 30% weight
        factors += 0.3
    
    # Factor 3: Page coverage
    if extracted_doc.page_count > 0:
        coverage = len(extracted_doc.text_blocks) / extracted_doc.page_count
        score += min(1.0, coverage) * 0.3  # 30% weight
        factors += 0.3
    
    return score / factors if factors > 0 else 0.0


def calculate_layout_confidence(extracted_doc: ExtractedDocument) -> float:
    """
    Calculate confidence for layout-aware extraction
    
    Layout extraction is trusted more for tables
    """
    if not extracted_doc.text_blocks and not extracted_doc.tables:
        return 0.0
    
    score = 0.0
    factors = 0
    
    # Factor 1: Table quality
    if extracted_doc.tables:
        # Check if tables have headers and data
        good_tables = 0
        for table in extracted_doc.tables:
            if table.headers and len(table.rows) > 0:
                good_tables += 1
        
        table_score = good_tables / len(extracted_doc.tables) if extracted_doc.tables else 0
        score += table_score * 0.5  # 50% weight
        factors += 0.5
    
    # Factor 2: Text block structure
    if extracted_doc.text_blocks:
        # Count blocks with good bounding boxes
        good_blocks = sum(1 for block in extracted_doc.text_blocks 
                         if block.bbox and block.bbox.area > 0)
        block_score = good_blocks / len(extracted_doc.text_blocks) if extracted_doc.text_blocks else 0
        score += block_score * 0.3  # 30% weight
        factors += 0.3
    
    # Factor 3: Page count match
    if extracted_doc.page_count > 0:
        page_coverage = len(extracted_doc.text_blocks) / extracted_doc.page_count
        score += min(1.0, page_coverage) * 0.2  # 20% weight
        factors += 0.2
    
    return score / factors if factors > 0 else 0.0


def calculate_vision_confidence(extracted_doc: ExtractedDocument) -> float:
    """
    Calculate confidence for vision extraction
    
    Vision is trusted highly but we check for completeness
    """
    if not extracted_doc.text_blocks and not extracted_doc.tables:
        return 0.0
    
    # Vision extraction is generally high confidence
    base_confidence = 0.9
    
    # Reduce confidence if missing expected content
    if extracted_doc.page_count > 0:
        coverage = len(extracted_doc.text_blocks) / extracted_doc.page_count
        if coverage < 0.5:
            base_confidence *= 0.8  # Penalize low coverage
    
    return base_confidence


def should_escalate(confidence: float, threshold: float = 0.6) -> bool:
    """
    Determine if extraction should escalate to next strategy
    
    Args:
        confidence: Current strategy confidence
        threshold: Minimum acceptable confidence
        
    Returns:
        True if confidence below threshold
    """
    return confidence < threshold