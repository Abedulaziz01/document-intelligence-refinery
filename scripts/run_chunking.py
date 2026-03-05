#!/usr/bin/env python
"""
Run Chunking on an extracted document
Usage: python scripts/run_chunking.py data/raw/sample.pdf
"""

import sys
import os
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.triage import TriageAgent
from src.agents.extractor import ExtractionRouter
from src.agents.chunker import ChunkingEngine
from src.models.ldu import ChunkType  # 👈 IMPORT ADDED HERE
from src.utils.hashing import verify_integrity
from dotenv import load_dotenv


def main():
    """Main function to run chunking"""
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("❌ Error: Please provide a PDF file path")
        print("Usage: python scripts/run_chunking.py data/raw/sample.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("📄 DOCUMENT INTELLIGENCE REFINERY")
    print("✂️  SEMANTIC CHUNKING ENGINE")
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
        
        # Step 4: Display Results
        print("\n" + "=" * 60)
        print("📊 CHUNKING RESULTS")
        print("=" * 60)
        print(f"📄 Document: {extracted.filename}")
        print(f"🆔 Doc ID: {extracted.doc_id}")
        print(f"📊 Total Chunks: {len(chunks)}")
        
        # Count by type
        chunk_types = {}
        for chunk in chunks:
            chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
        
        print("\n📋 Chunks by Type:")
        for chunk_type, count in chunk_types.items():
            print(f"  • {chunk_type}: {count}")
        
        # Show sample chunks
        print("\n🔍 Sample Chunks (first 3):")
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n  Chunk {i+1}: {chunk.ldu_id}")
            print(f"    Type: {chunk.chunk_type}")
            print(f"    Pages: {chunk.page_refs}")
            print(f"    Tokens: {chunk.token_count}")
            print(f"    Hash: {chunk.content_hash[:8]}...")
            # Preview first 80 chars of content
            preview = chunk.content[:80].replace('\n', ' ') + "..."
            print(f"    Preview: {preview}")
        
        # Step 5: Verify Hashes
        print("\n🔐 Verifying Hashes...")
        integrity = verify_integrity(chunks)
        valid_count = sum(1 for v in integrity.values() if v)
        print(f"  ✅ {valid_count}/{len(chunks)} chunks have valid hashes")
        
        # Step 6: Check Rule Compliance
        print("\n✅ Rule Compliance:")
        
        # Rule 1: Tables intact
        tables_intact = all(
            chunk.rule_compliance.get('table_intact', True) 
            for chunk in chunks if chunk.chunk_type == ChunkType.TABLE
        )
        print(f"  • Tables intact: {'✅' if tables_intact else '❌'}")
        
        # Rule 2: Captions attached
        captions_attached = all(
            chunk.rule_compliance.get('caption_attached', True) 
            for chunk in chunks if chunk.chunk_type == ChunkType.FIGURE
        )
        caption_status = '✅' if captions_attached else '⚠️  (some missing)'
        print(f"  • Captions attached: {caption_status}")
        
        # Rule 3: Lists preserved
        lists_found = any(chunk.chunk_type == ChunkType.LIST for chunk in chunks)
        if lists_found:
            lists_preserved = all(
                chunk.rule_compliance.get('list_preserved', True)
                for chunk in chunks if chunk.chunk_type == ChunkType.LIST
            )
            list_status = '✅' if lists_preserved else '❌'
        else:
            list_status = '⚠️  (no lists found)'
        print(f"  • Lists preserved: {list_status}")
        
        # Rule 4: Headers propagated
        non_header_chunks = [c for c in chunks if c.chunk_type != ChunkType.HEADER]
        if non_header_chunks:
            headers_propagated = all(
                len(chunk.section_hierarchy) > 0 
                for chunk in non_header_chunks
            )
            header_status = '✅' if headers_propagated else '⚠️  (some missing)'
        else:
            header_status = '⚠️  (no content chunks)'
        print(f"  • Headers propagated: {header_status}")
        
        # Rule 5: References resolved
        chunks_with_refs = [c for c in chunks if c.references]
        if chunks_with_refs:
            refs_resolved = all(
                all(ref.resolved for ref in chunk.references)
                for chunk in chunks_with_refs
            )
            ref_status = '✅' if refs_resolved else '⚠️  (some unresolved)'
        else:
            ref_status = '⚠️  (no references found)'
        print(f"  • References resolved: {ref_status}")
        
        # Step 7: Save chunks
        output_dir = Path(".refinery/chunks") / extracted.doc_id
        chunker.save_chunks(chunks, output_dir)
        
        print("\n✅ Chunking completed successfully!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during chunking: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())