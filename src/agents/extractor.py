"""
Extraction Router
Selects and runs the appropriate extraction strategy
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Type

from src.strategies.fast_text import FastTextExtractor
from src.strategies.layout_aware import LayoutAwareExtractor
from src.strategies.vision import VisionExtractor
from src.models.document_profile import DocumentProfile
from src.models.extracted_document import ExtractedDocument
from src.utils.confidence import should_escalate


class ExtractionRouter:
    """
    Routes documents to appropriate extraction strategy
    Implements escalation guard pattern
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the extraction router"""
        self.config = self._load_config(config_path)
        
        # Initialize strategies
        self.strategies = {
            'fast_text': FastTextExtractor(self.config),
            'layout_aware': LayoutAwareExtractor(self.config),
            'vision': VisionExtractor(self.config)
        }
        
        # Setup ledger
        self.ledger_path = Path(".refinery/extraction_ledger.jsonl")
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Confidence thresholds
        self.thresholds = self.config.get('confidence_thresholds', {
            'fast_text_min_confidence': 0.7,
            'layout_min_confidence': 0.8,
            'escalation_threshold': 0.6
        })
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from YAML"""
        import yaml
        
        default_config = {
            'confidence_thresholds': {
                'fast_text_min_confidence': 0.7,
                'layout_min_confidence': 0.8,
                'escalation_threshold': 0.6
            },
            'vision_budget': {
                'max_cost_per_document': 0.50
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
    
    def _log_to_ledger(self, entry: Dict[str, Any]):
        """Log extraction to ledger file"""
        entry['timestamp'] = datetime.now().isoformat()
        
        with open(self.ledger_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def extract(self, pdf_path: str, profile: DocumentProfile) -> ExtractedDocument:
        """
        Extract document using appropriate strategy
        
        Args:
            pdf_path: Path to PDF
            profile: DocumentProfile from Triage Agent
            
        Returns:
            ExtractedDocument
        """
        print(f"\n🔧 Extraction Router processing: {pdf_path}")
        print(f"   Recommended strategy: {profile.recommended_strategy}")
        
        # Start with recommended strategy
        current_strategy = profile.recommended_strategy
        strategies_tried = []
        final_doc = None
        
        while current_strategy and current_strategy not in strategies_tried:
            print(f"\n   Trying strategy: {current_strategy}")
            
            # Get strategy instance
            strategy = self.strategies.get(current_strategy)
            if not strategy:
                print(f"   ❌ Unknown strategy: {current_strategy}")
                break
            
            # Estimate cost before extraction
            cost_estimate = strategy.estimate_cost(pdf_path)
            print(f"   💰 Estimated cost: ${cost_estimate:.4f}")
            
            # Run extraction
            start_time = datetime.now()
            try:
                extracted_doc = strategy.extract(pdf_path, profile.doc_id)
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # Log this attempt
                ledger_entry = {
                    'doc_id': profile.doc_id,
                    'strategy_used': current_strategy,
                    'confidence_score': extracted_doc.overall_confidence,
                    'cost_estimate': cost_estimate,
                    'processing_time_ms': processing_time,
                    'pages': extracted_doc.page_count,
                    'tables_found': len(extracted_doc.tables)
                }
                self._log_to_ledger(ledger_entry)
                
                print(f"   ✅ Confidence: {extracted_doc.overall_confidence:.2f}")
                print(f"   ⏱️  Time: {processing_time:.0f}ms")
                
                # Check if we need to escalate
                threshold = self.thresholds.get('escalation_threshold', 0.6)
                if should_escalate(extracted_doc.overall_confidence, threshold):
                    print(f"   ⚠️ Confidence below threshold ({threshold}), escalating...")
                    
                    # Determine next strategy
                    if current_strategy == 'fast_text':
                        current_strategy = 'layout_aware'
                    elif current_strategy == 'layout_aware':
                        current_strategy = 'vision'
                    else:
                        current_strategy = None
                    
                    strategies_tried.append(current_strategy)
                    final_doc = extracted_doc  # Keep best so far
                else:
                    # Good enough, return this
                    print(f"   ✅ Extraction successful with {current_strategy}")
                    return extracted_doc
                    
            except Exception as e:
                print(f"   ❌ Error with {current_strategy}: {e}")
                # Try next strategy
                if current_strategy == 'fast_text':
                    current_strategy = 'layout_aware'
                elif current_strategy == 'layout_aware':
                    current_strategy = 'vision'
                else:
                    current_strategy = None
        
        # If we get here, all strategies failed or were low confidence
        if final_doc:
            print(f"\n⚠️ Using best available result (confidence: {final_doc.overall_confidence:.2f})")
            return final_doc
        else:
            print("\n❌ All extraction strategies failed")
            # Return empty document
            return ExtractedDocument(
                doc_id=profile.doc_id,
                filename=Path(pdf_path).name,
                page_count=0,
                strategy_used="none",
                overall_confidence=0.0
            )
    
    def extract_with_strategy(self, pdf_path: str, doc_id: str, 
                            strategy_name: str) -> ExtractedDocument:
        """
        Extract using a specific strategy (for testing)
        """
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        return strategy.extract(pdf_path, doc_id)