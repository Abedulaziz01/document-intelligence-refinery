"""
Extracted Document Model
Normalized output from any extraction strategy
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Spatial location on a page (in points, 72 points per inch)"""
    page_number: int = Field(..., description="Page number (1-indexed)")
    x0: float = Field(..., description="Left coordinate")
    y0: float = Field(..., description="Top coordinate (from bottom)")
    x1: float = Field(..., description="Right coordinate")
    y1: float = Field(..., description="Bottom coordinate")
    
    @property
    def width(self) -> float:
        """Calculate width"""
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        """Calculate height"""
        return self.y1 - self.y0
    
    @property
    def area(self) -> float:
        """Calculate area"""
        return self.width * self.height


class TextBlock(BaseModel):
    """A block of text with its location"""
    text: str = Field(..., description="The actual text")
    bbox: BoundingBox = Field(..., description="Location on page")
    block_type: str = Field("paragraph", description="paragraph, header, footer, etc.")
    confidence: float = Field(1.0, description="Extraction confidence (0-1)")


class TableCell(BaseModel):
    """A single cell in a table"""
    text: str = Field("", description="Cell content")
    row_index: int = Field(..., description="Row number (0-indexed)")
    col_index: int = Field(..., description="Column number (0-indexed)")
    row_header: bool = Field(False, description="Is this a row header?")
    col_header: bool = Field(False, description="Is this a column header?")
    bbox: Optional[BoundingBox] = Field(None, description="Cell location")


class ExtractedTable(BaseModel):
    """A complete table extracted from the document"""
    id: str = Field(..., description="Unique table ID")
    caption: Optional[str] = Field(None, description="Table caption")
    headers: List[str] = Field(default_factory=list, description="Column headers")
    rows: List[List[TableCell]] = Field(..., description="Table data rows")
    bbox: BoundingBox = Field(..., description="Table location")
    confidence: float = Field(1.0, description="Extraction confidence")
    
    def to_markdown(self) -> str:
        """Convert table to markdown format"""
        if not self.rows:
            return ""
        
        # Build markdown table
        lines = []
        
        # Add headers if they exist
        if self.headers:
            lines.append("| " + " | ".join(self.headers) + " |")
            lines.append("|" + "|".join([" --- "] * len(self.headers)) + "|")
        
        # Add data rows
        for row in self.rows:
            row_text = [cell.text for cell in row]
            lines.append("| " + " | ".join(row_text) + " |")
        
        return "\n".join(lines)


class ExtractedFigure(BaseModel):
    """A figure or image with its caption"""
    id: str = Field(..., description="Unique figure ID")
    caption: Optional[str] = Field(None, description="Figure caption")
    image_path: Optional[str] = Field(None, description="Path to extracted image")
    bbox: BoundingBox = Field(..., description="Figure location")
    confidence: float = Field(1.0, description="Extraction confidence")


class ExtractedDocument(BaseModel):
    """
    Normalized document representation from ANY extraction strategy
    All strategies must output this format
    """
    
    # Basic Info
    doc_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    page_count: int = Field(..., description="Total pages")
    
    # Strategy used
    strategy_used: str = Field(..., description="Which strategy extracted this")
    overall_confidence: float = Field(..., description="Overall confidence score")
    
    # Content (at least one should be populated)
    text_blocks: List[TextBlock] = Field(default_factory=list)
    tables: List[ExtractedTable] = Field(default_factory=list)
    figures: List[ExtractedFigure] = Field(default_factory=list)
    
    # Reading order (list of content IDs in order)
    reading_order: List[str] = Field(default_factory=list)
    
    # Metadata
    extracted_at: datetime = Field(default_factory=datetime.now)
    extraction_time_ms: Optional[float] = Field(None)
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = True
    
    def dict_for_json(self):
        """Convert to dict for JSON serialization"""
        data = self.dict()
        data['extracted_at'] = self.extracted_at.isoformat()
        return data