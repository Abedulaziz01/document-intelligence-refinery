"""
Provenance Models
Track the source of every extracted fact
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from src.models.extracted_document import BoundingBox


class SourceCitation(BaseModel):
    """
    A single source citation
    Points to exactly where information came from
    """
    
    # Document identification
    document_name: str = Field(..., description="Name of source document")
    document_id: str = Field(..., description="Unique document ID")
    
    # Location
    page_number: int = Field(..., description="Page where fact was found")
    bbox: Optional[BoundingBox] = Field(None, description="Exact location on page")
    
    # Content verification
    content_hash: str = Field(..., description="Hash of source content")
    extracted_text: str = Field(..., description="The actual text that was extracted")
    
    # Extraction info
    strategy_used: str = Field(..., description="Which strategy extracted this")
    confidence: float = Field(..., description="Confidence score")
    
    # Metadata
    extracted_at: datetime = Field(default_factory=datetime.now)


class ProvenanceChain(BaseModel):
    """
    A chain of sources supporting an answer
    Every answer from the Query Agent must include this
    """
    
    # The claim being supported
    claim: str = Field(..., description="The answer or fact")
    
    # Sources
    primary_source: SourceCitation = Field(..., description="Main source")
    supporting_sources: List[SourceCitation] = Field(
        default_factory=list, 
        description="Additional sources"
    )
    
    # Verification
    is_verified: bool = Field(False, description="Whether claim could be verified")
    verification_method: Optional[str] = Field(None, description="How it was verified")
    
    # For multi-document queries
    all_sources: List[SourceCitation] = Field(default_factory=list)
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = True
    
    def dict_for_json(self):
        """Convert to dict for JSON serialization"""
        data = self.dict()
        if self.primary_source:
            data['primary_source'] = self.primary_source.dict()
        data['supporting_sources'] = [s.dict() for s in self.supporting_sources]
        data['all_sources'] = [s.dict() for s in self.all_sources]
        return data
    
    def to_markdown(self) -> str:
        """Format as markdown for display"""
        lines = []
        lines.append(f"**Claim:** {self.claim}")
        lines.append("")
        lines.append("**Sources:**")
        lines.append(f"1. Primary: {self.primary_source.document_name}, page {self.primary_source.page_number}")
        
        for i, source in enumerate(self.supporting_sources, 2):
            lines.append(f"{i}. {source.document_name}, page {source.page_number}")
        
        if not self.is_verified:
            lines.append("")
            lines.append("⚠️ **Not Verified**")
        
        return "\n".join(lines)


class AuditRecord(BaseModel):
    """
    Complete audit trail for document processing
    """
    
    # Operation info
    operation_id: str = Field(..., description="Unique operation ID")
    operation_type: str = Field(..., description="triage, extract, chunk, query")
    
    # Document
    document_id: str = Field(..., description="Document being processed")
    
    # Input/Output
    input_data: Optional[Dict[str, Any]] = Field(None, description="Operation input")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Operation output")
    
    # Provenance
    sources_used: List[SourceCitation] = Field(default_factory=list)
    
    # Metrics
    processing_time_ms: float = Field(..., description="Time taken")
    confidence: float = Field(..., description="Confidence in result")
    
    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.now)