#!/usr/bin/env python
"""
Run PageIndex Builder on a document
Usage: python scripts/run_indexing.py data/raw/sample.pdf
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.triage import TriageAgent
from src.agents.extractor import ExtractionRouter
from src.agents.chunker import ChunkingEngine
from src.agents.indexer import PageIndexBuilder
from dotenv import load_dotenv


def main():
    """Main function to run indexing"""
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("❌ Error: Please provide a PDF file path")
        print("Usage: python scripts/run_indexing.py data/raw/sample.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("📄 DOCUMENT INTELLIGENCE REFINERY")
    print("🗺️  PAGEINDEX BUILDER")
    print("=" * 60)
    print(f"📁 File: {pdf_path}")
    
    try:
        # Step 1: Run Triage
        print("\n🔍 Running Triage...")
        triage = TriageAgent()
        profile = triage.process_document(pdf_path)
        
        # Step 2: Run Extraction
        print("\n🔧 Running Extraction...")
        router = ExtractionRouter()
        extracted = router.extract(pdf_path, profile)
        
        # Step 3: Run Chunking
        print("\n✂️  Running Chunking...")
        chunker = ChunkingEngine()
        chunks = chunker.chunk_document(extracted)
        
        # Step 4: Build PageIndex
        print("\n🗺️  Building PageIndex...")
        indexer = PageIndexBuilder()
        page_index = indexer.build_index(
            doc_id=profile.doc_id,
            filename=Path(pdf_path).name,
            chunks=chunks
        )
        
        # Step 5: Print tree structure
        indexer.print_tree(page_index)
        
        # Step 6: Show section details
        print("\n📊 Section Details (first 3):")
        for i, section in enumerate(page_index.root_sections[:3]):
            print(f"\n  Section {i+1}: {section.title}")
            print(f"    Pages: {section.page_start}-{section.page_end}")
            print(f"    Types: {', '.join([dt.value for dt in section.data_types_present])}")
            print(f"    Chunks: {section.chunk_count}")
            if section.key_entities:
                print(f"    Key entities: {', '.join(section.key_entities[:3])}")
            if section.summary:
                print(f"    Summary: {section.summary[:100]}...")
        
        # Step 7: Save index
        output_dir = Path(".refinery/pageindex")
        indexer.save_index(page_index, output_dir)
        
        print("\n✅ PageIndex built successfully!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during indexing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())