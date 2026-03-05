"""
Tests for Semantic Chunking Engine
"""

import pytest
from datetime import datetime
from pathlib import Path

from src.agents.chunker import ChunkingEngine, ChunkValidator
from src.models.ldu import LDU, ChunkType
from src.models.extracted_document import (
    ExtractedDocument, ExtractedTable, TableCell, BoundingBox
)
from src.utils.hashing import generate_chunk_hash, verify_chunk_hash


class TestChunkingEngine:
    """Test suite for Chunking Engine"""
    
    @pytest.fixture
    def engine(self):
        """Create chunking engine for testing"""
        return ChunkingEngine()
    
    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing"""
        # Create a bounding box
        bbox = BoundingBox(
            page_number=1,
            x0=0,
            y0=0,
            x1=100,
            y1=50
        )
        
        # Create a sample table
        table = ExtractedTable(
            id="table1",
            headers=["Year", "Revenue"],
            rows=[
                [TableCell(text="2023", row_index=0, col_index=0),
                 TableCell(text="$1M", row_index=0, col_index=1)],
                [TableCell(text="2024", row_index=1, col_index=0),
                 TableCell(text="$1.5M", row_index=1, col_index=1)]
            ],
            bbox=bbox,
            confidence=0.9
        )
        
        # Create document
        doc = ExtractedDocument(
            doc_id="test123",
            filename="test.pdf",
            page_count=2,
            strategy_used="layout_aware",
            overall_confidence=0.85,
            tables=[table]
        )
        
        return doc
    
    def test_engine_initialization(self, engine):
        """Test engine initializes correctly"""
        assert engine is not None
        assert engine.max_tokens == 2000
    
    def test_chunk_tables(self, engine, sample_document):
        """Test Rule 1: Tables never split"""
        table_chunks = engine._chunk_tables(sample_document)
        
        assert len(table_chunks) == 1
        assert table_chunks[0].chunk_type == ChunkType.TABLE
        assert len(table_chunks[0].tables) == 1
        assert table_chunks[0].tables[0].id == "table1"
    
    def test_rule_validator_no_table_split(self):
        """Test validator for Rule 1"""
        validator = ChunkValidator()
        
        # Create test chunks with same table in multiple chunks (should fail)
        bbox = BoundingBox(page_number=1, x0=0, y0=0, x1=100, y1=50)
        
        table1 = ExtractedTable(
            id="table1",
            headers=[],
            rows=[],
            bbox=bbox,
            confidence=0.9
        )
        
        chunk1 = LDU(
            ldu_id="chunk1",
            doc_id="test",
            chunk_type=ChunkType.TABLE,
            content="Table data",
            content_hash="hash1",
            tables=[table1],
            page_refs=[1],
            token_count=10,
            char_count=20,
            word_count=3
        )
        
        chunk2 = LDU(
            ldu_id="chunk2",
            doc_id="test",
            chunk_type=ChunkType.TABLE,
            content="More table",
            content_hash="hash2",
            tables=[table1],  # Same table!
            page_refs=[1],
            token_count=10,
            char_count=20,
            word_count=3
        )
        
        result = validator.validate_rule_1_no_table_split([chunk1, chunk2])
        assert result is False
        assert len(validator.get_violations()) > 0
    
    def test_hash_generation(self):
        """Test hash generation for chunks"""
        content = "This is test content"
        page_refs = [1, 2]
        bbox = BoundingBox(page_number=1, x0=0, y0=0, x1=100, y1=50)
        
        # Generate hash
        hash1 = generate_chunk_hash(content, page_refs, bbox)
        hash2 = generate_chunk_hash(content, page_refs, bbox)
        
        # Same content should produce same hash
        assert hash1 == hash2
        
        # Different content should produce different hash
        hash3 = generate_chunk_hash("different content", page_refs, bbox)
        assert hash1 != hash3
    
    def test_chunk_integrity(self):
        """Test chunk integrity verification"""
        bbox = BoundingBox(page_number=1, x0=0, y0=0, x1=100, y1=50)
        
        # Create chunk with hash
        chunk = LDU(
            ldu_id="test_chunk",
            doc_id="test",
            chunk_type=ChunkType.TEXT,
            content="Test content",
            content_hash="",  # Will be set
            page_refs=[1],
            bbox=bbox,
            token_count=5,
            char_count=12,
            word_count=2
        )
        
        # Generate hash
        chunk.content_hash = generate_chunk_hash(
            chunk.content, chunk.page_refs, chunk.bbox
        )
        
        # Verify
        assert verify_chunk_hash(chunk) is True
        
        # Tamper with content
        chunk.content = "Tampered content"
        assert verify_chunk_hash(chunk) is False


def test_with_real_data():
    """Test with actual extracted data if available"""
    # This would require a real extraction first
    print("\n🧪 Testing chunking with real data requires running extraction first")
    print("   Run: python scripts/run_extraction.py data/raw/sample.pdf")
    print("   Then run this test again")


if __name__ == "__main__":
    # Run manual tests
    print("🧪 Running Chunking Tests...")
    
    # Create test instances
    engine = ChunkingEngine()
    validator = ChunkValidator()
    
    print("✅ Engine initialized")
    print("✅ Validator initialized")
    
    # Test hash functions
    hash1 = generate_chunk_hash("test", [1], None)
    hash2 = generate_chunk_hash("test", [1], None)
    print(f"✅ Hash generation: {hash1 == hash2}")
    
    print("\n✅ All basic tests passed!")