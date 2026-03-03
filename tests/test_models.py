"""
Test all models to ensure they instantiate correctly
"""

import pytest
from datetime import datetime
from src.models.document_profile import DocumentProfile, OriginType, LayoutComplexity, DomainHint, ExtractionCost
from src.models.extracted_document import ExtractedDocument, BoundingBox, TextBlock, ExtractedTable, TableCell
from src.models.ldu import LDU, ChunkType
from src.models.pageindex import PageIndex, SectionNode, DataType
from src.models.provenance import ProvenanceChain, SourceCitation


class TestAllModels:
    """Test that all models can be instantiated"""
    
    def test_document_profile(self):
        """Test creating a DocumentProfile"""
        profile = DocumentProfile(
            doc_id="test123",
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_size_bytes=1024,
            page_count=10,
            origin_type=OriginType.NATIVE_DIGITAL,
            layout_complexity=LayoutComplexity.SINGLE_COLUMN,
            language="en",
            language_confidence=0.95,
            domain_hint=DomainHint.FINANCIAL,
            avg_character_density=0.5,
            image_to_page_ratio=0.1,
            has_embedded_fonts=True,
            estimated_extraction_cost=ExtractionCost.FAST_TEXT_SUFFICIENT,
            recommended_strategy="fast_text",
            processed_at=datetime.now()
        )
        assert profile.doc_id == "test123"
        assert profile.origin_type == "native_digital"
        print("✅ DocumentProfile test passed")
    
    def test_bounding_box(self):
        """Test creating a BoundingBox"""
        bbox = BoundingBox(
            page_number=1,
            x0=10.0,
            y0=20.0,
            x1=100.0,
            y1=200.0
        )
        assert bbox.width == 90.0
        assert bbox.height == 180.0
        assert bbox.area == 16200.0
        print("✅ BoundingBox test passed")
    
    def test_extracted_document(self):
        """Test creating an ExtractedDocument"""
        # Create a text block
        bbox = BoundingBox(page_number=1, x0=0, y0=0, x1=100, y1=50)
        text_block = TextBlock(
            text="Sample text",
            bbox=bbox,
            block_type="paragraph",
            confidence=0.9
        )
        
        # Create document
        doc = ExtractedDocument(
            doc_id="test123",
            filename="test.pdf",
            page_count=5,
            strategy_used="fast_text",
            overall_confidence=0.85,
            text_blocks=[text_block]
        )
        
        assert doc.doc_id == "test123"
        assert len(doc.text_blocks) == 1
        print("✅ ExtractedDocument test passed")
    
    def test_ldu(self):
        """Test creating an LDU"""
        ldu = LDU(
            ldu_id="ldu123",
            doc_id="test123",
            chunk_type=ChunkType.TEXT,
            content="This is a test chunk",
            content_hash="abc123hash",
            page_refs=[1],
            token_count=10,
            char_count=20
        )
        assert ldu.ldu_id == "ldu123"
        assert ldu.chunk_type == "text"
        print("✅ LDU test passed")
    
    def test_pageindex(self):
        """Test creating a PageIndex"""
        # Create a section
        section = SectionNode(
            section_id="sec1",
            title="Introduction",
            level=1,
            page_start=1,
            page_end=3,
            summary="This is the introduction",
            data_types_present=[DataType.TEXT]
        )
        
        # Create index
        index = PageIndex(
            doc_id="test123",
            filename="test.pdf",
            total_pages=10,
            root_sections=[section],
            section_by_id={"sec1": section},
            total_sections=1
        )
        
        assert index.doc_id == "test123"
        assert len(index.root_sections) == 1
        print("✅ PageIndex test passed")
    
    def test_provenance(self):
        """Test creating a ProvenanceChain"""
        # Create source
        bbox = BoundingBox(page_number=1, x0=0, y0=0, x1=100, y1=50)
        source = SourceCitation(
            document_name="test.pdf",
            document_id="test123",
            page_number=1,
            bbox=bbox,
            content_hash="abc123",
            extracted_text="Revenue was $1M",
            strategy_used="fast_text",
            confidence=0.95
        )
        
        # Create provenance chain
        chain = ProvenanceChain(
            claim="Revenue was $1M",
            primary_source=source,
            is_verified=True,
            verification_method="exact_match"
        )
        
        assert chain.claim == "Revenue was $1M"
        assert chain.primary_source.document_name == "test.pdf"
        print("✅ ProvenanceChain test passed")


if __name__ == "__main__":
    # Run tests manually
    test = TestAllModels()
    test.test_document_profile()
    test.test_bounding_box()
    test.test_extracted_document()
    test.test_ldu()
    test.test_pageindex()
    test.test_provenance()
    print("\n🎉 ALL TESTS PASSED!")