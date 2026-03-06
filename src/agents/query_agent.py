"""
Query Agent
LangGraph agent that answers questions using:
- PageIndex navigation
- Semantic search
- Structured query
Always returns provenance
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Try to import LangGraph
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph not installed. Run: pip install langgraph")

from src.models.provenance import ProvenanceChain, SourceCitation
from src.models.pageindex import PageIndex, SectionNode
from src.models.ldu import LDU
from src.utils.vector_store import VectorStore
from src.utils.fact_extractor import FactExtractor
from src.utils.hashing import generate_chunk_hash


class QueryTools:
    """
    Tools for the Query Agent
    Each tool performs a specific type of search
    """
    
    def __init__(self):
        """Initialize tools with access to all data sources"""
        self.vector_store = VectorStore()
        self.fact_extractor = FactExtractor()
        self.pageindex_cache = {}  # Cache for loaded PageIndex objects
        
    def load_pageindex(self, doc_id: str) -> Optional[PageIndex]:
        """
        Load PageIndex for a document from cache or disk
        """
        if doc_id in self.pageindex_cache:
            return self.pageindex_cache[doc_id]
        
        # Try to load from file
        index_path = Path(f".refinery/pageindex/{doc_id}_pageindex.json")
        if index_path.exists():
            with open(index_path, 'r') as f:
                data = json.load(f)
                # This is simplified - you'd need to reconstruct the PageIndex object
                self.pageindex_cache[doc_id] = data
                return data
        
        return None
    
    # =========================================================================
    # TOOL 1: PageIndex Navigation
    # =========================================================================
    
    def pageindex_navigate(self, query: str, doc_id: Optional[str] = None) -> List[Dict]:
        """
        Navigate the PageIndex to find relevant sections
        
        Args:
            query: User question or topic
            doc_id: Optional document ID to restrict search
            
        Returns:
            List of relevant sections with metadata
        """
        print(f"  🗺️  Navigating PageIndex for: '{query}'")
        
        # This would need all PageIndex objects
        # For now, return a structure that shows how it works
        relevant_sections = []
        
        # In a real implementation, you would:
        # 1. Load all PageIndex objects or filter by doc_id
        # 2. Search section titles and summaries for query terms
        # 3. Return the most relevant sections
        
        # For demonstration, return sample structure
        if "revenue" in query.lower():
            relevant_sections.append({
                'doc_id': 'sample_doc',
                'section_title': 'Revenue Analysis',
                'page_start': 5,
                'page_end': 7,
                'summary': 'This section discusses revenue figures for Q3 2023',
                'confidence': 0.9
            })
        
        return relevant_sections
    
    # =========================================================================
    # TOOL 2: Semantic Search
    # =========================================================================
    
    def semantic_search(self, query: str, doc_id: Optional[str] = None, n_results: int = 5) -> List[Dict]:
        """
        Search vector store for semantically similar chunks
        
        Args:
            query: User question
            doc_id: Optional document filter
            n_results: Number of results to return
            
        Returns:
            List of chunks with similarity scores
        """
        print(f"  🔍 Semantic searching for: '{query}'")
        
        if doc_id:
            results = self.vector_store.search_by_document(query, doc_id, n_results)
        else:
            results = self.vector_store.search(query, n_results)
        
        # Convert to citation-ready format
        citations = []
        for r in results:
            citation = {
                'content': r['content'],
                'metadata': r['metadata'],
                'distance': r.get('distance', 0),
                'relevance': 1 - r.get('distance', 0) if r.get('distance') else 0.5
            }
            citations.append(citation)
        
        return citations
    
    # =========================================================================
    # TOOL 3: Structured Query
    # =========================================================================
    
    def structured_query(self, query: str, doc_id: Optional[str] = None) -> List[Dict]:
        """
        Query the fact table for structured data
        
        Args:
            query: Natural language question about facts
            doc_id: Optional document filter
            
        Returns:
            List of matching facts
        """
        print(f"  📊 Querying fact table for: '{query}'")
        
        # Parse the query to extract what kind of fact we're looking for
        fact_key = None
        if 'revenue' in query.lower():
            fact_key = 'revenue'
        elif 'profit' in query.lower():
            fact_key = 'profit'
        elif 'year' in query.lower() or 'fiscal' in query.lower():
            fact_key = 'fiscal_year'
        
        if fact_key:
            # Build SQL query
            sql = f"SELECT * FROM facts WHERE key = '{fact_key}'"
            if doc_id:
                sql += f" AND doc_id = '{doc_id}'"
            sql += " ORDER BY numeric_value DESC LIMIT 10"
            
            results = self.fact_extractor.query(sql)
            return results
        
        return []
    
    # =========================================================================
    # Helper: Create Citation from Search Result
    # =========================================================================
    
    def create_citation(self, result: Dict, doc_name: str = "Unknown") -> SourceCitation:
        """
        Create a SourceCitation from a search result
        """
        metadata = result.get('metadata', {})
        
        # Get bounding box if available
        bbox = None
        # In real implementation, would extract from metadata
        
        return SourceCitation(
            document_name=doc_name,
            document_id=metadata.get('doc_id', 'unknown'),
            page_number=int(metadata.get('page', 1)),
            bbox=bbox,
            content_hash=metadata.get('hash', ''),
            extracted_text=result.get('content', '')[:200],
            chunk_id=metadata.get('chunk_id'),
            strategy_used=metadata.get('strategy', 'unknown'),
            confidence=float(metadata.get('confidence', 0.5))
        )
    
    # =========================================================================
    # Helper: Verify Claim
    # =========================================================================
    
    def verify_claim(self, claim: str, provenance: ProvenanceChain) -> bool:
        """
        Verify a claim against its source
        """
        # Check if we have a source
        if not provenance.primary_source:
            return False
        
        # Verify hash
        from src.utils.hashing import hash_text
        expected_hash = hash_text(provenance.primary_source.extracted_text)
        is_valid = expected_hash == provenance.primary_source.content_hash
        
        return is_valid
class QueryAgent:
    """
    Main Query Agent that answers questions using multiple tools
    Always returns provenance for verification
    """
    
    def __init__(self):
        """Initialize the query agent with tools"""
        self.tools = QueryTools()
        
        # State for the agent
        self.conversation_history = []
        
        print("✅ Query Agent initialized")
        print("   Tools: pageindex_navigate, semantic_search, structured_query")
    
    def answer(self, question: str, doc_id: Optional[str] = None) -> Dict:
        """
        Answer a question using all available tools
        
        Args:
            question: User's question
            doc_id: Optional document ID to restrict search
            
        Returns:
            Dictionary with answer and provenance
        """
        print(f"\n🔍 Query Agent processing: '{question}'")
        start_time = datetime.now()
        
        # Step 1: Try PageIndex navigation first (fastest)
        print("\n  Step 1: Navigating PageIndex...")
        sections = self.tools.pageindex_navigate(question, doc_id)
        
        # Step 2: If we found relevant sections, search within them
        # (In real implementation, you'd filter by section)
        print("\n  Step 2: Semantic search in relevant sections...")
        search_results = self.tools.semantic_search(question, doc_id, n_results=5)
        
        # Step 3: Query fact table for structured data
        print("\n  Step 3: Querying fact table...")
        fact_results = self.tools.structured_query(question, doc_id)
        
        # Step 4: Synthesize answer from all sources
        print("\n  Step 4: Synthesizing answer...")
        answer, provenance = self._synthesize_answer(
            question, 
            search_results, 
            fact_results,
            sections
        )
        
        # Step 5: Verify the answer
        print("\n  Step 5: Verifying claim...")
        is_verified = self.tools.verify_claim(answer, provenance)
        provenance.is_verified = is_verified
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Store in history
        self.conversation_history.append({
            'question': question,
            'answer': answer,
            'provenance': provenance,
            'timestamp': datetime.now().isoformat()
        })
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 QUERY RESULTS")
        print("=" * 60)
        print(f"❓ Question: {question}")
        print(f"💡 Answer: {answer}")
        print(f"✅ Verified: {'Yes' if is_verified else 'No'}")
        print(f"⏱️  Time: {processing_time:.0f}ms")
        print("\n📋 Provenance:")
        print(provenance.to_markdown())
        print("=" * 60)
        
        return {
            'question': question,
            'answer': answer,
            'provenance': provenance.dict_for_json(),
            'processing_time_ms': processing_time,
            'verified': is_verified
        }
    
    def _synthesize_answer(self, question: str, 
                          search_results: List[Dict],
                          fact_results: List[Dict],
                          sections: List[Dict]) -> Tuple[str, ProvenanceChain]:
        """
        Synthesize an answer from all sources
        
        This is where the magic happens - combining evidence into an answer
        """
        answer = "I couldn't find a definitive answer to your question."
        primary_source = None
        supporting_sources = []
        
        # Check fact results first (most reliable)
        if fact_results:
            # Get the most relevant fact
            fact = fact_results[0]
            key = fact.get('key', 'value')
            value = fact.get('value', '')
            numeric = fact.get('numeric_value')
            
            if numeric:
                if key == 'revenue':
                    answer = f"Revenue was ${numeric:,.2f}"
                elif key == 'profit':
                    answer = f"Profit was ${numeric:,.2f}"
                elif key == 'fiscal_year':
                    answer = f"Fiscal year: {int(numeric)}"
                else:
                    answer = f"{key}: {value}"
            else:
                answer = f"{key}: {value}"
            
            # Create citation for this fact
            # In real implementation, would get actual document name
            primary_source = self.tools.create_citation(
                {'content': value, 'metadata': fact}, 
                doc_name="Financial Report"
            )
        
        # If no facts, use search results
        elif search_results:
            best = search_results[0]
            answer = best['content'][:200] + "..."  # Truncate for display
            
            primary_source = self.tools.create_citation(
                best,
                doc_name=best.get('metadata', {}).get('doc_id', 'Unknown')
            )
            
            # Add supporting sources
            for r in search_results[1:3]:
                supporting_sources.append(
                    self.tools.create_citation(
                        r,
                        doc_name=r.get('metadata', {}).get('doc_id', 'Unknown')
                    )
                )
        
        # If we have sections but no content, use section info
        elif sections:
            section = sections[0]
            answer = f"Relevant section found: {section['section_title']}. Please search within this section."
            
            # Create basic citation
            primary_source = SourceCitation(
                document_name=section.get('doc_id', 'Unknown'),
                document_id=section.get('doc_id', 'unknown'),
                page_number=section.get('page_start', 1),
                extracted_text=section.get('summary', ''),
                content_hash="pending",
                strategy_used="pageindex",
                confidence=section.get('confidence', 0.5)
            )
        
        # Create provenance chain
        if primary_source:
            provenance = ProvenanceChain(
                claim=answer,
                primary_source=primary_source,
                supporting_sources=supporting_sources,
                all_sources=[primary_source] + supporting_sources
            )
        else:
            # No sources found
            provenance = ProvenanceChain(
                claim=answer,
                primary_source=SourceCitation(
                    document_name="No source",
                    document_id="unknown",
                    page_number=1,
                    extracted_text="No information found",
                    content_hash="none",
                    strategy_used="none",
                    confidence=0.0
                ),
                is_verified=False
            )
        
        return answer, provenance
    
    # =========================================================================
    # Audit Mode
    # =========================================================================
    
    def audit_claim(self, claim: str, provenance: Optional[ProvenanceChain] = None) -> Dict:
        """
        Audit mode: Verify a claim against source documents
        
        Args:
            claim: The claim to verify
            provenance: Optional provenance if we already have it
            
        Returns:
            Verification result
        """
        print(f"\n🔍 AUDIT MODE: Verifying claim: '{claim}'")
        
        if provenance:
            # We already have provenance, just verify it
            is_verified = self.tools.verify_claim(claim, provenance)
            
            result = {
                'claim': claim,
                'verified': is_verified,
                'method': 'hash_verification',
                'sources': [provenance.primary_source.dict_for_json()],
                'timestamp': datetime.now().isoformat()
            }
            
            status = "✅ VERIFIED" if is_verified else "❌ NOT VERIFIED"
            print(f"\n{status}")
            if is_verified:
                print(f"Source: {provenance.primary_source.to_string()}")
            
            return result
        
        else:
            # No provenance, need to search for the claim
            print("  Searching for evidence...")
            
            # Search for the claim
            results = self.tools.semantic_search(claim, n_results=3)
            
            if results:
                # Check if any result closely matches
                best = results[0]
                best_text = best['content'].lower()
                claim_lower = claim.lower()
                
                # Simple matching (in reality, would use more sophisticated)
                if claim_lower in best_text or best_text in claim_lower:
                    citation = self.tools.create_citation(
                        best,
                        doc_name=best.get('metadata', {}).get('doc_id', 'Unknown')
                    )
                    
                    result = {
                        'claim': claim,
                        'verified': True,
                        'method': 'semantic_match',
                        'confidence': 1 - best.get('distance', 0),
                        'sources': [citation.dict_for_json()],
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    print(f"\n✅ CLAIM VERIFIED")
                    print(f"Source: {citation.to_string()}")
                    print(f"Text: {best['content'][:150]}...")
                    
                    return result
            
            # No match found
            result = {
                'claim': claim,
                'verified': False,
                'method': 'no_evidence',
                'sources': [],
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"\n❌ CLAIM NOT VERIFIED - No supporting evidence found")
            return result
    
    def get_history(self) -> List[Dict]:
        """Get conversation history"""
        return self.conversation_history
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("🧹 Conversation history cleared")