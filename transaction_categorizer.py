"""
Transaction Categorizer for HCSTC Loan Scoring.
Categorizes UK consumer banking transactions for affordability assessment.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

from config.categorization_patterns import (
    INCOME_PATTERNS,
    TRANSFER_PATTERNS,
    DEBT_PATTERNS,
    ESSENTIAL_PATTERNS,
    RISK_PATTERNS,
    POSITIVE_PATTERNS,
)


@dataclass
class CategoryMatch:
    """Result of transaction categorization."""
    category: str
    subcategory: str
    confidence: float
    description: str
    match_method: str  # 'keyword', 'regex', 'fuzzy', 'plaid'
    risk_level: Optional[str] = None
    weight: float = 1.0
    is_stable: bool = False
    is_housing: bool = False


class TransactionCategorizer:
    """Categorizes transactions for HCSTC loan scoring."""
    
    # Minimum confidence threshold for fuzzy matching
    FUZZY_THRESHOLD = 80
    
    def __init__(self):
        """Initialize the categorizer with pattern dictionaries."""
        self.income_patterns = INCOME_PATTERNS
        self.transfer_patterns = TRANSFER_PATTERNS
        self.debt_patterns = DEBT_PATTERNS
        self.essential_patterns = ESSENTIAL_PATTERNS
        self.risk_patterns = RISK_PATTERNS
        self.positive_patterns = POSITIVE_PATTERNS
    
    def categorize_transaction(
        self, 
        description: str, 
        amount: float,
        merchant_name: Optional[str] = None,
        plaid_category: Optional[str] = None
    ) -> CategoryMatch:
        """
        Categorize a single transaction.
        
        Args:
            description: Transaction description/name
            amount: Transaction amount (negative = credit, positive = debit)
            merchant_name: Optional merchant name from PLAID
            plaid_category: Optional PLAID category (personal_finance_category.detailed)
        
        Returns:
            CategoryMatch with categorization result
        """
        # Normalize text for matching
        text = self._normalize_text(description)
        merchant_text = self._normalize_text(merchant_name) if merchant_name else ""
        combined_text = f"{text} {merchant_text}".strip()
        
        # Determine if income or expense based on amount
        is_credit = amount < 0  # Negative = money in
        
        if is_credit:
            return self._categorize_income(combined_text, text, plaid_category)
        else:
            return self._categorize_expense(combined_text, text, plaid_category)
    
    def _normalize_text(self, text: Optional[str]) -> str:
        """Normalize text for matching."""
        if not text:
            return ""
        # Convert to uppercase for matching
        return text.upper().strip()
    
    def _categorize_income(
        self, 
        combined_text: str, 
        description: str,
        plaid_category: Optional[str]
    ) -> CategoryMatch:
        """Categorize an income transaction (credit)."""
        
        # Check if it's a transfer (not real income)
        if self._is_transfer(combined_text):
            return CategoryMatch(
                category="transfer",
                subcategory="internal",
                confidence=0.9,
                description="Internal Transfer",
                match_method="keyword",
                weight=0.0,  # Not counted as income
                is_stable=False
            )
        
        # Check income patterns
        for subcategory, patterns in self.income_patterns.items():
            match = self._match_patterns(combined_text, patterns)
            if match:
                return CategoryMatch(
                    category="income",
                    subcategory=subcategory,
                    confidence=match[1],
                    description=patterns.get("description", subcategory),
                    match_method=match[0],
                    weight=patterns.get("weight", 1.0),
                    is_stable=patterns.get("is_stable", False)
                )
        
        # Use PLAID category as fallback
        if plaid_category:
            plaid_match = self._match_plaid_category(plaid_category, is_income=True)
            if plaid_match:
                return plaid_match
        
        # Unknown income
        return CategoryMatch(
            category="income",
            subcategory="other",
            confidence=0.5,
            description="Other Income",
            match_method="default",
            weight=0.5,  # Partial weight for unidentified income
            is_stable=False
        )
    
    def _categorize_expense(
        self, 
        combined_text: str, 
        description: str,
        plaid_category: Optional[str]
    ) -> CategoryMatch:
        """Categorize an expense transaction (debit)."""
        
        # Check risk patterns first (highest priority)
        for subcategory, patterns in self.risk_patterns.items():
            match = self._match_patterns(combined_text, patterns)
            if match:
                return CategoryMatch(
                    category="risk",
                    subcategory=subcategory,
                    confidence=match[1],
                    description=patterns.get("description", subcategory),
                    match_method=match[0],
                    risk_level=patterns.get("risk_level", "medium")
                )
        
        # Check debt patterns
        for subcategory, patterns in self.debt_patterns.items():
            match = self._match_patterns(combined_text, patterns)
            if match:
                return CategoryMatch(
                    category="debt",
                    subcategory=subcategory,
                    confidence=match[1],
                    description=patterns.get("description", subcategory),
                    match_method=match[0],
                    risk_level=patterns.get("risk_level", "medium")
                )
        
        # Check essential patterns
        for subcategory, patterns in self.essential_patterns.items():
            match = self._match_patterns(combined_text, patterns)
            if match:
                return CategoryMatch(
                    category="essential",
                    subcategory=subcategory,
                    confidence=match[1],
                    description=patterns.get("description", subcategory),
                    match_method=match[0],
                    is_housing=patterns.get("is_housing", False)
                )
        
        # Check positive patterns
        for subcategory, patterns in self.positive_patterns.items():
            match = self._match_patterns(combined_text, patterns)
            if match:
                return CategoryMatch(
                    category="positive",
                    subcategory=subcategory,
                    confidence=match[1],
                    description=patterns.get("description", subcategory),
                    match_method=match[0]
                )
        
        # Use PLAID category as fallback
        if plaid_category:
            plaid_match = self._match_plaid_category(plaid_category, is_income=False)
            if plaid_match:
                return plaid_match
        
        # Unknown expense
        return CategoryMatch(
            category="expense",
            subcategory="other",
            confidence=0.3,
            description="Other Expense",
            match_method="default"
        )
    
    def _is_transfer(self, text: str) -> bool:
        """Check if transaction is an internal transfer."""
        patterns = self.transfer_patterns
        
        # Check keywords
        for keyword in patterns.get("keywords", []):
            if keyword.upper() in text:
                return True
        
        # Check regex patterns
        for pattern in patterns.get("regex_patterns", []):
            if re.search(pattern, text):
                return True
        
        return False
    
    def _match_patterns(
        self, 
        text: str, 
        patterns: Dict
    ) -> Optional[Tuple[str, float]]:
        """
        Match text against pattern dictionary.
        
        Returns:
            Tuple of (match_method, confidence) or None if no match
        """
        # Check keyword matches first (fastest)
        for keyword in patterns.get("keywords", []):
            if keyword.upper() in text:
                return ("keyword", 0.95)
        
        # Check regex patterns
        for pattern in patterns.get("regex_patterns", []):
            if re.search(pattern, text, re.IGNORECASE):
                return ("regex", 0.90)
        
        # Try fuzzy matching if available
        if RAPIDFUZZ_AVAILABLE:
            for keyword in patterns.get("keywords", []):
                # Use token_set_ratio for better matching with extra words
                score = fuzz.token_set_ratio(keyword.upper(), text)
                if score >= self.FUZZY_THRESHOLD:
                    return ("fuzzy", score / 100.0)
        
        return None
    
    def _match_plaid_category(
        self, 
        plaid_category: str, 
        is_income: bool
    ) -> Optional[CategoryMatch]:
        """Map PLAID category to our categories."""
        if not plaid_category:
            return None
        
        plaid_upper = plaid_category.upper()
        
        # Income categories
        if is_income:
            if "SALARY" in plaid_upper or "PAYROLL" in plaid_upper:
                return CategoryMatch(
                    category="income",
                    subcategory="salary",
                    confidence=0.85,
                    description="Salary & Wages",
                    match_method="plaid",
                    weight=1.0,
                    is_stable=True
                )
            if "GOVERNMENT" in plaid_upper or "BENEFIT" in plaid_upper:
                return CategoryMatch(
                    category="income",
                    subcategory="benefits",
                    confidence=0.85,
                    description="Benefits & Government",
                    match_method="plaid",
                    weight=1.0,
                    is_stable=True
                )
            if "PENSION" in plaid_upper or "RETIREMENT" in plaid_upper:
                return CategoryMatch(
                    category="income",
                    subcategory="pension",
                    confidence=0.85,
                    description="Pension Income",
                    match_method="plaid",
                    weight=1.0,
                    is_stable=True
                )
        
        # Expense categories
        else:
            if "RENT" in plaid_upper:
                return CategoryMatch(
                    category="essential",
                    subcategory="rent",
                    confidence=0.85,
                    description="Rent",
                    match_method="plaid",
                    is_housing=True
                )
            if "MORTGAGE" in plaid_upper:
                return CategoryMatch(
                    category="essential",
                    subcategory="mortgage",
                    confidence=0.85,
                    description="Mortgage",
                    match_method="plaid",
                    is_housing=True
                )
            if "UTILITY" in plaid_upper or "UTILITIES" in plaid_upper:
                return CategoryMatch(
                    category="essential",
                    subcategory="utilities",
                    confidence=0.85,
                    description="Utilities",
                    match_method="plaid"
                )
            if "GROCERY" in plaid_upper or "GROCERIES" in plaid_upper:
                return CategoryMatch(
                    category="essential",
                    subcategory="groceries",
                    confidence=0.85,
                    description="Groceries",
                    match_method="plaid"
                )
            if "GAMBLING" in plaid_upper or "CASINO" in plaid_upper:
                return CategoryMatch(
                    category="risk",
                    subcategory="gambling",
                    confidence=0.85,
                    description="Gambling",
                    match_method="plaid",
                    risk_level="critical"
                )
            if "LOAN" in plaid_upper:
                return CategoryMatch(
                    category="debt",
                    subcategory="other_loans",
                    confidence=0.80,
                    description="Loan Payment",
                    match_method="plaid",
                    risk_level="medium"
                )
        
        return None
    
    def categorize_transactions(
        self, 
        transactions: List[Dict]
    ) -> List[Tuple[Dict, CategoryMatch]]:
        """
        Categorize a list of transactions.
        
        Args:
            transactions: List of transaction dictionaries
        
        Returns:
            List of tuples (transaction, category_match)
        """
        results = []
        
        for txn in transactions:
            description = txn.get("name", "")
            amount = txn.get("amount", 0)
            merchant_name = txn.get("merchant_name")
            plaid_category = txn.get("personal_finance_category.detailed")
            
            # Handle nested PLAID category if present
            if not plaid_category and "personal_finance_category" in txn:
                pfc = txn.get("personal_finance_category", {})
                if isinstance(pfc, dict):
                    plaid_category = pfc.get("detailed")
            
            category_match = self.categorize_transaction(
                description=description,
                amount=amount,
                merchant_name=merchant_name,
                plaid_category=plaid_category
            )
            
            results.append((txn, category_match))
        
        return results
    
    def get_category_summary(
        self, 
        categorized_transactions: List[Tuple[Dict, CategoryMatch]]
    ) -> Dict:
        """
        Generate a summary of categorized transactions.
        
        Returns:
            Dictionary with category totals and counts
        """
        summary = {
            "income": {
                "salary": {"total": 0.0, "count": 0},
                "benefits": {"total": 0.0, "count": 0},
                "pension": {"total": 0.0, "count": 0},
                "gig_economy": {"total": 0.0, "count": 0},
                "other": {"total": 0.0, "count": 0},
            },
            "debt": {
                "hcstc_payday": {"total": 0.0, "count": 0, "lenders": set()},
                "other_loans": {"total": 0.0, "count": 0},
                "credit_cards": {"total": 0.0, "count": 0},
                "bnpl": {"total": 0.0, "count": 0},
                "catalogue": {"total": 0.0, "count": 0},
            },
            "essential": {
                "rent": {"total": 0.0, "count": 0},
                "mortgage": {"total": 0.0, "count": 0},
                "council_tax": {"total": 0.0, "count": 0},
                "utilities": {"total": 0.0, "count": 0},
                "communications": {"total": 0.0, "count": 0},
                "insurance": {"total": 0.0, "count": 0},
                "transport": {"total": 0.0, "count": 0},
                "groceries": {"total": 0.0, "count": 0},
                "childcare": {"total": 0.0, "count": 0},
            },
            "risk": {
                "gambling": {"total": 0.0, "count": 0},
                "failed_payments": {"total": 0.0, "count": 0},
                "debt_collection": {"total": 0.0, "count": 0, "dcas": set()},
            },
            "positive": {
                "savings": {"total": 0.0, "count": 0},
            },
            "transfer": {"total": 0.0, "count": 0},
            "other": {"total": 0.0, "count": 0},
        }
        
        for txn, match in categorized_transactions:
            amount = abs(txn.get("amount", 0))
            category = match.category
            subcategory = match.subcategory
            
            if category in summary and subcategory in summary.get(category, {}):
                summary[category][subcategory]["total"] += amount
                summary[category][subcategory]["count"] += 1
                
                # Track distinct HCSTC lenders
                if category == "debt" and subcategory == "hcstc_payday":
                    merchant = txn.get("merchant_name") or txn.get("name", "")
                    summary[category][subcategory]["lenders"].add(
                        merchant.upper()[:20]  # First 20 chars for deduplication
                    )
                
                # Track distinct DCAs
                if category == "risk" and subcategory == "debt_collection":
                    merchant = txn.get("merchant_name") or txn.get("name", "")
                    summary[category][subcategory]["dcas"].add(
                        merchant.upper()[:20]
                    )
            
            elif category == "transfer":
                summary["transfer"]["total"] += amount
                summary["transfer"]["count"] += 1
            else:
                summary["other"]["total"] += amount
                summary["other"]["count"] += 1
        
        # Convert sets to counts
        if "lenders" in summary["debt"]["hcstc_payday"]:
            summary["debt"]["hcstc_payday"]["distinct_lenders"] = len(
                summary["debt"]["hcstc_payday"]["lenders"]
            )
            del summary["debt"]["hcstc_payday"]["lenders"]
        
        if "dcas" in summary["risk"]["debt_collection"]:
            summary["risk"]["debt_collection"]["distinct_dcas"] = len(
                summary["risk"]["debt_collection"]["dcas"]
            )
            del summary["risk"]["debt_collection"]["dcas"]
        
        return summary
