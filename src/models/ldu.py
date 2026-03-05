"""
Logical Document Unit (LDU) Model
Represents a semantically coherent chunk of a document
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
from pydantic import BaseModel, Field

from src.models.extracted_document import BoundingBox, ExtractedTable


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
    CAPTION = "caption"
    EQUATION = "equation"


class ChunkRelationship(str, Enum):
    """Types of relationships between chunks"""
    NEXT = "next"
    PREVIOUS = "previous"
    PARENT = "parent"
    CHILD = "child"
    REFERENCES = "references"
    REFERENCED_BY = "referenced_by"
    CONTINUATION = "continuation"


class CrossReference(BaseModel):
    """A reference to another chunk (like 'see Table 3')"""
    reference_text: str = Field(..., description="The reference text")
    target_id: Optional[str] = Field(None, description="ID of referenced chunk")
    target_type: Optional[str] = Field(None, description="Type of referenced chunk")
    resolved: bool = Field(False, description="Whether reference was resolved")
    page_number: int = Field(..., description="Page where reference appears")


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
    
    # Context (Section Hierarchy)
    section_hierarchy: List[str] = Field(
        default_factory=list, 
        description="Full section path e.g., ['Chapter 1', 'Section 1.1', 'Subsection A']"
    )
    section_headers: List[str] = Field(
        default_factory=list,
        description="All headers that apply to this chunk"
    )
    
    # Relationships
    previous_chunk_id: Optional[str] = Field(None, description="Previous chunk in reading order")
    next_chunk_id: Optional[str] = Field(None, description="Next chunk in reading order")
    parent_chunk_id: Optional[str] = Field(None, description="Parent chunk (e.g., section header)")
    child_chunk_ids: List[str] = Field(default_factory=list, description="Child chunks")
    
    # Cross References
    references: List[CrossReference] = Field(
        default_factory=list, 
        description="References to other chunks"
    )
    referenced_by: List[str] = Field(
        default_factory=list,
        description="IDs of chunks that reference this"
    )
    
    # Metrics
    token_count: int = Field(..., description="Number of tokens (for RAG limits)")
    char_count: int = Field(..., description="Number of characters")
    word_count: int = Field(..., description="Number of words")
    
    # Validation Flags (for chunking rules)
    rule_compliance: Dict[str, bool] = Field(
        default_factory=dict,
        description="Which chunking rules this chunk satisfies"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        arbitrary_types_allowed = True
    
    def dict_for_json(self):
        """Convert to dict for JSON serialization"""
        data = self.dict()
        data['created_at'] = self.created_at.isoformat()
        
        # Convert enums to strings
        if 'chunk_type' in data and hasattr(self.chunk_type, 'value'):
            data['chunk_type'] = self.chunk_type.value
        
        return data
    
    def verify_hash(self) -> bool:
        """
        Verify that the content hasn't changed
        This is used for audit mode
        """
        from src.utils.hashing import generate_chunk_hash
        expected_hash = generate_chunk_hash(
            content=self.content,
            page_refs=self.page_refs,
            bbox=self.bbox
        )
        return self.content_hash == expected_hash
    
    def get_summary(self, max_length: int = 100) -> str:
        """Get a brief summary of the chunk"""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
    
    def add_reference(self, reference: CrossReference):
        """Add a cross reference"""
        self.references.append(reference)
    
    def resolve_reference(self, reference_text: str, target_id: str):
        """Resolve a reference by linking to target chunk"""
        for ref in self.references:
            if ref.reference_text == reference_text and not ref.resolved:
                ref.target_id = target_id
                ref.resolved = True
                break