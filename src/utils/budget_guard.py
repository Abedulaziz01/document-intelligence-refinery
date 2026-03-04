"""
Budget Guard
Tracks and enforces budget limits for paid strategies
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, Optional


class BudgetGuard:
    """
    Tracks spending on paid extraction strategies
    Prevents cost overruns
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize budget guard with configuration
        
        config:
            max_cost_per_document: Maximum per document
            daily_budget: Maximum per day
            monthly_budget: Maximum per month
        """
        self.config = config or {}
        self.max_per_document = self.config.get('max_cost_per_document', 0.50)  # $0.50 default
        self.daily_budget = self.config.get('daily_budget', 5.00)  # $5 default
        self.monthly_budget = self.config.get('monthly_budget', 20.00)  # $20 default
        
        # Track spending
        self.spending_file = Path(".refinery/spending.json")
        self.spending = self._load_spending()
    
    def _load_spending(self) -> Dict[str, Any]:
        """Load spending history from file"""
        if self.spending_file.exists():
            try:
                with open(self.spending_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default spending structure
        return {
            'documents': {},  # doc_id -> total cost
            'daily': {},      # date -> total cost
            'monthly': {},    # YYYY-MM -> total cost
            'total': 0.0
        }
    
    def _save_spending(self):
        """Save spending to file"""
        self.spending_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.spending_file, 'w') as f:
            json.dump(self.spending, f, indent=2)
    
    def check_budget(self, doc_id: str, estimated_cost: float) -> bool:
        """
        Check if processing a document would exceed any budget
        
        Returns:
            True if within budget, False if would exceed
        """
        today = date.today().isoformat()
        month = date.today().strftime('%Y-%m')
        
        # Check per-document budget
        doc_total = self.spending['documents'].get(doc_id, 0.0)
        if doc_total + estimated_cost > self.max_per_document:
            print(f"⚠️ Per-document budget exceeded: ${self.max_per_document}")
            return False
        
        # Check daily budget
        daily_total = self.spending['daily'].get(today, 0.0)
        if daily_total + estimated_cost > self.daily_budget:
            print(f"⚠️ Daily budget exceeded: ${self.daily_budget}")
            return False
        
        # Check monthly budget
        monthly_total = self.spending['monthly'].get(month, 0.0)
        if monthly_total + estimated_cost > self.monthly_budget:
            print(f"⚠️ Monthly budget exceeded: ${self.monthly_budget}")
            return False
        
        return True
    
    def add_cost(self, doc_id: str, cost: float):
        """
        Add cost to spending records
        """
        today = date.today().isoformat()
        month = date.today().strftime('%Y-%m')
        
        # Update document spending
        self.spending['documents'][doc_id] = self.spending['documents'].get(doc_id, 0.0) + cost
        
        # Update daily spending
        self.spending['daily'][today] = self.spending['daily'].get(today, 0.0) + cost
        
        # Update monthly spending
        self.spending['monthly'][month] = self.spending['monthly'].get(month, 0.0) + cost
        
        # Update total
        self.spending['total'] += cost
        
        # Save
        self._save_spending()
    
    def get_document_cost(self, doc_id: str) -> float:
        """Get total cost for a document"""
        return self.spending['documents'].get(doc_id, 0.0)
    
    def get_daily_cost(self, date_str: Optional[str] = None) -> float:
        """Get cost for a specific date"""
        if date_str is None:
            date_str = date.today().isoformat()
        return self.spending['daily'].get(date_str, 0.0)
    
    def get_total_cost(self) -> float:
        """Get total cost across all documents"""
        return self.spending['total']