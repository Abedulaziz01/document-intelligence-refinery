"""
Logical Document Unit (LDU) Model
Represents a semantically coherent chunk of a document
"""
from enum import Enum  
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from src.models.extracted_document import BoundingBox
from src.models.extracted_document import ExtractedTable


class ChunkType(str, Enum):
    """What kind of content is in this chunk?"""
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"
    LIST = "list"
    HEADER = "header"
    FOOTER = "footer"
    SECTION = "section"
    MIXED = "mixed"


class LDU(BaseModel):
    """
    Logical Document Unit
    A self-contained, semantically meaningful chunk
    """
    
    # Identification
    ldu_id: str = Field(..., description="Unique chunk identifier")
    doc_id: str = Field(..., description="Source document ID")
    chunk_type: ChunkType = Field(..., description="Type of content")
    
    # Content
    content: str = Field(..., description="The actual text content")
    content_hash: str = Field(..., description="Hash of content + location (for verification)")
    
    # Structure
    tables: List[ExtractedTable] = Field(default_factory=list, description="Tables in this chunk")
    
    # Location
    page_refs: List[int] = Field(..., description="Pages this chunk spans")
    bbox: Optional[BoundingBox] = Field(None, description="Primary location on first page")
    
    # Context
    parent_section: Optional[str] = Field(None, description="Section this belongs to")
    section_hierarchy: List[str] = Field(default_factory=list, description="Full section path")
    
    # Relationships
    previous_chunk_id: Optional[str] = Field(None, description="Previous chunk in reading order")
    next_chunk_id: Optional[str] = Field(None, description="Next chunk in reading order")
    related_chunk_ids: List[str] = Field(default_factory=list, description="Other related chunks")
    
    # Metrics
    token_count: int = Field(..., description="Number of tokens (for RAG limits)")
    char_count: int = Field(..., description="Number of characters")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
    
    def dict_for_json(self):
        """Convert to dict for JSON serialization"""
        data = self.dict()
        data['created_at'] = self.created_at.isoformat()
        return data
    
    def verify_hash(self) -> bool:
        """
        Verify that the content hasn't changed
        This is used for audit mode
        """
        # We'll implement actual hash verification later
        return True