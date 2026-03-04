"""
Layout-Aware Extraction Strategy (Strategy B)
Uses advanced layout detection for complex documents
Cost: Free (using open-source tools)
"""

import pdfplumber
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from src.strategies.base_strategy import BaseExtractionStrategy
from src.models.extracted_document import (
    ExtractedDocument, TextBlock, BoundingBox,
    ExtractedTable, TableCell
)
from src.utils.confidence import calculate_layout_confidence


class LayoutAwareExtractor(BaseExtractionStrategy):
    """
    Layout-aware extraction using advanced PDF parsing
    Best for: multi-column, table-heavy, mixed layout docs
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.name = "layout_aware"
    
    def extract(self, pdf_path: str, doc_id: str) -> ExtractedDocument:
        """
        Extract content with layout awareness
        """
        start_time = datetime.now()
        
        pdf_path_obj = Path(pdf_path)
        filename = pdf_path_obj.name
        
        text_blocks = []
        tables = []
        page_count = 0
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    # Get page dimensions
                    width = page.width or 612
                    height = page.height or 792
                    
                    # Extract tables with better detection
                    page_tables = page.extract_tables({
                        'vertical_strategy': 'text',
                        'horizontal_strategy': 'text',
                        'intersection_tolerance': 5
                    })
                    
                    for table_data in page_tables:
                        if table_data and len(table_data) > 1:  # At least header + 1 row
                            table = self._create_table(table_data, page_num, page)
                            if table:
                                tables.append(table)
                    
                    # Extract text with better positioning
                    words = page.extract_words(
                        keep_blank_chars=False,
                        use_text_flow=True,
                        extra_attrs=['fontname', 'size']
                    )
                    
                    # Group words into paragraphs based on position
                    if words:
                        current_block = []
                        last_y = None
                        block_y_threshold = height * 0.02  # 2% of page height
                        
                        for word in words:
                            word_y = word['top']
                            
                            if last_y is None or abs(word_y - last_y) < block_y_threshold:
                                current_block.append(word)
                            else:
                                # Save current block
                                if current_block:
                                    block = self._create_text_block(current_block, page_num, page)
                                    if block:
                                        text_blocks.append(block)
                                current_block = [word]
                            
                            last_y = word_y
                        
                        # Save last block
                        if current_block:
                            block = self._create_text_block(current_block, page_num, page)
                            if block:
                                text_blocks.append(block)
            
            # Create extracted document
            extracted_doc = ExtractedDocument(
                doc_id=doc_id,
                filename=filename,
                page_count=page_count,
                strategy_used=self.name,
                overall_confidence=0.0,
                text_blocks=text_blocks,
                tables=tables
            )
            
            # Calculate confidence
            confidence = self.calculate_confidence(extracted_doc)
            extracted_doc.overall_confidence = confidence
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            extracted_doc.extraction_time_ms = processing_time
            
            return extracted_doc
            
        except Exception as e:
            print(f"❌ Error in LayoutAwareExtractor: {e}")
            return ExtractedDocument(
                doc_id=doc_id,
                filename=filename,
                page_count=0,
                strategy_used=self.name,
                overall_confidence=0.0
            )
    
    def _create_text_block(self, words: List[Dict], page_num: int, page) -> Optional[TextBlock]:
        """Create a text block from a group of words"""
        if not words:
            return None
        
        # Combine text
        text = " ".join([word['text'] for word in words])
        
        # Calculate bounding box
        x0 = min(word['x0'] for word in words)
        y0 = min(word['top'] for word in words)
        x1 = max(word['x1'] for word in words)
        y1 = max(word['bottom'] for word in words)
        
        bbox = BoundingBox(
            page_number=page_num,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1
        )
        
        # Determine block type (simplified)
        if len(words) < 5 and any(word.get('size', 12) > 14 for word in words):
            block_type = "header"
        else:
            block_type = "paragraph"
        
        return TextBlock(
            text=text,
            bbox=bbox,
            block_type=block_type,
            confidence=0.85
        )
    
    def _create_table(self, table_data: List[List], page_num: int, page) -> Optional[ExtractedTable]:
        """Create enhanced table from extracted data"""
        if not table_data or len(table_data) < 2:
            return None
        
        # First row as headers
        headers = [str(cell) if cell else "" for cell in table_data[0]]
        
        # Create rows
        rows = []
        for row_idx, row in enumerate(table_data[1:], 1):  # Skip header row
            row_cells = []
            for col_idx, cell in enumerate(row):
                cell_obj = TableCell(
                    text=str(cell) if cell else "",
                    row_index=row_idx,
                    col_index=col_idx,
                    row_header=False,
                    col_header=False
                )
                row_cells.append(cell_obj)
            rows.append(row_cells)
        
        # Estimate bounding box
        bbox = BoundingBox(
            page_number=page_num,
            x0=0,  # Simplified - would need actual table position
            y0=0,
            x1=page.width or 612,
            y1=page.height or 792
        )
        
        import hashlib
        table_id = hashlib.md5(f"{page_num}_{len(table_data)}".encode()).hexdigest()[:8]
        
        return ExtractedTable(
            id=table_id,
            caption=f"Table on page {page_num}",
            headers=headers,
            rows=rows,
            bbox=bbox,
            confidence=0.85
        )
    
    def calculate_confidence(self, extracted_doc: ExtractedDocument) -> float:
        """Calculate confidence for layout-aware extraction"""
        return calculate_layout_confidence(extracted_doc)