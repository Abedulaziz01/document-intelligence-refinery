"""
PageIndex Model
A hierarchical navigation structure for documents
Inspired by VectifyAI's PageIndex concept
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
from pydantic import BaseModel, Field


class DataType(str, Enum):
    """Types of data present in a section"""
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"
    EQUATION = "equation"
    CODE = "code"
    LIST = "list"
    CHART = "chart"
    FOOTNOTE = "footnote"


class EntityType(str, Enum):
    """Types of entities that can be extracted"""
    PERSON = "person"
    ORGANIZATION = "organization"
    DATE = "date"
    MONEY = "money"
    PERCENTAGE = "percentage"
    LOCATION = "location"
    PRODUCT = "product"
    LAW = "law"
    REGULATION = "regulation"
    METRIC = "metric"


class ExtractedEntity(BaseModel):
    """A named entity extracted from text"""
    text: str = Field(..., description="The entity text")
    entity_type: EntityType = Field(..., description="Type of entity")
    confidence: float = Field(..., description="Confidence score 0-1")
    mentions: List[int] = Field(default_factory=list, description="Pages where mentioned")


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
    
    # Content summary (LLM generated)
    summary: Optional[str] = Field(None, description="LLM-generated section summary")
    summary_confidence: Optional[float] = Field(None, description="Confidence in summary")
    
    # Entities found in this section
    entities: List[ExtractedEntity] = Field(default_factory=list, description="Named entities")
    key_entities: List[str] = Field(default_factory=list, description="Most important entities (simplified)")
    
    # Content types present
    data_types_present: List[DataType] = Field(default_factory=list)
    
    # Statistics
    chunk_count: int = Field(0, description="Number of LDUs in this section")
    table_count: int = Field(0, description="Number of tables")
    figure_count: int = Field(0, description="Number of figures")
    word_count: int = Field(0, description="Approximate word count")
    
    # Navigation
    parent_id: Optional[str] = Field(None, description="Parent section ID")
    child_sections: List['SectionNode'] = Field(default_factory=list, description="Subsections")
    path: List[str] = Field(default_factory=list, description="Full path of section titles")
    
    # For quick lookup
    all_chunk_ids: List[str] = Field(default_factory=list, description="All chunks in this section")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        arbitrary_types_allowed = True
    
    def has_children(self) -> bool:
        """Does this section have subsections?"""
        return len(self.child_sections) > 0
    
    def total_pages(self) -> int:
        """Calculate total pages in this section"""
        return self.page_end - self.page_start + 1
    
    def get_depth(self) -> int:
        """Get nesting depth of this section"""
        return len(self.path)
    
    def dict_for_json(self):
        """Convert to dict for JSON serialization"""
        data = self.dict()
        data['created_at'] = self.created_at.isoformat()
        
        # Convert enums to strings
        if 'data_types_present' in data:
            data['data_types_present'] = [dt.value if hasattr(dt, 'value') else dt for dt in self.data_types_present]
        
        return data


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
    
    # Global entities (across entire document)
    global_entities: List[ExtractedEntity] = Field(default_factory=list)
    
    # Content summary for entire document
    document_summary: Optional[str] = Field(None, description="Overall document summary")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    version: str = Field("1.0", description="PageIndex version")
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = True
    
    def dict_for_json(self):
        """Convert to dict for JSON serialization"""
        data = self.dict()
        data['created_at'] = self.created_at.isoformat()
        return data
    
    def find_section_by_title(self, title_substring: str) -> List[SectionNode]:
        """Find sections containing a title substring"""
        results = []
        for section_id, section in self.section_by_id.items():
            if title_substring.lower() in section.title.lower():
                results.append(section)
        return results
    
    def find_sections_by_entity(self, entity_text: str) -> List[SectionNode]:
        """Find sections containing a specific entity"""
        results = []
        for section_id, section in self.section_by_id.items():
            for entity in section.entities:
                if entity_text.lower() in entity.text.lower():
                    results.append(section)
                    break
        return results
    
    def find_sections_by_type(self, data_type: DataType) -> List[SectionNode]:
        """Find sections containing a specific data type"""
        results = []
        for section_id, section in self.section_by_id.items():
            if data_type in section.data_types_present:
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
    
    def print_tree(self, sections: Optional[List[SectionNode]] = None, level: int = 0):
        """Print the tree structure (for debugging)"""
        if sections is None:
            sections = self.root_sections
        
        for section in sections:
            indent = "  " * level
            types = ", ".join([dt.value if hasattr(dt, 'value') else str(dt) for dt in section.data_types_present])
            print(f"{indent}📁 {section.title} (pp {section.page_start}-{section.page_end}) [{types}]")
            
            if section.child_sections:
                self.print_tree(section.child_sections, level + 1)