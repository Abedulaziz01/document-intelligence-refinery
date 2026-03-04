"""
Extraction Router
Selects and runs the appropriate extraction strategy
USING EasyOCR (Pure Python, No Tesseract needed!)
"""

import json
import os
import gc
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import fitz  # PyMuPDF
from PIL import Image
import easyocr
import numpy as np

from src.strategies.fast_text import FastTextExtractor
from src.strategies.layout_aware import LayoutAwareExtractor
from src.models.document_profile import DocumentProfile
from src.models.extracted_document import ExtractedDocument, TextBlock, BoundingBox
from src.utils.confidence import should_escalate


class ExtractionRouter:
    """
    Routes documents to appropriate extraction strategy
    Uses EasyOCR for scanned documents (no Tesseract needed!)
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the extraction router"""
        self.config = self._load_config(config_path)
        
        # Initialize basic strategies
        self.strategies = {
            'fast_text': FastTextExtractor(self.config),
            'layout_aware': LayoutAwareExtractor(self.config)
        }
        
        # Initialize EasyOCR (downloads models on first run)
        self._init_easyocr()
        
        # Setup ledger
        self.ledger_path = Path(".refinery/extraction_ledger.jsonl")
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Confidence thresholds
        self.thresholds = self.config.get('confidence_thresholds', {
            'fast_text_min_confidence': 0.7,
            'layout_min_confidence': 0.8,
            'escalation_threshold': 0.6
        })
    
    def _init_easyocr(self):
        """Initialize EasyOCR reader"""
        self.easyocr_available = False
        try:
            print("📚 Loading EasyOCR model (first time may take a minute to download)...")
            # Initialize with English language - add more if needed
            self.reader = easyocr.Reader(['en'], gpu=False)  # Set gpu=True if you have CUDA
            self.easyocr_available = True
            print("✅ EasyOCR initialized successfully!")
        except Exception as e:
            print(f"⚠️ EasyOCR initialization failed: {e}")
            print("   Install with: pip install easyocr")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from YAML"""
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
    
    def _log_to_ledger(self, entry: Dict[str, Any]):
        """Log extraction to ledger file"""
        entry['timestamp'] = datetime.now().isoformat()
        with open(self.ledger_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def extract(self, pdf_path: str, profile: DocumentProfile) -> ExtractedDocument:
        """
        Extract document using appropriate strategy
        """
        print(f"\n🔧 Extraction Router processing: {pdf_path}")
        print(f"   Recommended strategy: {profile.recommended_strategy}")
        
        current_strategy = profile.recommended_strategy
        strategies_tried = []
        final_doc = None
        best_confidence = 0.0
        
        while current_strategy and current_strategy not in strategies_tried:
            print(f"\n   Trying strategy: {current_strategy}")
            start_time = datetime.now()
            extracted_doc = None
            
            if current_strategy == 'vision':
                extracted_doc = self._extract_with_easyocr(pdf_path, profile)
                if extracted_doc:
                    extracted_doc.strategy_used = "easyocr"
            else:
                strategy = self.strategies.get(current_strategy)
                if not strategy:
                    print(f"   ❌ Unknown strategy: {current_strategy}")
                    break
                
                try:
                    extracted_doc = strategy.extract(pdf_path, profile.doc_id)
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    extracted_doc = None
            
            if extracted_doc:
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                extracted_doc.extraction_time_ms = processing_time
                
                ledger_entry = {
                    'doc_id': profile.doc_id,
                    'strategy_used': extracted_doc.strategy_used,
                    'confidence_score': extracted_doc.overall_confidence,
                    'cost_estimate': 0.0,
                    'processing_time_ms': processing_time,
                    'pages': extracted_doc.page_count,
                    'tables_found': len(extracted_doc.tables)
                }
                self._log_to_ledger(ledger_entry)
                
                print(f"   ✅ Confidence: {extracted_doc.overall_confidence:.2f}")
                print(f"   ⏱️  Time: {processing_time:.0f}ms")
                
                if extracted_doc.overall_confidence > best_confidence:
                    best_confidence = extracted_doc.overall_confidence
                    final_doc = extracted_doc
                
                threshold = self.thresholds.get('escalation_threshold', 0.6)
                if should_escalate(extracted_doc.overall_confidence, threshold):
                    print(f"   ⚠️ Confidence below threshold, trying next...")
                    if current_strategy == 'fast_text':
                        current_strategy = 'layout_aware'
                    elif current_strategy == 'layout_aware':
                        current_strategy = 'vision'
                    else:
                        current_strategy = None
                    strategies_tried.append(current_strategy)
                else:
                    print(f"   ✅ Extraction successful")
                    gc.collect()
                    return extracted_doc
            else:
                print(f"   ❌ Strategy failed")
                if current_strategy == 'fast_text':
                    current_strategy = 'layout_aware'
                elif current_strategy == 'layout_aware':
                    current_strategy = 'vision'
                else:
                    current_strategy = None
        
        if final_doc:
            print(f"\n⚠️ Using best result (confidence: {final_doc.overall_confidence:.2f})")
            gc.collect()
            return final_doc
        else:
            print("\n❌ All strategies failed")
            # Return empty document with safe values
            return ExtractedDocument(
                doc_id=profile.doc_id,
                filename=Path(pdf_path).name,
                page_count=0,
                strategy_used="none",
                overall_confidence=0.0,
                extraction_time_ms=0.0  # Add this to avoid NoneType error
            )
    
    def _extract_with_easyocr(self, pdf_path: str, profile: DocumentProfile) -> Optional[ExtractedDocument]:
        """Extract using EasyOCR (pure Python, no Tesseract!)"""
        if not self.easyocr_available:
            print("   ❌ EasyOCR not available")
            return None
            
        doc = None
        try:
            print("\n   👁️ Running EasyOCR (pure Python, no Tesseract needed!)...")
            doc = fitz.open(pdf_path)
            text_blocks = []
            total_confidence = 0.0
            pages_processed = 0
            total_pages = len(doc)
            
            print(f"      Processing {total_pages} pages with EasyOCR...")
            
            for page_num in range(total_pages):
                try:
                    page = doc[page_num]
                    
                    # Convert page to image with good quality
                    zoom = 2.0  # Good balance of speed and quality
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Convert to numpy array (EasyOCR expects numpy array, not PIL Image)
                    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
                    
                    # FIX: Use the numpy array directly instead of PIL Image
                    result = self.reader.readtext(img_array, paragraph=True)
                    
                    # Extract text from results
                    text_parts = []
                    confidences = []
                    
                    for detection in result:
                        # Each detection is [bbox, text, confidence]
                        if len(detection) >= 2:
                            text_parts.append(detection[1])
                            if len(detection) >= 3:
                                confidences.append(detection[2])
                    
                    text = '\n'.join(text_parts) if text_parts else ""
                    
                    # Calculate page confidence
                    page_confidence = sum(confidences) / len(confidences) if confidences else 0.7
                    
                    if text.strip():
                        text_block = TextBlock(
                            text=text,
                            bbox=BoundingBox(
                                page_number=page_num + 1,
                                x0=0, y0=0,
                                x1=page.rect.width,
                                y1=page.rect.height
                            ),
                            block_type="page",
                            confidence=page_confidence
                        )
                        text_blocks.append(text_block)
                        pages_processed += 1
                        total_confidence += page_confidence
                        
                        # Progress indicator
                        if (page_num + 1) % 5 == 0:
                            print(f"         Processed {page_num + 1}/{total_pages} pages (conf: {page_confidence:.2f})")
                    else:
                        print(f"         ⚠️ Page {page_num + 1} - no text found")
                        
                except KeyboardInterrupt:
                    print(f"\n         ⚠️ Interrupted at page {page_num + 1}")
                    raise
                except Exception as e:
                    print(f"         ⚠️ Page {page_num + 1} failed: {str(e)[:100]}")
                    continue
                
                # Free memory periodically
                if (page_num + 1) % 10 == 0:
                    gc.collect()
            
            # Clean up
            doc.close()
            doc = None
            
            avg_confidence = total_confidence / pages_processed if pages_processed > 0 else 0.0
            
            print(f"\n   ✅ EasyOCR complete: {pages_processed}/{total_pages} pages processed")
            print(f"   📊 Average confidence: {avg_confidence:.2f}")
            
            return ExtractedDocument(
                doc_id=profile.doc_id,
                filename=profile.filename,
                page_count=pages_processed,
                strategy_used="easyocr",
                overall_confidence=avg_confidence,
                text_blocks=text_blocks,
                tables=[]
            )
            
        except KeyboardInterrupt:
            print("\n   ⚠️ Extraction interrupted by user")
            if doc:
                try:
                    doc.close()
                except:
                    pass
            return None
        except Exception as e:
            print(f"   ❌ EasyOCR failed: {e}")
            return None
        finally:
            if doc:
                try:
                    doc.close()
                except:
                    pass
            gc.collect()
    
    def _extract_with_fallback(self, pdf_path: str, profile: DocumentProfile) -> ExtractedDocument:
        """Basic fallback using pdfplumber"""
        pdf = None
        try:
            import pdfplumber
            pdf = pdfplumber.open(pdf_path)
            text_blocks = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                if text.strip():
                    text_block = TextBlock(
                        text=text,
                        bbox=BoundingBox(
                            page_number=page_num,
                            x0=0, y0=0,
                            x1=page.width or 612,
                            y1=page.height or 792
                        ),
                        block_type="page",
                        confidence=0.3
                    )
                    text_blocks.append(text_block)
            
            pdf.close()
            return ExtractedDocument(
                doc_id=profile.doc_id,
                filename=profile.filename,
                page_count=len(text_blocks),
                strategy_used="fallback",
                overall_confidence=0.3 if text_blocks else 0.0,
                text_blocks=text_blocks,
                tables=[],
                extraction_time_ms=0.0
            )
        except Exception as e:
            print(f"      ⚠️ Fallback failed: {e}")
            return ExtractedDocument(
                doc_id=profile.doc_id,
                filename=profile.filename,
                page_count=0,
                strategy_used="fallback",
                overall_confidence=0.0,
                text_blocks=[],
                tables=[],
                extraction_time_ms=0.0
            )
        finally:
            if pdf:
                try:
                    pdf.close()
                except:
                    pass
    
    def extract_with_strategy(self, pdf_path: str, doc_id: str, strategy_name: str) -> ExtractedDocument:
        """Extract using a specific strategy"""
        if strategy_name == 'vision':
            from src.models.document_profile import DocumentProfile
            from datetime import datetime
            profile = DocumentProfile(
                doc_id=doc_id,
                filename=Path(pdf_path).name,
                file_path=pdf_path,
                file_size_bytes=0,
                page_count=0,
                origin_type="scanned_image",
                layout_complexity="mixed",
                language="en",
                language_confidence=0.0,
                domain_hint="general",
                avg_character_density=0.0,
                image_to_page_ratio=0.0,
                has_embedded_fonts=False,
                estimated_extraction_cost="needs_vision_model",
                recommended_strategy="vision",
                processed_at=datetime.now()
            )
            return self._extract_with_easyocr(pdf_path, profile)
        else:
            strategy = self.strategies.get(strategy_name)
            if not strategy:
                raise ValueError(f"Unknown strategy: {strategy_name}")
            return strategy.extract(pdf_path, doc_id)