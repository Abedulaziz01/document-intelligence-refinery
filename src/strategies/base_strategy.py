"""
Base Strategy Class
All extraction strategies must inherit from this
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from src.models.extracted_document import ExtractedDocument


class BaseExtractionStrategy(ABC):
    """
    Abstract base class for all extraction strategies
    Defines the interface that all strategies must implement
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration"""
        self.config = config or {}
        self.name = self.__class__.__name__.replace('Extractor', '').lower()
    
    @abstractmethod
    def extract(self, pdf_path: str, doc_id: str) -> ExtractedDocument:
        """
        Extract content from PDF
        
        Args:
            pdf_path: Path to PDF file
            doc_id: Document identifier
            
        Returns:
            ExtractedDocument with all content
        """
        pass
    
    @abstractmethod
    def calculate_confidence(self, extracted_doc: ExtractedDocument) -> float:
        """
        Calculate confidence score for extraction
        
        Returns:
            Float between 0 and 1
        """
        pass
    
    def estimate_cost(self, pdf_path: str) -> float:
        """
        Estimate cost of extraction (for budget tracking)
        Override this for strategies that cost money (Vision)
        
        Returns:
            Cost in USD
        """
        return 0.0
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get strategy metadata"""
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'cost_per_page': self.estimate_cost('dummy.pdf')  # Rough estimate
        }