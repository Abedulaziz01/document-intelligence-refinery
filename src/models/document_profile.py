"""
Document Profile Model
Defines the classification output from the Triage Agent
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict  # 👈 Add ConfigDict to imports


class OriginType(str, Enum):
    """Where did this document come from?"""
    NATIVE_DIGITAL = "native_digital"  # Born-digital PDF
    SCANNED_IMAGE = "scanned_image"    # Scanned paper document
    MIXED = "mixed"                     # Combination
    FORM_FILLABLE = "form_fillable"     # Interactive PDF form


class LayoutComplexity(str, Enum):
    """How complex is the document layout?"""
    SINGLE_COLUMN = "single_column"     # Simple text
    MULTI_COLUMN = "multi_column"       # Newspaper style
    TABLE_HEAVY = "table_heavy"         # Many tables
    FIGURE_HEAVY = "figure_heavy"       # Many images/charts
    MIXED = "mixed"                      # Everything together


class DomainHint(str, Enum):
    """What type of content is this?"""
    FINANCIAL = "financial"
    LEGAL = "legal"
    TECHNICAL = "technical"
    MEDICAL = "medical"
    GENERAL = "general"


class ExtractionCost(str, Enum):
    """How expensive will extraction be?"""
    FAST_TEXT_SUFFICIENT = "fast_text_sufficient"
    NEEDS_LAYOUT_MODEL = "needs_layout_model"
    NEEDS_VISION_MODEL = "needs_vision_model"


class DocumentProfile(BaseModel):
    """
    Complete profile of a document from the Triage Agent
    This determines which extraction strategy to use
    """
    
    # Basic Info
    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Path to document")
    file_size_bytes: int = Field(..., description="File size")
    page_count: int = Field(..., description="Total pages")
    
    # Classification
    origin_type: OriginType = Field(..., description="Digital or scanned?")
    layout_complexity: LayoutComplexity = Field(..., description="Layout type")
    language: str = Field("en", description="Detected language code")
    language_confidence: float = Field(0.0, description="Language detection confidence")
    domain_hint: DomainHint = Field(DomainHint.GENERAL, description="Content domain")
    
    # Metrics used for classification
    avg_character_density: float = Field(..., description="Characters per page area")
    image_to_page_ratio: float = Field(..., description="Proportion of page that's images")
    has_embedded_fonts: bool = Field(False, description="Whether document has embedded fonts")
    
    # Strategy Decision
    estimated_extraction_cost: ExtractionCost = Field(
        ..., 
        description="Which strategy tier to use"
    )
    recommended_strategy: str = Field(..., description="Name of recommended strategy")
    
    # Metadata
    processed_at: datetime = Field(default_factory=datetime.now)
    processing_time_ms: Optional[float] = Field(None, description="Time to classify")
    
    # 👇 FIXED: Replaced class Config with model_config
    model_config = ConfigDict(
        use_enum_values=True  # Store enums as strings in JSON
    )
    
    def dict_for_json(self):
        """Convert to dict for JSON serialization"""
        # 👇 FIXED: Changed .dict() to .model_dump()
        data = self.model_dump()
        data['processed_at'] = self.processed_at.isoformat()
        return data