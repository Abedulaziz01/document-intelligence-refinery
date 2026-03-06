#!/usr/bin/env python
"""
Run Query Agent interactively
Usage: python scripts/run_query.py [--doc DOC_ID] [--question "your question"]
"""

import sys
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.query_agent import QueryAgent
from src.models.provenance import ProvenanceChain


def main():
    """Interactive query agent"""
    parser = argparse.ArgumentParser(description='Query documents')
    parser.add_argument('--doc', help='Document ID to restrict search')
    parser.add_argument('--question', help='Question to ask (non-interactive mode)')
    parser.add_argument('--audit', help='Claim to audit')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("📄 DOCUMENT INTELLIGENCE REFINERY")
    print("🔍 QUERY AGENT")
    print("=" * 60)
    
    # Initialize agent
    agent = QueryAgent()
    
    # Audit mode
    if args.audit:
        print(f"\n🔍 Audit mode activated")
        result = agent.audit_claim(args.audit)
        print("\n" + "=" * 60)
        return 0
    
    # Single question mode
    if args.question:
        print(f"\n❓ Question: {args.question}")
        result = agent.answer(args.question, args.doc)
        return 0
    
    # Interactive mode
    print("\nInteractive mode - Type your questions (or 'quit' to exit)")
    print("Commands:")
    print("  /audit <claim> - Audit a claim")
    print("  /history - Show conversation history")
    print("  /clear - Clear history")
    print("  /quit - Exit")
    print("-" * 60)
    
    while True:
        try:
            question = input("\n❓ Your question: ").strip()
            
            if question.lower() in ['quit', 'exit', '/quit']:
                print("\n👋 Goodbye!")
                break
            
            elif question.lower() == '/history':
                history = agent.get_history()
                print(f"\n📜 Conversation History ({len(history)} messages):")
                for i, h in enumerate(history[-5:], 1):
                    print(f"  {i}. Q: {h['question']}")
                    print(f"     A: {h['answer'][:50]}...")
                continue
            
            elif question.lower() == '/clear':
                agent.clear_history()
                continue
            
            elif question.startswith('/audit '):
                claim = question[7:].strip()
                result = agent.audit_claim(claim)
                continue
            
            elif not question:
                continue
            
            # Answer the question
            result = agent.answer(question, args.doc)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())