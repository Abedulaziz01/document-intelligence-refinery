#!/usr/bin/env python
"""
Run Extraction on a PDF file
Usage: python scripts/run_extraction.py path/to/document.pdf
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
from dotenv import load_dotenv


def main():
    """Main function to run extraction"""
    # Load environment variables (for API keys)
    load_dotenv()
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("❌ Error: Please provide a PDF file path")
        print("Usage: python scripts/run_extraction.py data/raw/sample.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("📄 DOCUMENT INTELLIGENCE REFINERY")
    print("🔧 EXTRACTION ENGINE")
    print("=" * 60)
    print(f"📁 File: {pdf_path}")
    
    try:
        # Step 1: Run Triage to get profile
        print("\n🔍 Running Triage...")
        triage_agent = TriageAgent()
        profile = triage_agent.process_document(pdf_path)
        
        # Step 2: Run Extraction
        print("\n🔧 Running Extraction...")
        config_path = project_root / "config" / "extraction_rules.yaml"
        router = ExtractionRouter(str(config_path) if config_path.exists() else None)
        
        extracted_doc = router.extract(pdf_path, profile)
        
        # Step 3: Print Results
        print("\n" + "=" * 60)
        print("📊 EXTRACTION RESULTS")
        print("=" * 60)
        print(f"📄 Document: {extracted_doc.filename}")
        print(f"🆔 Doc ID: {extracted_doc.doc_id}")
        print(f"📊 Strategy: {extracted_doc.strategy_used}")
        print(f"✅ Confidence: {extracted_doc.overall_confidence:.2f}")
        print(f"📑 Pages: {extracted_doc.page_count}")
        print(f"📋 Text Blocks: {len(extracted_doc.text_blocks)}")
        print(f"📊 Tables Found: {len(extracted_doc.tables)}")
        print(f"⏱️  Time: {extracted_doc.extraction_time_ms:.0f}ms")
        
        # Step 4: Show ledger
        print("\n" + "=" * 60)
        print("📋 RECENT LEDGER ENTRIES")
        print("=" * 60)
        
        ledger_path = Path(".refinery/extraction_ledger.jsonl")
        if ledger_path.exists():
            with open(ledger_path, 'r') as f:
                lines = f.readlines()
                # Show last 3 entries
                for line in lines[-3:]:
                    entry = json.loads(line)
                    print(f"  • {entry['strategy_used']}: confidence={entry['confidence_score']:.2f}, "
                          f"cost=${entry['cost_estimate']:.4f}, time={entry['processing_time_ms']:.0f}ms")
        
        print("\n✅ Extraction completed successfully!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())