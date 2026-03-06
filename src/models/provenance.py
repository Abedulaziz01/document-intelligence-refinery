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
    
    # Context
    section_title: Optional[str] = Field(None, description="Section where fact was found")
    chunk_id: Optional[str] = Field(None, description="ID of the source chunk")
    
    # Extraction info
    strategy_used: str = Field(..., description="Which strategy extracted this")
    confidence: float = Field(..., description="Confidence score")
    
    # Metadata
    extracted_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        arbitrary_types_allowed = True
    
    def dict_for_json(self):
        """Convert to dict for JSON serialization"""
        data = self.dict()
        data['extracted_at'] = self.extracted_at.isoformat()
        if self.bbox:
            data['bbox'] = self.bbox.dict()
        return data
    
    def to_string(self) -> str:
        """Human-readable citation"""
        location = f"page {self.page_number}"
        if self.bbox:
            location += f" at ({self.bbox.x0:.0f}, {self.bbox.y0:.0f})"
        
        return f"📄 {self.document_name}, {location}"


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
    verification_timestamp: Optional[datetime] = Field(None, description="When verified")
    
    # For multi-document queries
    all_sources: List[SourceCitation] = Field(default_factory=list)
    
    # Confidence in the answer
    overall_confidence: float = Field(1.0, description="Overall confidence in answer")
    
    class Config:
        arbitrary_types_allowed = True
    
    def dict_for_json(self):
        """Convert to dict for JSON serialization"""
        data = {
            'claim': self.claim,
            'is_verified': self.is_verified,
            'verification_method': self.verification_method,
            'overall_confidence': self.overall_confidence,
            'primary_source': self.primary_source.dict_for_json() if self.primary_source else None,
            'supporting_sources': [s.dict_for_json() for s in self.supporting_sources],
            'all_sources': [s.dict_for_json() for s in self.all_sources]
        }
        if self.verification_timestamp:
            data['verification_timestamp'] = self.verification_timestamp.isoformat()
        return data
    
    def to_markdown(self) -> str:
        """Format as markdown for display"""
        lines = []
        lines.append(f"**Answer:** {self.claim}")
        lines.append("")
        lines.append("**Sources:**")
        lines.append(f"1. Primary: {self.primary_source.to_string()}")
        lines.append(f"   > \"{self.primary_source.extracted_text[:100]}...\"")
        
        for i, source in enumerate(self.supporting_sources, 2):
            lines.append(f"{i}. Supporting: {source.to_string()}")
        
        if self.is_verified:
            lines.append("")
            lines.append(f"✅ **Verified** via {self.verification_method}")
        else:
            lines.append("")
            lines.append("⚠️ **Not Verified** - Could not verify against source")
        
        return "\n".join(lines)
    
    def verify_with_source(self, pdf_path: str) -> bool:
        """
        Verify the claim by checking against source PDF
        This would open the PDF and check the content
        """
        # In a real implementation, this would extract text from the PDF
        # at the specified location and compare
        # For now, we'll return True if hash matches
        from src.utils.hashing import hash_text
        
        # This is a simplified verification
        # In reality, you'd extract text from the PDF at the bbox
        expected_hash = hash_text(self.primary_source.extracted_text)
        is_valid = expected_hash == self.primary_source.content_hash
        
        self.is_verified = is_valid
        self.verification_method = "hash_match" if is_valid else "verification_failed"
        self.verification_timestamp = datetime.now()
        
        return is_valid


class AuditRecord(BaseModel):
    """
    Complete audit trail for document processing
    """
    
    # Operation info
    operation_id: str = Field(..., description="Unique operation ID")
    operation_type: str = Field(..., description="triage, extract, chunk, query")
    
    # Document
    document_id: str = Field(..., description="Document being processed")
    document_name: str = Field(..., description="Document filename")
    
    # Input/Output
    query: Optional[str] = Field(None, description="User query (for query operations)")
    response: Optional[str] = Field(None, description="System response")
    
    # Provenance
    provenance: Optional[ProvenanceChain] = Field(None, description="Provenance chain")
    
    # Metrics
    processing_time_ms: float = Field(..., description="Time taken")
    confidence: float = Field(..., description="Confidence in result")
    
    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        arbitrary_types_allowed = True