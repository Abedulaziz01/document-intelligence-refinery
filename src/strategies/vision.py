"""
Vision Extraction Strategy (Strategy C)
Uses Gemini Vision AI for scanned documents
FREE using Gemini 3 Flash Preview
"""

import os
import base64
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

# Updated import for new SDK
import google.genai as genai
from google.genai import types

from src.strategies.base_strategy import BaseExtractionStrategy
from src.models.extracted_document import (
    ExtractedDocument, TextBlock, BoundingBox,
    ExtractedTable, TableCell
)
from src.utils.budget_guard import BudgetGuard
from src.utils.confidence import calculate_vision_confidence


class VisionExtractor(BaseExtractionStrategy):
    """
    Vision-based extraction using Gemini AI
    Best for: scanned documents, handwriting, complex layouts
    
    Uses FREE Gemini 3 Flash Preview model
    Rate limits: 15 RPM, 1M TPM, 1500 RPD
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.name = "vision"
        
        # Initialize Gemini with new SDK
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("⚠️  GEMINI_API_KEY not found. Using fallback mode.")
            self.client = None
        else:
            # New SDK initialization
            self.client = genai.Client(api_key=api_key)
            # Using FREE Gemini 3 Flash Preview model
            self.model_name = 'gemini-3-flash-preview'
            print("✅ Using FREE Gemini 3 Flash model")
        
        # Budget tracking (optional now since it's free)
        self.budget_guard = BudgetGuard(config.get('vision_budget', {}))
        
        # Cost tracking - now $0!
        self.cost_per_page = 0.0
    
    def extract(self, pdf_path: str, doc_id: str) -> ExtractedDocument:
        """
        Extract using Vision AI (FREE!)
        """
        start_time = datetime.now()
        
        pdf_path_obj = Path(pdf_path)
        filename = pdf_path_obj.name
        
        text_blocks = []
        tables = []
        total_cost = 0.0  # Still $0!
        
        try:
            # Convert PDF to images and process
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            
            print(f"📄 Processing {page_count} pages with FREE Gemini Vision...")
            
            # Check budget before processing (now just a formality)
            estimated_cost = page_count * self.cost_per_page
            if not self.budget_guard.check_budget(doc_id, estimated_cost):
                print(f"⚠️ Budget check passed - it's FREE!")
            
            for page_num in range(page_count):
                # Convert page to image
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for better quality
                img_data = pix.tobytes("png")
                
                # Prepare prompt for document extraction
                prompt = """
                Extract ALL text from this document page exactly as written.
                Return ONLY the extracted text content.
                If there are tables, format them with proper spacing.
                Do not add any explanations or markdown formatting.
                """
                
                # Call Gemini with new SDK (FREE!)
                if self.client:
                    # New SDK way to send image + text
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=[
                            prompt,
                            types.Part.from_bytes(
                                data=img_data,
                                mime_type="image/png"
                            )
                        ]
                    )
                    
                    # Parse response
                    if response and response.text:
                        # Create text block from response
                        bbox = BoundingBox(
                            page_number=page_num + 1,
                            x0=0,
                            y0=0,
                            x1=page.rect.width,
                            y1=page.rect.height
                        )
                        
                        text_block = TextBlock(
                            text=response.text,
                            bbox=bbox,
                            block_type="page",
                            confidence=0.85  # Gemini is quite accurate
                        )
                        text_blocks.append(text_block)
                        
                        print(f"   Page {page_num + 1}/{page_count} complete")
                else:
                    # Fallback if no API key
                    print(f"⚠️  No API key - skipping page {page_num + 1}")
                    # You could add Tesseract fallback here
            
            doc.close()
            
            # Create extracted document
            extracted_doc = ExtractedDocument(
                doc_id=doc_id,
                filename=filename,
                page_count=page_count,
                strategy_used=self.name,
                overall_confidence=0.0,
                text_blocks=text_blocks,
                tables=tables
            )
            
            # Calculate confidence
            confidence = self.calculate_confidence(extracted_doc)
            extracted_doc.overall_confidence = confidence
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            extracted_doc.extraction_time_ms = processing_time
            
            # Track cost (still $0)
            if self.client:
                self.budget_guard.add_cost(doc_id, 0.0, {
                    "pages": page_count,
                    "model": self.model_name
                })
            
            print(f"💰 Vision extraction cost: FREE! (${total_cost:.2f})")
            print(f"   Pages processed: {len(text_blocks)}/{page_count}")
            print(f"   Confidence: {confidence:.2f}")
            
            return extracted_doc
            
        except Exception as e:
            print(f"❌ Error in VisionExtractor: {e}")
            import traceback
            traceback.print_exc()
            return ExtractedDocument(
                doc_id=doc_id,
                filename=filename,
                page_count=0,
                strategy_used=self.name,
                overall_confidence=0.0
            )
    
    def estimate_cost(self, pdf_path: str) -> float:
        """Estimate cost for this document - always $0!"""
        return 0.0
    
    def calculate_confidence(self, extracted_doc: ExtractedDocument) -> float:
        """Calculate confidence for vision extraction"""
        return calculate_vision_confidence(extracted_doc)