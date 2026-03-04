#!/usr/bin/env python
"""
Run Triage Agent on a PDF file
Usage: python scripts/run_triage.py path/to/document.pdf
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.triage import TriageAgent
from dotenv import load_dotenv


def main():
    """Main function to run triage"""
    # Load environment variables
    load_dotenv()
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("❌ Error: Please provide a PDF file path")
        print("Usage: python scripts/run_triage.py data/raw/sample.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File not found: {pdf_path}")
        sys.exit(1)
    
    # Check if it's a PDF
    if not pdf_path.lower().endswith('.pdf'):
        print(f"❌ Error: File must be a PDF: {pdf_path}")
        sys.exit(1)
    
    print("=" * 50)
    print("📄 DOCUMENT INTELLIGENCE REFINERY")
    print("🔍 TRIAGE AGENT")
    print("=" * 50)
    
    try:
        # Create triage agent
        config_path = project_root / "config" / "extraction_rules.yaml"
        agent = TriageAgent(str(config_path) if config_path.exists() else None)
        
        # Process document
        profile = agent.process_document(pdf_path)
        
        print("\n✅ Triage completed successfully!")
        print("=" * 50)
        
        # Return success
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during triage: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())