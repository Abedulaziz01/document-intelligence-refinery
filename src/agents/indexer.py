"""
PageIndex Builder
Creates a hierarchical navigation structure from document chunks
Uses LLM for summarization and entity extraction
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

import google.generativeai as genai

from src.models.pageindex import PageIndex, SectionNode, DataType, ExtractedEntity, EntityType
from src.models.ldu import LDU, ChunkType


class PageIndexBuilder:
    """
    Builds a PageIndex tree from document chunks
    Enables navigation without vector search
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the PageIndex builder"""
        self.config = config or {}
        
        # Initialize Gemini for summarization (if API key available)
        self.use_llm = False
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.llm = genai.GenerativeModel('gemini-1.5-flash')
                self.use_llm = True
                print("✅ LLM initialized for summaries")
            except:
                print("⚠️ LLM initialization failed, using rule-based fallback")
        else:
            print("⚠️ No Gemini API key found, using rule-based summaries")
        
        # Entity patterns for rule-based extraction
        self.entity_patterns = {
            EntityType.MONEY: r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|dollars)',
            EntityType.PERCENTAGE: r'\d+(?:\.\d+)?\s*%',
            EntityType.DATE: r'\d{4}|\d{1,2}/\d{1,2}/\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}',
            EntityType.ORGANIZATION: r'\b[A-Z][a-z]+ (?:Inc|Corp|Company|Bank|Group|LLC|Ltd)\b',
        }
    
    def build_index(self, doc_id: str, filename: str, chunks: List[LDU]) -> PageIndex:
        """
        Build PageIndex from document chunks
        
        Args:
            doc_id: Document identifier
            filename: Original filename
            chunks: List of LDUs from chunking engine
            
        Returns:
            PageIndex tree structure
        """
        print(f"\n🏗️  Building PageIndex for: {filename}")
        
        # Step 1: Group chunks into sections based on headers
        print("  📋 Grouping chunks into sections...")
        sections = self._group_into_sections(chunks)
        print(f"     ✅ Found {len(sections)} sections")
        
        # Step 2: Build the tree structure
        print("  🌳 Building section tree...")
        root_sections, section_by_id = self._build_section_tree(sections)
        
        # Step 3: Extract entities from each section
        print("  🔍 Extracting entities...")
        self._extract_entities(sections, section_by_id)
        
        # Step 4: Determine data types present
        print("  📊 Determining data types...")
        self._determine_data_types(sections, section_by_id, chunks)
        
        # Step 5: Generate summaries (using LLM if available)
        print("  📝 Generating summaries...")
        self._generate_summaries(sections, section_by_id)
        
        # Step 6: Collect global entities
        print("  🌍 Collecting global entities...")
        global_entities = self._collect_global_entities(section_by_id)
        
        # Step 7: Calculate statistics
        total_sections = len(section_by_id)
        max_depth = self._calculate_max_depth(root_sections)
        
        # Step 8: Create PageIndex
        page_index = PageIndex(
            doc_id=doc_id,
            filename=filename,
            total_pages=self._get_total_pages(chunks),
            root_sections=root_sections,
            section_by_id=section_by_id,
            total_sections=total_sections,
            max_depth=max_depth,
            global_entities=global_entities,
            created_at=datetime.now()
        )
        
        print(f"\n✅ PageIndex built successfully!")
        print(f"   📁 {total_sections} sections, max depth {max_depth}")
        
        return page_index
    
    def _group_into_sections(self, chunks: List[LDU]) -> Dict[str, List[LDU]]:
        """
        Group chunks into sections based on headers
        Returns: dict mapping section_id -> list of chunks
        """
        sections = {}
        
        # Find all header chunks
        header_chunks = [c for c in chunks if c.chunk_type == ChunkType.HEADER]
        
        if not header_chunks:
            # No headers found, treat entire document as one section
            sections['root'] = chunks
            return sections
        
        # Sort chunks by page and position
        def sort_key(chunk):
            if chunk.bbox:
                return (chunk.bbox.page_number, chunk.bbox.y0)
            return (chunk.page_refs[0] if chunk.page_refs else 0, 0)
        
        sorted_chunks = sorted(chunks, key=sort_key)
        
        # Group chunks under nearest previous header
        current_section = None
        current_section_chunks = []
        
        for chunk in sorted_chunks:
            if chunk.chunk_type == ChunkType.HEADER:
                # Save previous section
                if current_section and current_section_chunks:
                    sections[current_section.ldu_id] = current_section_chunks
                
                # Start new section
                current_section = chunk
                current_section_chunks = [chunk]
            else:
                if current_section:
                    current_section_chunks.append(chunk)
                else:
                    # Chunks before first header
                    if 'preamble' not in sections:
                        sections['preamble'] = []
                    sections['preamble'].append(chunk)
        
        # Don't forget last section
        if current_section and current_section_chunks:
            sections[current_section.ldu_id] = current_section_chunks
        
        return sections
    
    def _build_section_tree(self, sections: Dict[str, List[LDU]]) -> Tuple[List[SectionNode], Dict[str, SectionNode]]:
        """
        Build hierarchical tree from flat sections
        Returns: (root_sections, section_by_id)
        """
        section_by_id = {}
        root_sections = []
        
        # First pass: create SectionNode for each section
        for section_id, chunks in sections.items():
            if section_id == 'preamble':
                # Special handling for preamble
                title = "Document Introduction"
                level = 1
                page_start = min((c.page_refs[0] for c in chunks if c.page_refs), default=1)
                page_end = max((c.page_refs[-1] for c in chunks if c.page_refs), default=1)
            else:
                # Find the header chunk
                header_chunk = next((c for c in chunks if c.chunk_type == ChunkType.HEADER), None)
                title = header_chunk.content if header_chunk else f"Section {section_id[:8]}"
                level = len(header_chunk.section_hierarchy) if header_chunk else 1
                
                # Get page range
                pages = []
                for c in chunks:
                    if c.page_refs:
                        pages.extend(c.page_refs)
                page_start = min(pages) if pages else 1
                page_end = max(pages) if pages else 1
            
            # Create section node
            section = SectionNode(
                section_id=section_id,
                title=title[:100],  # Limit length
                level=level,
                page_start=page_start,
                page_end=page_end,
                chunk_count=len(chunks),
                all_chunk_ids=[c.ldu_id for c in chunks]
            )
            
            section_by_id[section_id] = section
        
        # Second pass: build hierarchy
        for section_id, section in section_by_id.items():
            if section_id == 'preamble':
                root_sections.append(section)
                continue
            
            # Try to find parent based on level and position
            parent_found = False
            for other_id, other in section_by_id.items():
                if (other.level < section.level and 
                    other.page_start <= section.page_start and
                    other_id != section_id and
                    other_id != 'preamble'):
                    
                    # Check if this is the closest parent
                    if not section.parent_id or other.level > section_by_id[section.parent_id].level:
                        section.parent_id = other_id
                        parent_found = True
            
            if not parent_found:
                # No parent found, add to root
                root_sections.append(section)
        
        # Build child lists
        for section in section_by_id.values():
            if section.parent_id and section.parent_id in section_by_id:
                parent = section_by_id[section.parent_id]
                if section not in parent.child_sections:
                    parent.child_sections.append(section)
        
        # Sort children by page number
        for section in section_by_id.values():
            section.child_sections.sort(key=lambda x: x.page_start)
        
        # Sort root sections
        root_sections.sort(key=lambda x: x.page_start)
        
        return root_sections, section_by_id
    
    def _extract_entities(self, sections: Dict[str, List[LDU]], section_by_id: Dict[str, SectionNode]):
        """Extract named entities from each section"""
        
        for section_id, chunks in sections.items():
            if section_id not in section_by_id:
                continue
            
            section = section_by_id[section_id]
            
            # Combine all text in section
            all_text = " ".join([c.content for c in chunks])
            
            # Use LLM for entity extraction if available
            if self.use_llm:
                entities = self._extract_entities_with_llm(all_text, section.page_start)
            else:
                # Rule-based extraction
                entities = self._extract_entities_rule_based(all_text, section.page_start)
            
            section.entities = entities
            section.key_entities = [e.text for e in entities[:5]]  # Top 5 entities
    
    def _extract_entities_rule_based(self, text: str, page_num: int) -> List[ExtractedEntity]:
        """Extract entities using regex patterns"""
        entities = []
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                entity = ExtractedEntity(
                    text=match.group(),
                    entity_type=entity_type,
                    confidence=0.7,  # Rule-based confidence
                    mentions=[page_num]
                )
                entities.append(entity)
        
        return entities
    
    def _extract_entities_with_llm(self, text: str, page_num: int) -> List[ExtractedEntity]:
        """Extract entities using LLM"""
        try:
            # Truncate text if too long
            if len(text) > 2000:
                text = text[:2000] + "..."
            
            prompt = f"""
            Extract important named entities from this text. Return as JSON list with:
            - text: the entity text
            - type: one of [person, organization, date, money, percentage, location]
            - confidence: 0.0-1.0
            
            Text: {text}
            """
            
            response = self.llm.generate_content(prompt)
            
            # Parse response (simplified)
            entities = []
            if response and response.text:
                # Very basic parsing - in real world, use proper JSON parsing
                if "person" in response.text.lower():
                    entities.append(ExtractedEntity(
                        text="Entity found",
                        entity_type=EntityType.PERSON,
                        confidence=0.8,
                        mentions=[page_num]
                    ))
            
            return entities
            
        except Exception as e:
            print(f"⚠️ LLM entity extraction failed: {e}")
            return []
    
    def _determine_data_types(self, sections: Dict[str, List[LDU]], 
                              section_by_id: Dict[str, SectionNode],
                              all_chunks: List[LDU]):
        """Determine what types of data are in each section"""
        
        # Build lookup of chunks by ID
        chunk_by_id = {c.ldu_id: c for c in all_chunks}
        
        for section_id, chunks in sections.items():
            if section_id not in section_by_id:
                continue
            
            section = section_by_id[section_id]
            data_types = set()
            
            for chunk in chunks:
                # Check chunk type
                if chunk.chunk_type == ChunkType.TABLE:
                    data_types.add(DataType.TABLE)
                elif chunk.chunk_type == ChunkType.FIGURE:
                    data_types.add(DataType.FIGURE)
                elif chunk.chunk_type == ChunkType.LIST:
                    data_types.add(DataType.LIST)
                elif chunk.chunk_type == ChunkType.TEXT:
                    data_types.add(DataType.TEXT)
                
                # Check for equations
                if '=' in chunk.content or '∑' in chunk.content or '∫' in chunk.content:
                    data_types.add(DataType.EQUATION)
                
                # Check for footnotes
                if any(c.isdigit() for c in chunk.content[:10]) and 'note' in chunk.content.lower():
                    data_types.add(DataType.FOOTNOTE)
            
            section.data_types_present = list(data_types)
            
            # Count tables and figures
            section.table_count = len([c for c in chunks if c.chunk_type == ChunkType.TABLE])
            section.figure_count = len([c for c in chunks if c.chunk_type == ChunkType.FIGURE])
            
            # Approximate word count
            section.word_count = sum(len(c.content.split()) for c in chunks)
    
    def _generate_summaries(self, sections: Dict[str, List[LDU]], section_by_id: Dict[str, SectionNode]):
        """Generate summaries for each section"""
        
        for section_id, chunks in sections.items():
            if section_id not in section_by_id:
                continue
            
            section = section_by_id[section_id]
            
            # Combine text for summary
            all_text = " ".join([c.content for c in chunks if c.chunk_type != ChunkType.TABLE])
            
            if len(all_text) < 50:
                section.summary = all_text
                section.summary_confidence = 1.0
                continue
            
            if self.use_llm and len(all_text) < 2000:
                # Use LLM for summary
                summary = self._generate_summary_with_llm(all_text, section.title)
                if summary:
                    section.summary = summary
                    section.summary_confidence = 0.9
            else:
                # Rule-based summary (first few sentences)
                summary = self._generate_summary_rule_based(all_text)
                section.summary = summary
                section.summary_confidence = 0.6
    
    def _generate_summary_with_llm(self, text: str, title: str) -> Optional[str]:
        """Generate summary using LLM"""
        try:
            prompt = f"""
            Summarize this section in 2-3 sentences.
            Section title: {title}
            
            Text: {text[:1500]}...
            
            Summary:
            """
            
            response = self.llm.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except:
            pass
        return None
    
    def _generate_summary_rule_based(self, text: str, max_sentences: int = 3) -> str:
        """Generate simple summary by taking first few sentences"""
        sentences = re.split(r'[.!?]+', text)
        summary = '. '.join(sentences[:max_sentences]).strip()
        if summary and not summary.endswith('.'):
            summary += '.'
        return summary
    
    def _collect_global_entities(self, section_by_id: Dict[str, SectionNode]) -> List[ExtractedEntity]:
        """Collect entities that appear across multiple sections"""
        entity_counts = {}
        entity_details = {}
        
        for section in section_by_id.values():
            for entity in section.entities:
                key = f"{entity.text}:{entity.entity_type}"
                if key not in entity_counts:
                    entity_counts[key] = 0
                    entity_details[key] = entity
                entity_counts[key] += 1
        
        # Return entities that appear in multiple sections
        global_entities = []
        for key, count in entity_counts.items():
            if count > 1:
                entity = entity_details[key]
                entity.mentions = list(range(1, count + 1))  # Simplified
                global_entities.append(entity)
        
        return global_entities[:10]  # Top 10 global entities
    
    def _calculate_max_depth(self, sections: List[SectionNode], current_depth: int = 1) -> int:
        """Calculate maximum nesting depth"""
        if not sections:
            return current_depth - 1
        
        max_depth = current_depth
        for section in sections:
            if section.child_sections:
                depth = self._calculate_max_depth(section.child_sections, current_depth + 1)
                max_depth = max(max_depth, depth)
        
        return max_depth
    
    def _get_total_pages(self, chunks: List[LDU]) -> int:
        """Get total number of pages in document"""
        all_pages = set()
        for chunk in chunks:
            if chunk.page_refs:
                all_pages.update(chunk.page_refs)
        return max(all_pages) if all_pages else 1
    
    def save_index(self, page_index: PageIndex, output_dir: Path):
        """
        Save PageIndex to JSON file
        FIXED: Handles datetime serialization properly
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = output_dir / f"{page_index.doc_id}_pageindex.json"
        
        # Convert to dict for JSON serialization
        try:
            # Use dict_for_json if available (handles datetime conversion)
            if hasattr(page_index, 'dict_for_json'):
                index_dict = page_index.dict_for_json()
            else:
                # Fallback to model_dump and handle datetime manually
                index_dict = page_index.model_dump()
                
                # Convert datetime fields to strings
                if 'created_at' in index_dict and index_dict['created_at']:
                    if hasattr(index_dict['created_at'], 'isoformat'):
                        index_dict['created_at'] = index_dict['created_at'].isoformat()
                
                # Handle any nested datetime objects in sections
                if 'root_sections' in index_dict:
                    self._convert_datetime_in_sections(index_dict['root_sections'])
                if 'section_by_id' in index_dict:
                    for section in index_dict['section_by_id'].values():
                        self._convert_datetime_in_sections([section])
            
            # Save with default=str as ultimate fallback
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(index_dict, f, indent=2, default=str)
            
            print(f"💾 PageIndex saved to: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"⚠️ Error saving with primary method: {e}")
            
            # Ultimate fallback - minimal save
            try:
                minimal_dict = {
                    "doc_id": page_index.doc_id,
                    "filename": page_index.filename,
                    "total_pages": page_index.total_pages,
                    "total_sections": page_index.total_sections,
                    "created_at": datetime.now().isoformat(),
                    "note": "Full serialization failed, saved minimal version"
                }
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(minimal_dict, f, indent=2)
                
                print(f"⚠️ Saved minimal PageIndex to: {filepath}")
                return filepath
            except:
                print(f"❌ Failed to save PageIndex")
                return None
    
    def _convert_datetime_in_sections(self, sections: List):
        """Helper to convert datetime fields in sections"""
        for section in sections:
            if isinstance(section, dict):
                # Check for datetime fields
                if 'created_at' in section and section['created_at']:
                    if hasattr(section['created_at'], 'isoformat'):
                        section['created_at'] = section['created_at'].isoformat()
                
                # Recursively process child sections
                if 'child_sections' in section and section['child_sections']:
                    self._convert_datetime_in_sections(section['child_sections'])
    
    def print_tree(self, page_index: PageIndex):
        """Print the tree structure"""
        print("\n🌳 PageIndex Tree Structure:")
        print("=" * 60)
        page_index.print_tree()
        print("=" * 60)

        def find_relevant_sections(self, query: str, page_index: PageIndex, top_k: int = 3) -> List[Dict]:
    """
    Find most relevant sections for a query
    
    Args:
        query: User query or topic
        page_index: PageIndex object
        top_k: Number of sections to return
    
    Returns:
        List of relevant sections with relevance scores
    """
    print(f"  🔍 Finding relevant sections for: '{query}'")
    
    query_lower = query.lower()
    scored_sections = []
    
    # Score each section
    for section_id, section in page_index.section_by_id.items():
        score = 0.0
        
        # Check title match
        if query_lower in section.title.lower():
            score += 0.4
        
        # Check summary match
        if section.summary and query_lower in section.summary.lower():
            score += 0.3
        
        # Check entity match
        for entity in section.key_entities:
            if query_lower in entity.lower():
                score += 0.2
                break
        
        # Check data types match
        if 'table' in query_lower and DataType.TABLE in section.data_types_present:
            score += 0.1
        if 'figure' in query_lower and DataType.FIGURE in section.data_types_present:
            score += 0.1
        
        if score > 0:
            scored_sections.append({
                'section_id': section_id,
                'title': section.title,
                'page_start': section.page_start,
                'page_end': section.page_end,
                'summary': section.summary,
                'data_types': [dt.value for dt in section.data_types_present],
                'key_entities': section.key_entities,
                'relevance_score': score,
                'path': section.path
            })
    
  