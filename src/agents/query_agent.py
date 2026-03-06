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