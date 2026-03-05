#!/usr/bin/env python
"""
Search documents using vector store and fact table
Usage: python scripts/search_documents.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.vector_store import VectorStore
from src.utils.fact_extractor import FactExtractor


def main():
    """Interactive search demo"""
    
    print("=" * 60)
    print("📄 DOCUMENT INTELLIGENCE REFINERY")
    print("🔍 SEARCH DEMO")
    print("=" * 60)
    
    # Initialize stores
    vector_store = VectorStore()
    fact_extractor = FactExtractor()
    
    # Show stats
    vector_stats = vector_store.get_stats()
    print(f"\n📊 Current Statistics:")
    print(f"   • Vector store: {vector_stats.get('total_chunks', 0)} chunks")
    
    fact_summary = fact_extractor.get_financial_summary()
    print(f"   • Fact table: {sum(v['count'] for v in fact_summary.values()) if fact_summary else 0} facts")
    
    while True:
        print("\n" + "=" * 60)
        print("🔍 SEARCH OPTIONS:")
        print("1. Semantic search (find chunks by meaning)")
        print("2. Fact query (SQL on numeric data)")
        print("3. Financial summary")
        print("4. Exit")
        print("=" * 60)
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            # Semantic search
            query = input("Enter search query: ").strip()
            if query:
                print(f"\n🔍 Searching for: '{query}'")
                results = vector_store.search(query, n_results=5)
                
                if results:
                    for i, r in enumerate(results, 1):
                        print(f"\n  Result {i}:")
                        print(f"    📄 Doc: {r['metadata'].get('doc_id', 'unknown')}")
                        print(f"    📑 Page: {r['metadata'].get('page', '?')}")
                        print(f"    📝 Type: {r['metadata'].get('chunk_type', 'unknown')}")
                        print(f"    📋 Preview: {r['content'][:150]}...")
                else:
                    print("  No results found")
        
        elif choice == '2':
            # Fact query
            print("\n📊 Example fact queries:")
            print("  SELECT * FROM facts WHERE key='revenue'")
            print("  SELECT * FROM facts WHERE numeric_value > 1000000")
            print("  SELECT key, AVG(numeric_value) FROM facts GROUP BY key")
            
            sql = input("\nEnter SQL query: ").strip()
            if sql:
                results = fact_extractor.query(sql)
                print(f"\n📊 Found {len(results)} results:")
                for r in results[:10]:
                    print(f"  • {r}")
        
        elif choice == '3':
            # Financial summary
            summary = fact_extractor.get_financial_summary()
            print("\n📊 Financial Summary:")
            for key, stats in summary.items():
                print(f"  • {key}: {stats['count']} occurrences, avg: ${stats['average']:,.2f}")
        
        elif choice == '4':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    main()