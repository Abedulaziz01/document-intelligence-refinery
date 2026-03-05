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


# =============================================================================
# STEP 7.3: CHUNK VALIDATOR (The Inspector)
# =============================================================================

class ChunkValidator:
    """
    Validates chunks against the 5 chunking rules
    This class CHECKS that rules are followed
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
                        f"❌ Table {table.id} appears in multiple chunks"
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
                    f"❌ Caption {caption.ldu_id} has no target on same page"
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
                    f"❌ List {list_chunk.ldu_id} may be broken (only {list_markers} markers)"
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
                            f"❌ Chunk {chunk.ldu_id} missing header '{header.content}'"
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
            self.violations.append(f"❌ Unresolved references: {', '.join(unresolved[:3])}")
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


# =============================================================================
# STEP 7.4: CHUNKING ENGINE (The Builder)
# =============================================================================

class ChunkingEngine:
    """
    Semantic Chunking Engine
    Converts ExtractedDocument into List[LDU]
    Enforces all chunking rules
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize chunking engine"""
        self.config = config or {}
        self.validator = ChunkValidator()
        
        # Chunking settings
        self.max_tokens = self.config.get('max_tokens', 2000)
        self.min_chunk_size = self.config.get('min_chunk_size', 100)  # characters
        
    def chunk_document(self, extracted_doc: ExtractedDocument) -> List[LDU]:
        """
        Main method: Convert extracted document to LDUs
        
        Args:
            extracted_doc: Document from extraction stage
            
        Returns:
            List of LDUs following all chunking rules
        """
        chunks = []
        
        # Step 1: Process tables first (they must stay intact)
        print("  📊 Processing tables...")
        table_chunks = self._chunk_tables(extracted_doc)
        chunks.extend(table_chunks)
        print(f"     ✅ Created {len(table_chunks)} table chunks")
        
        # Step 2: Process figures with captions
        print("  🖼️  Processing figures...")
        figure_chunks = self._chunk_figures(extracted_doc)
        chunks.extend(figure_chunks)
        print(f"     ✅ Created {len(figure_chunks)} figure chunks")
        
        # Step 3: Process text blocks into semantic chunks
        print("  📝 Processing text...")
        text_chunks = self._chunk_text(extracted_doc)
        chunks.extend(text_chunks)
        print(f"     ✅ Created {len(text_chunks)} text chunks")
        
        # Step 4: Detect and preserve lists
        print("  📋 Detecting lists...")
        chunks = self._detect_and_preserve_lists(chunks)
        list_count = len([c for c in chunks if c.chunk_type == ChunkType.LIST])
        print(f"     ✅ Found {list_count} lists")
        
        # Step 5: Propagate section headers
        print("  🏷️  Propagating headers...")
        chunks = self._propagate_headers(chunks)
        
        # Step 6: Detect and resolve cross-references
        print("  🔗 Resolving references...")
        chunks = self._resolve_references(chunks)
        
        # Step 7: Add relationships (next/previous)
        print("  🔄 Adding relationships...")
        chunks = self._add_relationships(chunks)
        
        # Step 8: Generate hashes for all chunks
        print("  🔐 Generating hashes...")
        chunks = self._generate_hashes(chunks)
        
        # Step 9: Validate all rules
        print("  ✅ Validating rules...")
        validation_results = self.validator.validate_all(chunks)
        
        # Log validation results
        for rule, passed in validation_results.items():
            status = "✅" if passed else "❌"
            print(f"     {status} {rule}")
        
        if not all(validation_results.values()):
            print("\n⚠️  Validation violations found:")
            for violation in self.validator.get_violations()[:5]:
                print(f"     • {violation}")
        
        return chunks
    
    def _chunk_tables(self, doc: ExtractedDocument) -> List[LDU]:
        """
        Rule 1: Tables never split
        Each table becomes its own chunk
        """
        chunks = []
        
        for table in doc.tables:
            # Convert table to markdown for content
            content = table.to_markdown()
            
            # Create LDU
            ldu = LDU(
                ldu_id=f"table_{table.id}",
                doc_id=doc.doc_id,
                chunk_type=ChunkType.TABLE,
                content=content,
                content_hash="",  # Will be set later
                tables=[table],
                page_refs=[table.bbox.page_number] if table.bbox else [1],
                bbox=table.bbox,
                token_count=len(content.split()),
                char_count=len(content),
                word_count=len(content.split()),
                rule_compliance={'table_intact': True}
            )
            chunks.append(ldu)
        
        return chunks
    
    def _chunk_figures(self, doc: ExtractedDocument) -> List[LDU]:
        """
        Rule 2: Captions attached to figures
        """
        chunks = []
        
        for figure in doc.figures:
            content = f"[Figure: {figure.id}]\n"
            if figure.caption:
                content += f"Caption: {figure.caption}\n"
            
            ldu = LDU(
                ldu_id=f"figure_{figure.id}",
                doc_id=doc.doc_id,
                chunk_type=ChunkType.FIGURE,
                content=content,
                content_hash="",
                page_refs=[figure.bbox.page_number] if figure.bbox else [1],
                bbox=figure.bbox,
                token_count=len(content.split()),
                char_count=len(content),
                word_count=len(content.split()),
                rule_compliance={'caption_attached': bool(figure.caption)}
            )
            chunks.append(ldu)
        
        return chunks
    
    def _chunk_text(self, doc: ExtractedDocument) -> List[LDU]:
        """
        Chunk text into semantic units
        Respects paragraphs, sections, and reading order
        """
        chunks = []
        
        # Sort text blocks by reading order
        text_blocks = sorted(
            doc.text_blocks,
            key=lambda x: (x.bbox.page_number, x.bbox.y0) if x.bbox else (0, 0)
        )
        
        current_chunk = []
        current_tokens = 0
        
        for block in text_blocks:
            block_tokens = len(block.text.split())
            
            # Start new chunk if this block would exceed max tokens
            if current_tokens + block_tokens > self.max_tokens and current_chunk:
                # Save current chunk
                chunk = self._create_text_chunk(current_chunk, doc.doc_id)
                chunks.append(chunk)
                current_chunk = []
                current_tokens = 0
            
            current_chunk.append(block)
            current_tokens += block_tokens
        
        # Don't forget the last chunk
        if current_chunk:
            chunk = self._create_text_chunk(current_chunk, doc.doc_id)
            chunks.append(chunk)
        
        return chunks
    
    def _create_text_chunk(self, blocks: List, doc_id: str) -> LDU:
        """Create a text chunk from a list of text blocks"""
        # Combine text
        content = "\n\n".join([block.text for block in blocks])
        
        # Get page references
        page_refs = list(set(block.bbox.page_number for block in blocks if block.bbox))
        page_refs.sort()
        
        # Get first block's bbox as approximate location
        first_bbox = blocks[0].bbox if blocks else None
        
        # Determine if this might be a header
        is_header = any(
            getattr(block, 'block_type', '') == 'header' 
            for block in blocks
        )
        
        # Generate a simple ID
        import hashlib
        chunk_id = hashlib.md5(content[:50].encode()).hexdigest()[:8]
        
        return LDU(
            ldu_id=f"chunk_{chunk_id}",
            doc_id=doc_id,
            chunk_type=ChunkType.HEADER if is_header else ChunkType.TEXT,
            content=content,
            content_hash="",
            page_refs=page_refs,
            bbox=first_bbox,
            token_count=len(content.split()),
            char_count=len(content),
            word_count=len(content.split())
        )
    
    def _detect_and_preserve_lists(self, chunks: List[LDU]) -> List[LDU]:
        """
        Rule 3: Lists preserved as single units
        Detect if any text chunks are actually lists and mark them
        """
        new_chunks = []
        
        for chunk in chunks:
            if chunk.chunk_type == ChunkType.TEXT:
                content = chunk.content
                lines = content.split('\n')
                
                # Check for list patterns
                list_pattern = r'^\s*[\d\-•*]+\.?\s'
                list_lines = sum(1 for line in lines if re.match(list_pattern, line))
                
                # If more than 30% of lines are list items, treat as list
                if len(lines) > 0 and list_lines / len(lines) > 0.3:
                    chunk.chunk_type = ChunkType.LIST
                    chunk.rule_compliance['list_preserved'] = True
            
            new_chunks.append(chunk)
        
        return new_chunks
    
    def _propagate_headers(self, chunks: List[LDU]) -> List[LDU]:
        """
        Rule 4: Section headers propagated to all child chunks
        """
        # Find all header chunks
        headers = [c for c in chunks if c.chunk_type == ChunkType.HEADER]
        
        # Sort by page
        headers.sort(key=lambda x: x.page_refs[0] if x.page_refs else 0)
        
        for chunk in chunks:
            if chunk.chunk_type != ChunkType.HEADER:
                # Find applicable headers (headers on same or previous page)
                chunk_page = chunk.page_refs[0] if chunk.page_refs else 1
                
                applicable_headers = []
                for header in headers:
                    header_page = header.page_refs[0] if header.page_refs else 1
                    if header_page <= chunk_page:
                        applicable_headers.append(header.content)
                
                # Use last 3 headers as hierarchy
                chunk.section_hierarchy = applicable_headers[-3:]
        
        return chunks
    
    def _resolve_references(self, chunks: List[LDU]) -> List[LDU]:
        """
        Rule 5: Cross-references resolved
        Find references like "see Table 3" and link them
        """
        # Build lookup of chunks by ID and type
        table_chunks = {c.ldu_id: c for c in chunks if c.chunk_type == ChunkType.TABLE}
        figure_chunks = {c.ldu_id: c for c in chunks if c.chunk_type == ChunkType.FIGURE}
        
        # Patterns for references
        table_pattern = r'(?:see|refer to|in)\s+[Tt]able\s+(\d+)'
        figure_pattern = r'(?:see|refer to|in)\s+[Ff]igure\s+(\d+)'
        
        for chunk in chunks:
            content = chunk.content
            
            # Find table references
            table_refs = re.findall(table_pattern, content)
            for ref_num in table_refs:
                # Look for matching table
                for table_id, table_chunk in table_chunks.items():
                    if f"Table {ref_num}" in table_chunk.content:
                        ref = CrossReference(
                            reference_text=f"Table {ref_num}",
                            target_id=table_id,
                            target_type="table",
                            resolved=True,
                            page_number=chunk.page_refs[0] if chunk.page_refs else 1
                        )
                        chunk.references.append(ref)
                        
                        # Also add reverse reference
                        if not hasattr(table_chunk, 'referenced_by') or table_chunk.referenced_by is None:
                            table_chunk.referenced_by = []
                        table_chunk.referenced_by.append(chunk.ldu_id)
                        break
            
            # Find figure references (similar pattern)
            figure_refs = re.findall(figure_pattern, content)
            for ref_num in figure_refs:
                for figure_id, figure_chunk in figure_chunks.items():
                    if f"Figure {ref_num}" in figure_chunk.content:
                        ref = CrossReference(
                            reference_text=f"Figure {ref_num}",
                            target_id=figure_id,
                            target_type="figure",
                            resolved=True,
                            page_number=chunk.page_refs[0] if chunk.page_refs else 1
                        )
                        chunk.references.append(ref)
                        
                        if not hasattr(figure_chunk, 'referenced_by') or figure_chunk.referenced_by is None:
                            figure_chunk.referenced_by = []
                        figure_chunk.referenced_by.append(chunk.ldu_id)
                        break
        
        return chunks
    
    def _add_relationships(self, chunks: List[LDU]) -> List[LDU]:
        """Add next/previous relationships based on reading order"""
        # Sort by page and position
        def sort_key(chunk):
            if chunk.bbox:
                return (chunk.bbox.page_number, chunk.bbox.y0)
            return (chunk.page_refs[0] if chunk.page_refs else 0, 0)
        
        sorted_chunks = sorted(chunks, key=sort_key)
        
        # Link them
        for i, chunk in enumerate(sorted_chunks):
            if i > 0:
                chunk.previous_chunk_id = sorted_chunks[i-1].ldu_id
            if i < len(sorted_chunks) - 1:
                chunk.next_chunk_id = sorted_chunks[i+1].ldu_id
        
        return sorted_chunks
    
    def _generate_hashes(self, chunks: List[LDU]) -> List[LDU]:
        """Generate content hashes for all chunks"""
        for chunk in chunks:
            chunk.content_hash = generate_chunk_hash(
                content=chunk.content,
                page_refs=chunk.page_refs,
                bbox=chunk.bbox
            )
        return chunks
    
    def save_chunks(self, chunks: List[LDU], output_dir: Path):
        """Save chunks to JSON files"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save individual chunks
        for chunk in chunks:
            chunk_path = output_dir / f"{chunk.ldu_id}.json"
            with open(chunk_path, 'w') as f:
                import json
                json.dump(chunk.dict_for_json(), f, indent=2)
        
        # Save manifest
        manifest = {
            'doc_id': chunks[0].doc_id if chunks else 'unknown',
            'chunk_count': len(chunks),
            'chunks': [c.ldu_id for c in chunks],
            'created_at': datetime.now().isoformat()
        }
        
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"  💾 Saved {len(chunks)} chunks to {output_dir}")