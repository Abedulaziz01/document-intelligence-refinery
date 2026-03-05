"""
Semantic Chunking Engine
Splits documents into Logical Document Units (LDUs)
Enforces 5 chunking rules
"""

import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from pathlib import Path

from src.models.ldu import LDU, ChunkType, CrossReference
from src.models.extracted_document import ExtractedDocument, ExtractedTable
from src.utils.hashing import generate_chunk_hash


class ChunkValidator:
    """
    Validates chunks against the 5 chunking rules
    """
    
    def __init__(self):
        self.violations = []
    
    def validate_rule_1_no_table_split(self, chunks: List[LDU]) -> bool:
        """
        Rule 1: Tables never split
        Each table should be in exactly ONE chunk
        """
        table_chunks = [c for c in chunks if c.chunk_type == ChunkType.TABLE]
        table_ids = set()
        
        for chunk in table_chunks:
            for table in chunk.tables:
                if table.id in table_ids:
                    self.violations.append(
                        f"Table {table.id} appears in multiple chunks"
                    )
                    return False
                table_ids.add(table.id)
        
        return True
    
    def validate_rule_2_captions_attached(self, chunks: List[LDU]) -> bool:
        """
        Rule 2: Captions attached to their figures/tables
        """
        # Find all chunks with captions
        caption_chunks = [c for c in chunks if c.chunk_type == ChunkType.CAPTION]
        
        for caption in caption_chunks:
            # Check if caption is near its target (simplified)
            has_target = False
            for chunk in chunks:
                if chunk.ldu_id != caption.ldu_id:
                    # Check if pages overlap
                    if set(chunk.page_refs) & set(caption.page_refs):
                        # Caption and content on same page - good enough for now
                        has_target = True
                        break
            
            if not has_target:
                self.violations.append(
                    f"Caption {caption.ldu_id} has no target on same page"
                )
                return False
        
        return True
    
    def validate_rule_3_lists_preserved(self, chunks: List[LDU]) -> bool:
        """
        Rule 3: Lists preserved as single units
        """
        list_chunks = [c for c in chunks if c.chunk_type == ChunkType.LIST]
        
        for list_chunk in list_chunks:
            content = list_chunk.content
            
            # Check if list items are numbered/bulleted consistently
            lines = content.split('\n')
            list_markers = 0
            
            for line in lines:
                # Check for common list markers
                if re.match(r'^\s*[\d\-•*]+\.?\s', line):
                    list_markers += 1
            
            # If we have multiple lines but only one marker, might be broken list
            if len(lines) > 3 and list_markers < 2:
                self.violations.append(
                    f"List {list_chunk.ldu_id} may be broken (only {list_markers} markers)"
                )
                return False
        
        return True
    
    def validate_rule_4_headers_propagated(self, chunks: List[LDU]) -> bool:
        """
        Rule 4: Section headers propagated to all child chunks
        """
        # Find header chunks
        header_chunks = [c for c in chunks if c.chunk_type == ChunkType.HEADER]
        
        for header in header_chunks:
            # Find chunks on same/similar pages that should inherit this header
            header_page = header.page_refs[0] if header.page_refs else None
            
            if header_page:
                following_chunks = [
                    c for c in chunks 
                    if c.page_refs and c.page_refs[0] >= header_page
                    and c.ldu_id != header.ldu_id
                ]
                
                for chunk in following_chunks[:5]:  # Check next 5 chunks
                    # Should have this header in their hierarchy
                    if header.content not in chunk.section_hierarchy:
                        self.violations.append(
                            f"Chunk {chunk.ldu_id} missing header '{header.content}'"
                        )
                        return False
        
        return True
    
    def validate_rule_5_references_resolved(self, chunks: List[LDU]) -> bool:
        """
        Rule 5: Cross-references resolved
        """
        unresolved = []
        
        for chunk in chunks:
            for ref in chunk.references:
                if not ref.resolved:
                    unresolved.append(f"{chunk.ldu_id}: '{ref.reference_text}'")
        
        if unresolved:
            self.violations.append(f"Unresolved references: {', '.join(unresolved[:3])}")
            return False
        
        return True
    
    def validate_all(self, chunks: List[LDU]) -> Dict[str, bool]:
        """
        Validate all 5 rules
        
        Returns:
            Dictionary of rule_name -> passed
        """
        self.violations = []
        
        results = {
            'rule_1_no_table_split': self.validate_rule_1_no_table_split(chunks),
            'rule_2_captions_attached': self.validate_rule_2_captions_attached(chunks),
            'rule_3_lists_preserved': self.validate_rule_3_lists_preserved(chunks),
            'rule_4_headers_propagated': self.validate_rule_4_headers_propagated(chunks),
            'rule_5_references_resolved': self.validate_rule_5_references_resolved(chunks)
        }
        
        return results
    
    def get_violations(self) -> List[str]:
        """Get list of validation violations"""
        return self.violations