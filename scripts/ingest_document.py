#!/usr/bin/env python
"""
Ingest document chunks into vector store and fact table
Usage: python scripts/ingest_document.py data/raw/sample.pdf
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
from src.utils.vector_store import VectorStore
from src.utils.fact_extractor import FactExtractor
from dotenv import load_dotenv


def main():
    """Main function to ingest document"""
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("❌ Error: Please provide a PDF file path")
        print("Usage: python scripts/ingest_document.py data/raw/sample.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("📄 DOCUMENT INTELLIGENCE REFINERY")
    print("📥 DOCUMENT INGESTION")
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
        
        # Step 4: Initialize stores
        print("\n🗄️  Initializing stores...")
        vector_store = VectorStore()
        fact_extractor = FactExtractor()
        
        # Step 5: Ingest into vector store
        print("\n📥 Ingesting into vector store...")
        vector_store.add_chunks(chunks, profile.doc_id)
        
        # Step 6: Extract and store facts
        print("\n📊 Extracting facts...")
        facts = fact_extractor.extract_facts_from_chunks(chunks, profile.doc_id)
        
        # Step 7: Show statistics
        print("\n" + "=" * 60)
        print("📊 INGESTION SUMMARY")
        print("=" * 60)
        print(f"📄 Document: {Path(pdf_path).name}")
        print(f"🆔 Doc ID: {profile.doc_id}")
        print(f"📑 Total chunks: {len(chunks)}")
        print(f"📊 Facts extracted: {len(facts)}")
        
        # Vector store stats
        vector_stats = vector_store.get_stats()
        print(f"\n🗄️  Vector Store:")
        print(f"   • Total chunks: {vector_stats.get('total_chunks', 0)}")
        print(f"   • Documents: {vector_stats.get('unique_documents', 0)}")
        
        # Fact table preview
        if facts:
            print(f"\n📊 Sample Facts (first 3):")
            for fact in facts[:3]:
                print(f"   • {fact['key']}: {fact['value']} (page {fact['page']})")
        
        print("\n✅ Ingestion completed successfully!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())