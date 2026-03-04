"""
Triage Agent
Classifies documents to determine extraction strategy
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from src.models.document_profile import (
    DocumentProfile, 
    OriginType, 
    LayoutComplexity, 
    DomainHint, 
    ExtractionCost
)
from src.utils.pdf_utils import (
    analyze_pdf_with_pdfplumber,
    detect_origin_type,
    detect_layout_complexity,
    detect_domain_hint,
    estimate_extraction_cost,
    extract_first_page_text
)


class TriageAgent:
    """
    Triage Agent - Analyzes documents and creates profiles
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the Triage Agent"""
        self.config = self._load_config(config_path)
        self.profiles_dir = Path(".refinery/profiles")
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        import yaml
        
        default_config = {
            'confidence_thresholds': {
                'fast_text_min_confidence': 0.7,
                'layout_min_confidence': 0.8,
                'escalation_threshold': 0.6
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    return config or default_config
            except:
                return default_config
        return default_config
    
    def _generate_doc_id(self, filepath: str) -> str:
        """Generate a unique document ID based on file path and timestamp"""
        unique_string = f"{filepath}_{datetime.now().isoformat()}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
    
    def analyze_document(self, pdf_path: str) -> DocumentProfile:
        """
        Analyze a document and create a profile
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            DocumentProfile with classification results
        """
        start_time = datetime.now()
        
        # Get file info
        file_path = Path(pdf_path)
        filename = file_path.name
        file_size_bytes = file_path.stat().st_size if file_path.exists() else 0
        
        # Generate document ID
        doc_id = self._generate_doc_id(pdf_path)
        
        # Analyze PDF with pdfplumber
        pdf_analysis = analyze_pdf_with_pdfplumber(pdf_path)
        
        # Extract first page text for domain detection
        first_page_text = extract_first_page_text(pdf_path)
        
        # Classify document
        origin_type_str = detect_origin_type(pdf_analysis)
        origin_type = OriginType(origin_type_str)
        
        layout_complexity_str = detect_layout_complexity(pdf_analysis)
        layout_complexity = LayoutComplexity(layout_complexity_str)
        
        domain_hint_str = detect_domain_hint(filename, first_page_text)
        domain_hint = DomainHint(domain_hint_str)
        
        # Estimate extraction cost
        estimated_cost_str = estimate_extraction_cost(origin_type_str, layout_complexity_str)
        estimated_extraction_cost = ExtractionCost(estimated_cost_str)
        
        # Map cost to recommended strategy
        strategy_map = {
            "fast_text_sufficient": "fast_text",
            "needs_layout_model": "layout_aware",
            "needs_vision_model": "vision"
        }
        recommended_strategy = strategy_map.get(estimated_cost_str, "layout_aware")
        
        # Calculate processing time
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Create profile
        profile = DocumentProfile(
            doc_id=doc_id,
            filename=filename,
            file_path=str(file_path),
            file_size_bytes=file_size_bytes,
            page_count=pdf_analysis['page_count'],
            origin_type=origin_type,
            layout_complexity=layout_complexity,
            language="en",  # Default to English for now
            language_confidence=0.9,
            domain_hint=domain_hint,
            avg_character_density=pdf_analysis['avg_char_density'],
            image_to_page_ratio=pdf_analysis['image_to_page_ratio'],
            has_embedded_fonts=len(pdf_analysis['fonts_found']) > 0,
            estimated_extraction_cost=estimated_extraction_cost,
            recommended_strategy=recommended_strategy,
            processed_at=datetime.now(),
            processing_time_ms=processing_time_ms
        )
        
        return profile
    
    def save_profile(self, profile: DocumentProfile) -> str:
        """
        Save profile to .refinery/profiles/
        
        Returns:
            Path to saved profile
        """
        # Create filename
        filename = f"{profile.doc_id}_profile.json"
        filepath = self.profiles_dir / filename
        
        # Convert to dict and save
        profile_dict = profile.dict_for_json()
        
        with open(filepath, 'w') as f:
            json.dump(profile_dict, f, indent=2)
        
        return str(filepath)
    
    def process_document(self, pdf_path: str) -> DocumentProfile:
        """
        Complete triage process: analyze and save profile
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            The created profile
        """
        print(f"🔍 Triage Agent analyzing: {pdf_path}")
        
        # Analyze document
        profile = self.analyze_document(pdf_path)
        
        # Save profile
        saved_path = self.save_profile(profile)
        
        # Print summary
        print(f"\n📊 Document Profile Summary:")
        print(f"   Doc ID: {profile.doc_id}")
        print(f"   Origin: {profile.origin_type}")
        print(f"   Layout: {profile.layout_complexity}")
        print(f"   Domain: {profile.domain_hint}")
        print(f"   Strategy: {profile.recommended_strategy}")
        print(f"   Pages: {profile.page_count}")
        print(f"\n💾 Profile saved to: {saved_path}")
        
        return profile