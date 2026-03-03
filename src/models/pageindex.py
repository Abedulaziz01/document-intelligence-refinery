"""
PageIndex Model
A hierarchical navigation structure for documents
Inspired by VectifyAI's PageIndex concept
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum  # 👈 Add this import (you were missing it!)


class DataType(str, Enum):
    """Types of data present in a section"""
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"
    EQUATION = "equation"
    CODE = "code"
    LIST = "list"


class SectionNode(BaseModel):
    """
    A single node in the PageIndex tree
    Represents a section or subsection
    """
    
    # Identification
    section_id: str = Field(..., description="Unique section identifier")
    title: str = Field(..., description="Section title")
    level: int = Field(..., description="Heading level (1, 2, 3, etc.)")
    
    # Location
    page_start: int = Field(..., description="Starting page")
    page_end: int = Field(..., description="Ending page")
    
    # Content summary
    summary: Optional[str] = Field(None, description="LLM-generated section summary")
    key_entities: List[str] = Field(default_factory=list, description="Named entities found")
    data_types_present: List[DataType] = Field(default_factory=list)
    
    # Statistics
    chunk_count: int = Field(0, description="Number of LDUs in this section")
    table_count: int = Field(0, description="Number of tables")
    figure_count: int = Field(0, description="Number of figures")
    
    # Navigation
    parent_id: Optional[str] = Field(None, description="Parent section ID")
    child_sections: List['SectionNode'] = Field(default_factory=list, description="Subsections")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # 👇 FIXED: Replaced class Config with model_config
    model_config = ConfigDict(
        use_enum_values=True,
        arbitrary_types_allowed=True
    )
    
    def has_children(self) -> bool:
        """Does this section have subsections?"""
        return len(self.child_sections) > 0
    
    def total_pages(self) -> int:
        """Calculate total pages in this section"""
        return self.page_end - self.page_start + 1


# This forward reference is needed for self-referential model
SectionNode.update_forward_refs()


class PageIndex(BaseModel):
    """
    Complete PageIndex tree for a document
    Enables navigation without vector search
    """
    
    # Document info
    doc_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    total_pages: int = Field(..., description="Total document pages")
    
    # Root of the tree
    root_sections: List[SectionNode] = Field(default_factory=list, description="Top-level sections")
    
    # Flat list for quick lookup
    section_by_id: Dict[str, SectionNode] = Field(default_factory=dict)
    
    # Statistics
    total_sections: int = Field(0, description="Total number of sections")
    max_depth: int = Field(0, description="Maximum nesting depth")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 👇 FIXED: Replaced class Config with model_config
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
    
    def dict_for_json(self):
        """Convert to dict for JSON serialization"""
        data = self.model_dump()  # 👈 Note: In V2, .dict() becomes .model_dump()
        data['created_at'] = self.created_at.isoformat()
        return data
    
    def find_section_by_title(self, title_substring: str) -> List[SectionNode]:
        """Find sections containing a title substring"""
        results = []
        for section_id, section in self.section_by_id.items():
            if title_substring.lower() in section.title.lower():
                results.append(section)
        return results
    
    def get_path_to_section(self, section_id: str) -> List[SectionNode]:
        """Get the hierarchical path to a section"""
        path = []
        current = self.section_by_id.get(section_id)
        
        while current:
            path.insert(0, current)  # Insert at beginning
            if current.parent_id:
                current = self.section_by_id.get(current.parent_id)
            else:
                current = None
        
        return path