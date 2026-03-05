"""
Hashing Utilities
Generate and verify content hashes for LDUs
"""


import hashlib
import json
from typing import List, Optional, Union, Dict  # 👈 Added Dict here
from pathlib import Path

from src.models.extracted_document import BoundingBox


def generate_chunk_hash(
    content: str,
    page_refs: List[int],
    bbox: Optional[BoundingBox] = None
) -> str:
    """
    Generate a unique hash for a chunk
    
    The hash includes:
    - Content text
    - Page numbers
    - Bounding box coordinates (if available)
    
    This ensures the hash changes if ANY of these change
    """
    # Create a dictionary of all components
    hash_components = {
        'content': content.strip(),
        'pages': sorted(page_refs),  # Sort for consistency
    }
    
    # Add bbox if available
    if bbox:
        hash_components['bbox'] = {
            'page': bbox.page_number,
            'x0': round(bbox.x0, 2),  # Round to avoid floating point issues
            'y0': round(bbox.y0, 2),
            'x1': round(bbox.x1, 2),
            'y1': round(bbox.y1, 2)
        }
    
    # Convert to JSON string with sorted keys for consistency
    hash_string = json.dumps(hash_components, sort_keys=True)
    
    # Generate SHA-256 hash
    return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()[:16]  # First 16 chars for readability


def verify_chunk_hash(chunk) -> bool:
    """
    Verify that a chunk's hash matches its content
    
    Args:
        chunk: LDU object with content_hash attribute
        
    Returns:
        True if hash matches, False otherwise
    """
    expected_hash = generate_chunk_hash(
        content=chunk.content,
        page_refs=chunk.page_refs,
        bbox=chunk.bbox
    )
    
    return chunk.content_hash == expected_hash


def generate_document_hash(doc_id: str, chunks: List) -> str:
    """
    Generate a hash for an entire document based on its chunks
    
    Useful for version tracking
    """
    # Collect all chunk hashes
    chunk_hashes = [chunk.content_hash for chunk in chunks]
    chunk_hashes.sort()  # Sort for consistency
    
    # Create combined hash
    combined = "|".join(chunk_hashes)
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16]


def hash_file(file_path: Union[str, Path]) -> str:
    """
    Generate hash of a file's contents
    
    Useful for checking if a file has changed
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return ""
    
    sha256 = hashlib.sha256()
    
    with open(file_path, 'rb') as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    
    return sha256.hexdigest()[:16]


def hash_text(text: str) -> str:
    """Generate hash of text content only"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def verify_integrity(chunks: List) -> Dict[str, bool]:
    """
    Verify integrity of all chunks in a list
    
    Returns:
        Dictionary mapping chunk_id -> is_valid
    """
    results = {}
    
    for chunk in chunks:
        results[chunk.ldu_id] = verify_chunk_hash(chunk)
    
    return results