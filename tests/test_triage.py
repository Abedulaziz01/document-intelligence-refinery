"""
Tests for the Triage Agent
"""

import pytest
import json
import os
import tempfile
from pathlib import Path

from src.agents.triage import TriageAgent
from src.models.document_profile import OriginType, LayoutComplexity, DomainHint


class TestTriageAgent:
    """Test suite for Triage Agent"""
    
    @pytest.fixture
    def agent(self):
        """Create a Triage Agent instance for testing"""
        return TriageAgent()
    
    def test_agent_initialization(self, agent):
        """Test that agent initializes correctly"""
        assert agent is not None
        assert agent.profiles_dir.exists()
    
    def test_doc_id_generation(self, agent):
        """Test document ID generation"""
        doc_id = agent._generate_doc_id("test.pdf")
        assert len(doc_id) == 12  # 12 character hash
        assert isinstance(doc_id, str)
    
    def test_analyze_with_mock_data(self, agent, monkeypatch):
        """Test analysis with mocked PDF data"""
        
        # Mock the PDF analysis function
        def mock_analyze(*args, **kwargs):
            return {
                'page_count': 10,
                'total_chars': 5000,
                'avg_char_density': 500.0,
                'image_count': 2,
                'image_to_page_ratio': 0.1,
                'has_text': True,
                'fonts_found': ['Arial'],
                'pages_with_text': 9,
                'pages_with_images': 2
            }
        
        # Mock first page text extraction
        def mock_extract_text(*args, **kwargs):
            return "Annual financial report revenue profit"
        
        # Apply mocks
        import src.utils.pdf_utils
        monkeypatch.setattr(src.utils.pdf_utils, 'analyze_pdf_with_pdfplumber', mock_analyze)
        monkeypatch.setattr(src.utils.pdf_utils, 'extract_first_page_text', mock_extract_text)
        
        # Run analysis
        profile = agent.analyze_document("mock.pdf")
        
        # Check results
        assert profile.origin_type == OriginType.NATIVE_DIGITAL
        assert profile.domain_hint == DomainHint.FINANCIAL
        assert profile.page_count == 10
        assert profile.recommended_strategy in ["fast_text", "layout_aware", "vision"]
    
    def test_save_profile(self, agent):
        """Test saving profile to file"""
        from src.models.document_profile import DocumentProfile
        from datetime import datetime
        
        # Create a test profile
        profile = DocumentProfile(
            doc_id="test123",
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_size_bytes=1024,
            page_count=5,
            origin_type=OriginType.NATIVE_DIGITAL,
            layout_complexity=LayoutComplexity.SINGLE_COLUMN,
            language="en",
            language_confidence=0.95,
            domain_hint=DomainHint.GENERAL,
            avg_character_density=100.0,
            image_to_page_ratio=0.0,
            has_embedded_fonts=True,
            estimated_extraction_cost="fast_text_sufficient",
            recommended_strategy="fast_text",
            processed_at=datetime.now()
        )
        
        # Save profile
        saved_path = agent.save_profile(profile)
        
        # Check that file exists
        assert os.path.exists(saved_path)
        
        # Check file contents
        with open(saved_path, 'r') as f:
            data = json.load(f)
            assert data['doc_id'] == 'test123'
            assert data['filename'] == 'test.pdf'
        
        # Clean up
        os.remove(saved_path)
    
    def test_classification_rules(self, agent):
        """Test classification rules with different document types"""
        
        # Test Case 1: Scanned document (no text, lots of images)
        scanned_mock = {
            'page_count': 5,
            'total_chars': 0,
            'avg_char_density': 0.0,
            'image_count': 10,
            'image_to_page_ratio': 0.9,
            'has_text': False,
            'fonts_found': [],
            'pages_with_text': 0,
            'pages_with_images': 5
        }
        
        # Test detection functions directly
        from src.utils.pdf_utils import detect_origin_type
        origin = detect_origin_type(scanned_mock)
        assert origin == "scanned_image"
        
        # Test Case 2: Digital document (lots of text, few images)
        digital_mock = {
            'page_count': 10,
            'total_chars': 50000,
            'avg_char_density': 5000.0,
            'image_count': 1,
            'image_to_page_ratio': 0.05,
            'has_text': True,
            'fonts_found': ['Arial'],
            'pages_with_text': 10,
            'pages_with_images': 1
        }
        
        origin = detect_origin_type(digital_mock)
        assert origin == "native_digital"
        
        # Test Case 3: Mixed document
        mixed_mock = {
            'page_count': 8,
            'total_chars': 2000,
            'avg_char_density': 250.0,
            'image_count': 5,
            'image_to_page_ratio': 0.5,
            'has_text': True,
            'fonts_found': ['Arial'],
            'pages_with_text': 4,
            'pages_with_images': 4
        }
        
        origin = detect_origin_type(mixed_mock)
        assert origin == "mixed"


def test_with_real_pdf():
    """Test with an actual PDF file (if available)"""
    
    # Check if we have a test PDF
    test_pdfs = [
        "data/raw/CBE_ANNUAL_REPORT_2023-24.pdf",
        "data/raw/Audit_Report_2023.pdf",
        "data/raw/fta_performance_survey_final_report_2022.pdf",
        "data/raw/tax_expenditure_ethiopia_2021_22.pdf"
    ]
    
    agent = TriageAgent()
    
    for pdf_path in test_pdfs:
        if os.path.exists(pdf_path):
            print(f"\nTesting with: {pdf_path}")
            
            # Process document
            profile = agent.process_document(pdf_path)
            
            # Print results
            print(f"  Origin: {profile.origin_type}")
            print(f"  Layout: {profile.layout_complexity}")
            print(f"  Domain: {profile.domain_hint}")
            print(f"  Strategy: {profile.recommended_strategy}")
            
            # Assertions
            assert profile.doc_id is not None
            assert profile.origin_type in ["native_digital", "scanned_image", "mixed"]
            assert profile.layout_complexity in ["single_column", "multi_column", "table_heavy", "figure_heavy", "mixed"]
            assert profile.domain_hint in ["financial", "legal", "technical", "medical", "general"]
            
            # Check that profile was saved
            saved_file = f".refinery/profiles/{profile.doc_id}_profile.json"
            assert os.path.exists(saved_file)
            
            print(f"  ✅ Test passed for {pdf_path}")
        else:
            print(f"⚠️ Skipping {pdf_path} - file not found")


if __name__ == "__main__":
    # Run tests manually
    print("🧪 Running Triage Agent Tests...")
    
    # Run the test with real PDFs if available
    test_with_real_pdf()
    
    print("\n✅ All tests completed!")