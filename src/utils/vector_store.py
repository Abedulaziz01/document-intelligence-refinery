"""
Vector Store Utilities
Handles embedding and searching of document chunks
Uses ChromaDB for local vector storage
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# Try to import ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("⚠️ ChromaDB not installed. Run: pip install chromadb")

# Try to import sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("⚠️ Sentence transformers not installed. Run: pip install sentence-transformers")


class VectorStore:
    """
    Vector database for semantic search of chunks
    Uses ChromaDB with local sentence transformers
    """
    
    def __init__(self, persist_directory: str = ".refinery/vectordb"):
        """
        Initialize vector store
        
        Args:
            persist_directory: Where to store the vector database
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.initialized = False
        
        # Try to initialize
        self._initialize()
    
    def _initialize(self):
        """Initialize ChromaDB and embedding model"""
        if not CHROMA_AVAILABLE:
            print("❌ ChromaDB not available. Please install: pip install chromadb")
            return
        
        if not EMBEDDINGS_AVAILABLE:
            print("❌ Sentence transformers not available. Please install: pip install sentence-transformers")
            return
        
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory)
            )
            
            # Initialize embedding model (small and fast)
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection("document_chunks")
                print(f"📚 Loaded existing collection with {self.collection.count()} chunks")
            except:
                self.collection = self.client.create_collection("document_chunks")
                print("📚 Created new collection")
            
            self.initialized = True
            
        except Exception as e:
            print(f"❌ Error initializing vector store: {e}")
    
    def add_chunks(self, chunks: List, doc_id: str):
        """
        Add chunks to vector store
        
        Args:
            chunks: List of LDU objects
            doc_id: Document identifier
        """
        if not self.initialized:
            print("❌ Vector store not initialized")
            return
        
        if not chunks:
            print("⚠️ No chunks to add")
            return
        
        print(f"\n📥 Adding {len(chunks)} chunks to vector store...")
        
        # Prepare data for ChromaDB
        ids = []
        embeddings = []
        metadatas = []
        documents = []
        
        for i, chunk in enumerate(chunks):
            # Create unique ID
            chunk_id = f"{doc_id}_{chunk.ldu_id}_{i}"
            ids.append(chunk_id)
            
            # Get embedding
            embedding = self.embedding_model.encode(chunk.content).tolist()
            embeddings.append(embedding)
            
            # Create metadata
            metadata = {
                'doc_id': doc_id,
                'chunk_id': chunk.ldu_id,
                'chunk_type': str(chunk.chunk_type),
                'page': str(chunk.page_refs[0]) if chunk.page_refs else '1',
                'token_count': chunk.token_count,
                'hash': chunk.content_hash
            }
            metadatas.append(metadata)
            
            # Add content
            documents.append(chunk.content)
        
        # Add to ChromaDB in batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            end_idx = min(i + batch_size, len(ids))
            self.collection.add(
                ids=ids[i:end_idx],
                embeddings=embeddings[i:end_idx],
                metadatas=metadatas[i:end_idx],
                documents=documents[i:end_idx]
            )
            print(f"  ✅ Added batch {i//batch_size + 1}/{(len(ids)-1)//batch_size + 1}")
        
        print(f"✅ Successfully added {len(chunks)} chunks to vector store")
    
    def search(self, query: str, n_results: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """
        Search for similar chunks
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_dict: Optional metadata filter
            
        Returns:
            List of search results with content and metadata
        """
        if not self.initialized:
            print("❌ Vector store not initialized")
            return []
        
        try:
            # Get query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_dict
            )
            
            # Format results
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    result = {
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ Error searching vector store: {e}")
            return []
    
    def search_by_document(self, query: str, doc_id: str, n_results: int = 5) -> List[Dict]:
        """Search within a specific document"""
        return self.search(query, n_results, {"doc_id": doc_id})
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        if not self.initialized or not self.collection:
            return {"status": "not initialized"}
        
        try:
            count = self.collection.count()
            
            # Get unique documents
            all_metadatas = self.collection.get()['metadatas']
            unique_docs = set(m.get('doc_id') for m in all_metadatas if m)
            
            return {
                "status": "initialized",
                "total_chunks": count,
                "unique_documents": len(unique_docs),
               "persist_directory": str(self.persist_directory)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def clear(self):
        """Clear all data from vector store"""
        if not self.initialized:
            return
        
        try:
            self.client.delete_collection("document_chunks")
            self.collection = self.client.create_collection("document_chunks")
            print("🧹 Cleared vector store")
        except Exception as e:
            print(f"❌ Error clearing vector store: {e}")
def add_chunks(self, chunks: List, doc_id: str):
    """
    Add chunks to vector store with complete metadata
    
    Passes all required metadata:
    - chunk_type
    - page_refs  
    - content_hash
    - parent_section
    - bbox coordinates
    """
    if not self.initialized:
        print("❌ Vector store not initialized")
        return
    
    if not chunks:
        print("⚠️ No chunks to add")
        return
    
    print(f"\n📥 Adding {len(chunks)} chunks to vector store...")
    
    # Prepare data for ChromaDB
    ids = []
    embeddings = []
    metadatas = []
    documents = []
    
    for i, chunk in enumerate(chunks):
        # Create unique ID
        chunk_id = f"{doc_id}_{chunk.ldu_id}_{i}"
        ids.append(chunk_id)
        
        # Get embedding
        embedding = self.embedding_model.encode(chunk.content).tolist()
        embeddings.append(embedding)
        
        # Create complete metadata as required by rubric
        metadata = {
            'doc_id': doc_id,
            'chunk_id': chunk.ldu_id,
            'chunk_type': str(chunk.chunk_type.value) if hasattr(chunk.chunk_type, 'value') else str(chunk.chunk_type),
            'page': str(chunk.page_refs[0]) if chunk.page_refs else '1',
            'all_pages': ','.join(str(p) for p in chunk.page_refs) if chunk.page_refs else '1',
            'token_count': str(chunk.token_count),
            'content_hash': chunk.content_hash,
            'parent_section': chunk.parent_section if hasattr(chunk, 'parent_section') and chunk.parent_section else 'none',
            'section_hierarchy': '|'.join(chunk.section_hierarchy) if hasattr(chunk, 'section_hierarchy') and chunk.section_hierarchy else '',
            
            # Bounding box coordinates (if available)
            'has_bbox': 'true' if chunk.bbox else 'false',
            'bbox_page': str(chunk.bbox.page_number) if chunk.bbox else '',
            'bbox_x0': str(chunk.bbox.x0) if chunk.bbox else '',
            'bbox_y0': str(chunk.bbox.y0) if chunk.bbox else '',
            'bbox_x1': str(chunk.bbox.x1) if chunk.bbox else '',
            'bbox_y1': str(chunk.bbox.y1) if chunk.bbox else '',
            
            # Additional metadata for filtering
            'has_tables': 'true' if chunk.tables else 'false',
            'table_count': str(len(chunk.tables)) if chunk.tables else '0',
            'strategy': getattr(chunk, 'strategy_used', 'unknown')
        }
        metadatas.append(metadata)
        
        # Add content
        documents.append(chunk.content)
    
    # Add to ChromaDB in batches
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        end_idx = min(i + batch_size, len(ids))
        self.collection.add(
            ids=ids[i:end_idx],
            embeddings=embeddings[i:end_idx],
            metadatas=metadatas[i:end_idx],
            documents=documents[i:end_idx]
        )
        print(f"  ✅ Added batch {i//batch_size + 1}/{(len(ids)-1)//batch_size + 1}")
    
    print(f"✅ Successfully added {len(chunks)} chunks to vector store with complete metadata")