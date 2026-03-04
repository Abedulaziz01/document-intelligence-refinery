"""
Fast Text Extraction Strategy (Strategy A)
Uses pdfplumber for simple digital documents
Cost: Free
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
from src.utils.confidence import calculate_text_confidence


class FastTextExtractor(BaseExtractionStrategy):
    """
    Fast text extraction using pdfplumber
    Best for: native digital, single column, text-heavy docs
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.name = "fast_text"
    
    def extract(self, pdf_path: str, doc_id: str) -> ExtractedDocument:
        """
        Extract text using pdfplumber
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
                    # Extract text with position
                    words = page.extract_words()
                    
                    # Group words into text blocks (simplified)
                    if words:
                        # Get page dimensions
                        width = page.width or 612
                        height = page.height or 792
                        
                        # Create a text block for the whole page (simplified)
                        text = page.extract_text() or ""
                        
                        if text.strip():
                            bbox = BoundingBox(
                                page_number=page_num,
                                x0=0,
                                y0=0,
                                x1=width,
                                y1=height
                            )
                            
                            text_block = TextBlock(
                                text=text,
                                bbox=bbox,
                                block_type="paragraph",
                                confidence=0.8  # Base confidence
                            )
                            text_blocks.append(text_block)
                    
                    # Try to extract tables
                    page_tables = page.extract_tables()
                    for table_data in page_tables:
                        if table_data and len(table_data) > 0:
                            table = self._convert_to_extracted_table(
                                table_data, page_num, page
                            )
                            if table:
                                tables.append(table)
            
            # Create extracted document
            extracted_doc = ExtractedDocument(
                doc_id=doc_id,
                filename=filename,
                page_count=page_count,
                strategy_used=self.name,
                overall_confidence=0.0,  # Will be set after calculation
                text_blocks=text_blocks,
                tables=tables
            )
            
            # Calculate confidence
            confidence = self.calculate_confidence(extracted_doc)
            extracted_doc.overall_confidence = confidence
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            extracted_doc.extraction_time_ms = processing_time
            
            return extracted_doc
            
        except Exception as e:
            print(f"❌ Error in FastTextExtractor: {e}")
            # Return empty document on error
            return ExtractedDocument(
                doc_id=doc_id,
                filename=filename,
                page_count=0,
                strategy_used=self.name,
                overall_confidence=0.0
            )
    
    def _convert_to_extracted_table(self, table_data: List[List], 
                                   page_num: int, page) -> Optional[ExtractedTable]:
        """Convert pdfplumber table to ExtractedTable"""
        if not table_data or len(table_data) < 1:
            return None
        
        # Use first row as headers
        headers = [str(cell) if cell else "" for cell in table_data[0]]
        
        # Create cells for all rows
        rows = []
        for row_idx, row in enumerate(table_data):
            row_cells = []
            for col_idx, cell in enumerate(row):
                cell_obj = TableCell(
                    text=str(cell) if cell else "",
                    row_index=row_idx,
                    col_index=col_idx,
                    row_header=(row_idx == 0),  # First row is header
                    col_header=False
                )
                row_cells.append(cell_obj)
            rows.append(row_cells)
        
        # Create bounding box (simplified - whole page)
        bbox = BoundingBox(
            page_number=page_num,
            x0=0,
            y0=0,
            x1=page.width or 612,
            y1=page.height or 792
        )
        
        import hashlib
        table_id = hashlib.md5(f"{page_num}_{len(table_data)}".encode()).hexdigest()[:8]
        
        return ExtractedTable(
            id=table_id,
            headers=headers,
            rows=rows,
            bbox=bbox,
            confidence=0.7  # Base confidence for tables
        )
    
    def calculate_confidence(self, extracted_doc: ExtractedDocument) -> float:
        """Calculate confidence score for extraction"""
        return calculate_text_confidence(extracted_doc)