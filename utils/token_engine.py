"""
Token-based Tendering System Engine
Core functionality for managing tokens in government procurement
Author: Tebello
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

class TokenEngine:
    """
    Core engine for managing token-based tendering system
    """
    
    def __init__(self, transactions_file: str = "data/transactions.json"):
        self.transactions_file = transactions_file
        self.transactions = self._load_transactions()
        
    def _load_transactions(self) -> List[Dict]:
        """Load existing transactions from JSON file"""
        try:
            with open(self.transactions_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def _save_transactions(self):
        """Save transactions to JSON file"""
        with open(self.transactions_file, 'w') as f:
            json.dump(self.transactions, f, indent=2, default=str)
    
    def issue_tokens(self, tender_id: str, contractor_id: str, 
                    total_value: float, project_scope: List[str]) -> Dict:
        """
        Issue tokens to a contractor for a specific tender
        
        Args:
            tender_id: Unique identifier for the tender
            contractor_id: Contractor receiving tokens
            total_value: Total rand value of the project
            project_scope: List of allowed spending categories
            
        Returns:
            Dictionary containing token issuance details
        """
        token_id = str(uuid.uuid4())
        issuance = {
            "transaction_id": token_id,
            "type": "TOKEN_ISSUANCE",
            "tender_id": tender_id,
            "contractor_id": contractor_id,
            "tokens_issued": total_value,
            "tokens_remaining": total_value,
            "project_scope": project_scope,
            "timestamp": datetime.now().isoformat(),
            "status": "ACTIVE"
        }
        
        self.transactions.append(issuance)
        self._save_transactions()
        
        return issuance
    
    def spend_tokens(self, tender_id: str, contractor_id: str, 
                    amount: float, category: str, milestone: str,
                    description: str) -> Dict:
        """
        Record token spending for a specific milestone
        
        Args:
            tender_id: Tender ID
            contractor_id: Contractor spending tokens
            amount: Amount of tokens to spend
            category: Spending category (must be in project scope)
            milestone: Milestone being worked on
            description: Description of expenditure
            
        Returns:
            Dictionary containing spending transaction details
        """
        # Find the token issuance record
        issuance = self._find_active_issuance(tender_id, contractor_id)
        if not issuance:
            raise ValueError(f"No active token issuance found for tender {tender_id}")
        
        # Check if category is allowed
        if category not in issuance["project_scope"]:
            raise ValueError(f"Category '{category}' not in project scope")
        
        # Check if sufficient tokens available
        if issuance["tokens_remaining"] < amount:
            raise ValueError(f"Insufficient tokens. Available: {issuance['tokens_remaining']}")
        
        # Create spending transaction
        spending = {
            "transaction_id": str(uuid.uuid4()),
            "type": "TOKEN_SPENDING",
            "tender_id": tender_id,
            "contractor_id": contractor_id,
            "amount": amount,
            "category": category,
            "milestone": milestone,
            "description": description,
            "timestamp": datetime.now().isoformat()
        }
        
        # Update remaining tokens
        issuance["tokens_remaining"] -= amount
        
        self.transactions.append(spending)
        self._save_transactions()
        
        return spending
    
    def verify_milestone(self, tender_id: str, milestone: str, 
                        quality_score: float) -> Dict:
        """
        Verify and score a milestone completion
        
        Args:
            tender_id: Tender ID
            milestone: Milestone name
            quality_score: Score out of 100
            
        Returns:
            Dictionary containing verification details
        """
        verification = {
            "transaction_id": str(uuid.uuid4()),
            "type": "MILESTONE_VERIFICATION",
            "tender_id": tender_id,
            "milestone": milestone,
            "quality_score": quality_score,
            "passed": quality_score >= 80,
            "timestamp": datetime.now().isoformat()
        }
        
        self.transactions.append(verification)
        self._save_transactions()
        
        return verification
    
    def redeem_tokens(self, tender_id: str, contractor_id: str) -> Dict:
        """
        Redeem unused tokens if all milestones passed
        
        Args:
            tender_id: Tender ID
            contractor_id: Contractor redeeming tokens
            
        Returns:
            Dictionary containing redemption details
        """
        issuance = self._find_active_issuance(tender_id, contractor_id)
        if not issuance:
            raise ValueError(f"No active token issuance found for tender {tender_id}")
        
        # Check if all milestones passed
        milestones = self._get_milestone_verifications(tender_id)
        if not milestones:
            raise ValueError("No milestones verified yet")
        
        all_passed = all(m["passed"] for m in milestones)
        avg_score = sum(m["quality_score"] for m in milestones) / len(milestones)
        
        if not all_passed:
            # Return tokens to treasury instead
            return self.return_tokens_to_treasury(tender_id, contractor_id)
        
        # Calculate bonus based on efficiency
        tokens_remaining = issuance["tokens_remaining"]
        bonus_multiplier = min(1.2, 1 + (avg_score - 80) / 100)  # Max 20% bonus
        cash_value = tokens_remaining * bonus_multiplier
        
        redemption = {
            "transaction_id": str(uuid.uuid4()),
            "type": "TOKEN_REDEMPTION",
            "tender_id": tender_id,
            "contractor_id": contractor_id,
            "tokens_redeemed": tokens_remaining,
            "cash_value": cash_value,
            "bonus_multiplier": bonus_multiplier,
            "average_quality_score": avg_score,
            "timestamp": datetime.now().isoformat()
        }
        
        # Mark issuance as completed
        issuance["status"] = "REDEEMED"
        issuance["tokens_remaining"] = 0
        
        self.transactions.append(redemption)
        self._save_transactions()
        
        return redemption
    
    def return_tokens_to_treasury(self, tender_id: str, contractor_id: str) -> Dict:
        """
        Return unused tokens to treasury (penalty for poor performance)
        
        Args:
            tender_id: Tender ID
            contractor_id: Contractor
            
        Returns:
            Dictionary containing return details
        """
        issuance = self._find_active_issuance(tender_id, contractor_id)
        if not issuance:
            raise ValueError(f"No active token issuance found for tender {tender_id}")
        
        tokens_returned = issuance["tokens_remaining"]
        
        return_transaction = {
            "transaction_id": str(uuid.uuid4()),
            "type": "TOKENS_RETURNED",
            "tender_id": tender_id,
            "contractor_id": contractor_id,
            "tokens_returned": tokens_returned,
            "reason": "Quality standards not met",
            "timestamp": datetime.now().isoformat()
        }
        
        # Mark issuance as completed
        issuance["status"] = "RETURNED"
        issuance["tokens_remaining"] = 0
        
        self.transactions.append(return_transaction)
        self._save_transactions()
        
        return return_transaction
    
    def _find_active_issuance(self, tender_id: str, contractor_id: str) -> Optional[Dict]:
        """Find active token issuance for a tender"""
        for transaction in self.transactions:
            if (transaction["type"] == "TOKEN_ISSUANCE" and 
                transaction["tender_id"] == tender_id and
                transaction["contractor_id"] == contractor_id and
                transaction["status"] == "ACTIVE"):
                return transaction
        return None
    
    def _get_milestone_verifications(self, tender_id: str) -> List[Dict]:
        """Get all milestone verifications for a tender"""
        return [t for t in self.transactions 
                if t["type"] == "MILESTONE_VERIFICATION" and t["tender_id"] == tender_id]
    
    def get_tender_summary(self, tender_id: str) -> Dict:
        """Get complete summary of a tender's token transactions"""
        tender_transactions = [t for t in self.transactions if t.get("tender_id") == tender_id]
        
        issuance = next((t for t in tender_transactions if t["type"] == "TOKEN_ISSUANCE"), None)
        if not issuance:
            return {"error": "Tender not found"}
        
        spendings = [t for t in tender_transactions if t["type"] == "TOKEN_SPENDING"]
        verifications = [t for t in tender_transactions if t["type"] == "MILESTONE_VERIFICATION"]
        redemption = next((t for t in tender_transactions if t["type"] in ["TOKEN_REDEMPTION", "TOKENS_RETURNED"]), None)
        
        total_spent = sum(s["amount"] for s in spendings)
        
        return {
            "tender_id": tender_id,
            "contractor_id": issuance["contractor_id"],
            "total_tokens_issued": issuance["tokens_issued"],
            "total_tokens_spent": total_spent,
            "tokens_remaining": issuance["tokens_remaining"],
            "status": issuance["status"],
            "milestones_completed": len(verifications),
            "average_quality_score": sum(v["quality_score"] for v in verifications) / len(verifications) if verifications else 0,
            "final_outcome": redemption["type"] if redemption else "IN_PROGRESS",
            "transactions": tender_transactions
        }
    
    def get_spending_by_category(self, tender_id: str) -> Dict[str, float]:
        """Get spending breakdown by category for a tender"""
        spendings = [t for t in self.transactions 
                    if t["type"] == "TOKEN_SPENDING" and t["tender_id"] == tender_id]
        
        category_totals = {}
        for spending in spendings:
            category = spending["category"]
            category_totals[category] = category_totals.get(category, 0) + spending["amount"]
        
        return category_totals