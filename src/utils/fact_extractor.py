"""
Fact Table Extractor
Extracts key-value facts from financial/numerical documents
Stores in SQLite for precise querying
"""

import sqlite3
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path


class FactExtractor:
    """
    Extracts structured facts from document chunks
    Stores in SQLite database for precise querying
    """
    
    def __init__(self, db_path: str = ".refinery/facts.db"):
        """
        Initialize fact extractor
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create facts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                fact_type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                numeric_value REAL,
                unit TEXT,
                page INTEGER,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_doc ON facts(doc_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_numeric ON facts(numeric_value) WHERE numeric_value IS NOT NULL')
        
        conn.commit()
        conn.close()
        
        print(f"✅ Fact database initialized at {self.db_path}")
    
    def extract_facts_from_chunks(self, chunks: List, doc_id: str) -> List[Dict]:
        """
        Extract facts from document chunks
        
        Args:
            chunks: List of LDU objects
            doc_id: Document identifier
            
        Returns:
            List of extracted facts
        """
        all_facts = []
        
        for chunk in chunks:
            # Extract based on chunk type
            if chunk.chunk_type == "table":
                facts = self._extract_from_table(chunk, doc_id)
            else:
                facts = self._extract_from_text(chunk, doc_id)
            
            all_facts.extend(facts)
        
        # Store in database
        if all_facts:
            self._store_facts(all_facts)
        
        print(f"📊 Extracted {len(all_facts)} facts from document")
        return all_facts
    
    def _extract_from_text(self, chunk, doc_id: str) -> List[Dict]:
        """Extract facts from text chunk"""
        facts = []
        content = chunk.content
        page = chunk.page_refs[0] if chunk.page_refs else 1
        
        # Pattern 1: Revenue/Profit/Income: $X
        patterns = [
            (r'revenue(?: was| of)?\s*\$?([\d,]+(?:\.\d+)?)\s*(million|billion|M|B)?', 'revenue'),
            (r'profit(?: was| of)?\s*\$?([\d,]+(?:\.\d+)?)\s*(million|billion|M|B)?', 'profit'),
            (r'income(?: was| of)?\s*\$?([\d,]+(?:\.\d+)?)\s*(million|billion|M|B)?', 'income'),
            (r'total assets?\s*\$?([\d,]+(?:\.\d+)?)\s*(million|billion|M|B)?', 'assets'),
            (r'liabilities?\s*\$?([\d,]+(?:\.\d+)?)\s*(million|billion|M|B)?', 'liabilities'),
            (r'equity\s*\$?([\d,]+(?:\.\d+)?)\s*(million|billion|M|B)?', 'equity'),
            (r'growth\s*([\d,]+(?:\.\d+)?)\s*%', 'growth_percentage'),
            (r'increased by\s*([\d,]+(?:\.\d+)?)\s*%', 'increase_percentage'),
        ]
        
        for pattern, fact_key in patterns:
            matches = re.finditer(pattern, content.lower())
            for match in matches:
                value = match.group(1).replace(',', '')
                unit = match.group(2) if len(match.groups()) > 1 else None
                
                # Convert to numeric
                try:
                    numeric_value = float(value)
                    
                    # Adjust for million/billion
                    if unit:
                        if unit.lower() in ['million', 'm']:
                            numeric_value *= 1_000_000
                        elif unit.lower() in ['billion', 'b']:
                            numeric_value *= 1_000_000_000
                    
                    fact = {
                        'doc_id': doc_id,
                        'chunk_id': chunk.ldu_id,
                        'fact_type': 'financial',
                        'key': fact_key,
                        'value': match.group(0),
                        'numeric_value': numeric_value,
                        'unit': unit,
                        'page': page,
                        'confidence': 0.8
                    }
                    facts.append(fact)
                except:
                    pass
        
        # Pattern 2: Year/Date facts
        date_pattern = r'(?:fiscal year|FY|year ended|as of)\s*(\d{4})'
        date_matches = re.finditer(date_pattern, content.lower())
        for match in date_matches:
            fact = {
                'doc_id': doc_id,
                'chunk_id': chunk.ldu_id,
                'fact_type': 'metadata',
                'key': 'fiscal_year',
                'value': match.group(1),
                'numeric_value': float(match.group(1)),
                'unit': 'year',
                'page': page,
                'confidence': 0.9
            }
            facts.append(fact)
        
        return facts
    
    def _extract_from_table(self, chunk, doc_id: str) -> List[Dict]:
        """Extract facts from table chunk"""
        facts = []
        page = chunk.page_refs[0] if chunk.page_refs else 1
        
        # For tables, we look for specific patterns
        content = chunk.content
        
        # Look for rows with years and values
        lines = content.split('\n')
        for line in lines:
            # Pattern: Year | Value
            if '|' in line and any(year in line for year in ['2020','2021','2022','2023','2024']):
                parts = [p.strip() for p in line.split('|') if p.strip()]
                
                # Try to find year and number
                year = None
                value = None
                
                for part in parts:
                    if re.match(r'20\d{2}', part):
                        year = part
                    elif re.search(r'[\d,]+(?:\.\d+)?', part):
                        value = part
                
                if year and value:
                    # Extract number
                    num_match = re.search(r'([\d,]+(?:\.\d+)?)', value)
                    if num_match:
                        numeric_value = float(num_match.group(1).replace(',', ''))
                        
                        fact = {
                            'doc_id': doc_id,
                            'chunk_id': chunk.ldu_id,
                            'fact_type': 'financial',
                            'key': 'table_value',
                            'value': f"{year}: {value}",
                            'numeric_value': numeric_value,
                            'unit': 'usd',
                            'page': page,
                            'confidence': 0.7
                        }
                        facts.append(fact)
        
        return facts
    
    def _store_facts(self, facts: List[Dict]):
        """Store facts in SQLite database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        for fact in facts:
            cursor.execute('''
                INSERT INTO facts 
                (doc_id, chunk_id, fact_type, key, value, numeric_value, unit, page, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fact['doc_id'],
                fact['chunk_id'],
                fact['fact_type'],
                fact['key'],
                fact['value'],
                fact.get('numeric_value'),
                fact.get('unit'),
                fact['page'],
                fact['confidence']
            ))
        
        conn.commit()
        conn.close()
    
    def query(self, sql: str) -> List[Dict]:
        """
        Execute SQL query on facts table
        
        Args:
            sql: SQL query string
            
        Returns:
            List of results as dictionaries
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            # Convert to dicts
            results = [dict(row) for row in rows]
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"❌ SQL Error: {e}")
            conn.close()
            return []
    
    def get_financial_summary(self, doc_id: Optional[str] = None) -> Dict:
        """Get summary of financial facts"""
        if doc_id:
            query = f"SELECT key, COUNT(*) as count, AVG(numeric_value) as avg_value FROM facts WHERE doc_id = '{doc_id}' AND numeric_value IS NOT NULL GROUP BY key"
        else:
            query = "SELECT key, COUNT(*) as count, AVG(numeric_value) as avg_value FROM facts WHERE numeric_value IS NOT NULL GROUP BY key"
        
        results = self.query(query)
        
        summary = {}
        for r in results:
            summary[r['key']] = {
                'count': r['count'],
                'average': r['avg_value']
            }
        
        return summary
    
    def search_facts(self, key: Optional[str] = None, 
                    min_value: Optional[float] = None,
                    max_value: Optional[float] = None,
                    year: Optional[int] = None) -> List[Dict]:
        """
        Search for facts with filters
        
        Args:
            key: Fact key (revenue, profit, etc.)
            min_value: Minimum numeric value
            max_value: Maximum numeric value
            year: Filter by year
        """
        conditions = []
        params = []
        
        if key:
            conditions.append("key = ?")
            params.append(key)
        
        if min_value is not None:
            conditions.append("numeric_value >= ?")
            params.append(min_value)
        
        if max_value is not None:
            conditions.append("numeric_value <= ?")
            params.append(max_value)
        
        if year:
            conditions.append("page = ? OR value LIKE ?")  # Simplified
            params.append(year)
            params.append(f"%{year}%")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"SELECT * FROM facts WHERE {where_clause} ORDER BY numeric_value DESC"
        
        return self.query(query)