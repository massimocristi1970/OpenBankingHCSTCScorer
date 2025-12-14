"""
Transaction Categorizer for HCSTC Loan Scoring.
Categorizes UK consumer banking transactions for affordability assessment.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

from ..patterns.transaction_patterns import (
    INCOME_PATTERNS,
    TRANSFER_PATTERNS,
    DEBT_PATTERNS,
    ESSENTIAL_PATTERNS,
    RISK_PATTERNS,
    POSITIVE_PATTERNS,
)

from ..income.income_detector import IncomeDetector


# HCSTC Lender Canonical Name Mappings
# Maps variations of lender names to a single canonical identifier
HCSTC_LENDER_CANONICAL_NAMES = {
    "LENDING STREAM": "LENDING_STREAM",
    "LENDINGSTREAM": "LENDING_STREAM",
    "DRAFTY": "DRAFTY",
    "MR LENDER": "MR_LENDER",
    "MRLENDER": "MR_LENDER",
    "MONEYBOAT": "MONEYBOAT",
    "CREDITSPRING": "CREDITSPRING",
    "CASHFLOAT": "CASHFLOAT",
    "QUIDMARKET": "QUIDMARKET",
    "QUID MARKET": "QUIDMARKET",
    "LOANS 2 GO": "LOANS_2_GO",
    "LOANS2GO": "LOANS_2_GO",
    "CASHASAP": "CASHASAP",
    "POLAR CREDIT": "POLAR_CREDIT",
    "118 118 MONEY": "118_118_MONEY",
    "118118 MONEY": "118_118_MONEY",
    "118118MONEY": "118_118_MONEY",
    "THE MONEY PLATFORM": "THE_MONEY_PLATFORM",
    "MONEY PLATFORM": "THE_MONEY_PLATFORM",
    "FAST LOAN UK": "FAST_LOAN_UK",
    "FASTLOAN": "FAST_LOAN_UK",
    "CONDUIT": "CONDUIT",
    "SALAD MONEY": "SALAD_MONEY",
    "FAIR FINANCE": "FAIR_FINANCE",
}

# Pre-computed sorted patterns (longest first) for efficient matching
# This avoids sorting on every call to _normalize_hcstc_lender
HCSTC_LENDER_PATTERNS_SORTED = sorted(
    HCSTC_LENDER_CANONICAL_NAMES.items(),
    key=lambda x: len(x[0]),
    reverse=True
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
    
    # Salary detection keywords (used to identify legitimate salary payments)
    SALARY_KEYWORDS = [
        "SALARY", "WAGES", "PAYROLL", "NET PAY", "WAGE", 
        "PAYSLIP", "EMPLOYER", "EMPLOYERS",
        "BGC", "BANK GIRO CREDIT", "CHEQUERS CONTRACT",
        "CONTRACT PAY", "MONTHLY PAY", "WEEKLY PAY"
    ]
    
    # Keywords that indicate internal transfers (not income)
    TRANSFER_EXCLUSION_KEYWORDS = ["OWN ACCOUNT", "INTERNAL", "SELF TRANSFER"]
    
    # Known expense services that should not be treated as income
    # These are payment processors, BNPL services, and lenders that might
    # have keywords like "PAY" or "PAYMENT" but are expenses, not income
    # Stored as set for O(1) lookup performance
    KNOWN_EXPENSE_SERVICES = {
        # Payment processors
        "PAYPAL", "STRIPE", "SQUARE", "WORLDPAY", "SAGEPAY",
        # BNPL services (already in debt patterns but listed for clarity)
        "CLEARPAY", "KLARNA", "ZILCH", "LAYBUY", "MONZO FLEX",
        # HCSTC Lenders (already in debt patterns but listed for clarity)
        "LENDING STREAM", "LENDINGSTREAM", "MONEYBOAT", "DRAFTY",
        "CASHFLOAT", "QUIDMARKET", "MR LENDER", "MRLENDER",
        # Additional loan providers
        "LENDABLE", "ZOPA", "TOTALSA", "AQUA", "HSBC LOANS",
        "VISA DIRECT PAYMENT", "BARCLAYS CASHBACK",
    }
    
    def __init__(self):
        """Initialize the categorizer with pattern dictionaries."""
        self.income_patterns = INCOME_PATTERNS
        self.transfer_patterns = TRANSFER_PATTERNS
        self.debt_patterns = DEBT_PATTERNS
        self.essential_patterns = ESSENTIAL_PATTERNS
        self.risk_patterns = RISK_PATTERNS
        self.positive_patterns = POSITIVE_PATTERNS
        self.income_detector = IncomeDetector()
    
    def categorize_transaction(
        self, 
        description: str, 
        amount: float,
        merchant_name: Optional[str] = None,
        plaid_category: Optional[str] = None,
        plaid_category_primary: Optional[str] = None
    ) -> CategoryMatch:
        """
        Categorize a single transaction.
        
        Args:
            description: Transaction description/name
            amount: Transaction amount (negative = credit, positive = debit)
            merchant_name: Optional merchant name from PLAID
            plaid_category: Optional PLAID category (personal_finance_category.detailed)
            plaid_category_primary: Optional PLAID primary category (personal_finance_category.primary)
        
        Returns:
            CategoryMatch with categorization result
        """
        # Normalize text for matching
        text = self._normalize_text(description)
        merchant_text = self._normalize_text(merchant_name) if merchant_name else ""
        combined_text = f"{text} {merchant_text}".strip()
        
        # Determine if income or expense based on PLAID amount convention.
        # In PLAID format: Negative amounts = credits (money IN to account),
        # Positive amounts = debits (money OUT of account).
        # This is the opposite of typical accounting where negative = outflow.
        is_credit = amount < 0
        
        if is_credit:
            return self._categorize_income(combined_text, text, amount, plaid_category, plaid_category_primary)
        else:
            return self._categorize_expense(combined_text, text, plaid_category)
    
    def _normalize_text(self, text: Optional[str]) -> str:
        """Normalize text for matching."""
        if not text:
            return ""
        # Convert to uppercase for matching
        return text.upper().strip()
    
    def _normalize_hcstc_lender(self, merchant_name: str) -> Optional[str]:
        """
        Normalize HCSTC lender name to canonical form.
        
        Args:
            merchant_name: Raw merchant/transaction name
            
        Returns:
            Canonical lender name if recognized, None otherwise
        """
        if not merchant_name:
            return None
            
        upper_name = merchant_name.upper()
        
        # Use pre-sorted patterns (longest first) to ensure most specific match
        # This prevents "LENDING" from matching "MR LENDER" before "LENDING STREAM"
        for pattern, canonical in HCSTC_LENDER_PATTERNS_SORTED:
            if pattern in upper_name:
                return canonical
        
        return None
    
            
    def _check_strict_plaid_categories(
        self,
        plaid_category_detailed: Optional[str]
    ) -> Optional[CategoryMatch]:
        """
        Check for strict PLAID detailed categories that must ALWAYS be respected.
        These categories override any keyword matching or behavioral detection.
        
        Args:
            plaid_category_detailed: The detailed PLAID category
            
        Returns:
            CategoryMatch if strict category found, None otherwise
        """
        if not plaid_category_detailed:
            return None
        
        detailed_upper = str(plaid_category_detailed).strip().upper()
        
        # TRANSFER_IN_ACCOUNT_TRANSFER -> transfer > internal (ALWAYS)
        if detailed_upper == "TRANSFER_IN_ACCOUNT_TRANSFER":
            return CategoryMatch(
                category="transfer",
                subcategory="internal",
                confidence=0.98,
                description="Internal Transfer",
                match_method="plaid_strict",
                weight=0.0,
                is_stable=False
            )
        
        # TRANSFER_OUT_ACCOUNT_TRANSFER -> transfer > external (ALWAYS)
        if detailed_upper == "TRANSFER_OUT_ACCOUNT_TRANSFER":
            return CategoryMatch(
                category="transfer",
                subcategory="external",
                confidence=0.98,
                description="External Transfer",
                match_method="plaid_strict",
                weight=0.0,
                is_stable=False
            )
        
        # TRANSFER_IN_CASH_ADVANCES_AND_LOANS -> income > loans (ALWAYS)
        if detailed_upper == "TRANSFER_IN_CASH_ADVANCES_AND_LOANS":
            return CategoryMatch(
                category="income",
                subcategory="loans",
                confidence=0.98,
                description="Loan Payments/Disbursements",
                match_method="plaid_strict",
                weight=0.0,
                is_stable=False
            )
        
        return None
    
    def _categorize_income(
        self, 
        combined_text: str, 
        description: str,
        amount: float,
        plaid_category: Optional[str],
        plaid_category_primary: Optional[str] = None
    ) -> CategoryMatch:
        """Categorize an income transaction (credit)."""
        
        # STEP 0A: Check strict PLAID categories FIRST (before any other logic)
        strict_match = self._check_strict_plaid_categories(plaid_category)
        if strict_match:
            return strict_match
        
        # STEP 0B: Check if this is a known expense service that should NEVER be income
        # This prevents false positives from keyword matching (e.g., "PAYPAL PAYMENT", "CLEARPAY")
        for service in self.KNOWN_EXPENSE_SERVICES:
            if service in combined_text:
                # This is a known expense service - check if it's actually a refund/credit
                # If PLAID says it's a transfer or loan, trust that
                if plaid_category_primary:
                    plaid_primary_upper = plaid_category_primary.upper()
                    if "TRANSFER" in plaid_primary_upper:
                        return CategoryMatch(
                            category="transfer",
                            subcategory="internal",
                            confidence=0.90,
                            description="Internal Transfer",
                            match_method="plaid",
                            weight=0.0,
                            is_stable=False
                        )
                    # CRITICAL: Check for LOAN_PAYMENTS to prevent loan disbursements from being income
                    if "LOAN_PAYMENTS" in plaid_primary_upper:
                        return CategoryMatch(
                            category="income",
                            subcategory="loans",
                            confidence=0.95,
                            description="Loan Payments/Disbursements",
                            match_method="plaid",
                            weight=0.0,
                            is_stable=False
                        )
                # Otherwise default to other income with low confidence
                # (could be a refund or reimbursement)
                return CategoryMatch(
                    category="income",
                    subcategory="other",
                    confidence=0.5,
                    description="Other Income",
                    match_method="known_service_exclusion",
                    weight=1.0,
                    is_stable=False
                )
        
        # STEP 1: Check PLAID categories for high-confidence loan/transfer indicators
        # BEFORE applying keyword-based income detection
        # This preserves PLAID's accurate categorization of loan payments and transfers
        if plaid_category or plaid_category_primary:
            plaid_cat_upper = (plaid_category or "").upper()
            plaid_primary_upper = (plaid_category_primary or "").upper()
            
            # Check for LOAN_PAYMENTS category - these are loan disbursements/refunds, NOT income
            # CRITICAL: This must be checked BEFORE keyword-based income detection to prevent
            # loan disbursements from being miscategorized as salary/income
            if "LOAN_PAYMENTS" in plaid_primary_upper or "LOAN_PAYMENTS" in plaid_cat_upper:
                return CategoryMatch(
                    category="income",
                    subcategory="loans",
                    confidence=0.95,
                    description="Loan Payments/Disbursements",
                    match_method="plaid",
                    weight=0.0,  # Not counted as income
                    is_stable=False
                )
            
            # Check for TRANSFER_IN with CASH_ADVANCES or LOANS
            # These are loan disbursements, should be categorized as income > loans with weight=0.0
            if "CASH_ADVANCES" in plaid_cat_upper or "ADVANCES" in plaid_cat_upper or "LOANS" in plaid_cat_upper:
                # This is likely a cash advance or loan disbursement
                return CategoryMatch(
                    category="income",
                    subcategory="loans",
                    confidence=0.95,
                    description="Loan Payments/Disbursements",
                    match_method="plaid",
                    weight=0.0,
                    is_stable=False
                )
        
        # STEP 2: SIMPLIFIED - Check PLAID INCOME_WAGES first (Pragmatic Fix)
        # Use simplified income detector (PLAID-first only, no behavioral)
        is_income, confidence, reason = self.income_detector.is_likely_income(
            description=description,
            amount=amount,
            plaid_category_primary=plaid_category_primary,
            plaid_category_detailed=plaid_category
        )
        
        # If PLAID identifies as income with high confidence, trust it
        if is_income and confidence >= 0.85:
            # Determine subcategory based on reason
            if "wages" in reason or "salary" in reason:
                return CategoryMatch(
                    category="income",
                    subcategory="salary",
                    confidence=confidence,
                    description="Salary & Wages",
                    match_method=f"plaid_{reason}",
                    weight=1.0,
                    is_stable=True
                )
            else:
                # Generic PLAID income - check if it matches specific patterns
                gig_match = self._check_gig_economy_patterns(combined_text)
                if gig_match:
                    return gig_match
                # Not gig economy, return as other income with lower weight
                return CategoryMatch(
                    category="income",
                    subcategory="other",
                    confidence=0.7,
                    description="Other Income",
                    match_method=f"plaid_{reason}",
                    # Weight 0.5 for unverifiable income (vs 1.0 for stable salary)
                    # This reflects that non-salary income is less reliable for affordability
                    weight=0.5,
                    is_stable=False
                )
        
        # STEP 3: Check income patterns (keyword matching ONLY)
        # No PLAID guessing or behavioral detection
        for subcategory, patterns in self.income_patterns.items():
            match = self._match_patterns(combined_text, patterns)
            if match:
                match_method, match_confidence = match
                
                return CategoryMatch(
                    category="income",
                    subcategory=subcategory,
                    confidence=match_confidence,
                    description=patterns.get("description", subcategory),
                    match_method=match_method,
                    weight=patterns.get("weight", 1.0),
                    is_stable=patterns.get("is_stable", False)
                )
        
        # STEP 4: Check for transfers (only if NOT identified as income above)
        if self._is_plaid_transfer(plaid_category_primary, plaid_category, description):
            return CategoryMatch(
                category="transfer",
                subcategory="internal",
                confidence=0.95,
                description="Internal Transfer",
                match_method="plaid",
                weight=0.0,  # Not counted as income
                is_stable=False
            )
        
        # Check if it's a transfer based on keywords (fallback)
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
        
        # STEP 5: Unknown income (default with low weight)
        return CategoryMatch(
            category="income",
            subcategory="other",
            confidence=0.5,
            description="Other Income",
            match_method="default",
            # Weight 0.5 for unverifiable income (vs 1.0 for stable salary)
            # This reflects that unknown income sources are less reliable for affordability
            weight=0.5,
            is_stable=False
        )
    
    def _check_credit_card_or_catalogue_debt(
        self,
        combined_text: str
    ) -> Optional[CategoryMatch]:
        """
        Check if transaction matches credit card or catalogue debt patterns.
        
        Helper method to avoid code duplication when checking for debt patterns
        before categorizing as groceries.
        
        Args:
            combined_text: Combined description and merchant text (normalized)
        
        Returns:
            CategoryMatch if debt pattern found, None otherwise
        """
        for subcategory, patterns in self.debt_patterns.items():
            if subcategory in ["credit_cards", "catalogue"]:
                match = self._match_patterns(combined_text, patterns)
                if match:
                    # This is a credit card or catalogue payment, not groceries
                    return CategoryMatch(
                        category="debt",
                        subcategory=subcategory,
                        confidence=match[1],
                        description=patterns.get("description", subcategory),
                        match_method=match[0],
                        risk_level=patterns.get("risk_level", "medium")
                    )
        return None
    
    def _categorize_expense(
        self, 
        combined_text: str, 
        description: str,
        plaid_category: Optional[str]
    ) -> CategoryMatch:
        """Categorize an expense transaction (debit)."""
        
        # STEP 1: Check strict PLAID categories FIRST
        strict_match = self._check_strict_plaid_categories(plaid_category)
        if strict_match:
            return strict_match
        
        # STEP 2: Check risk patterns (highest priority)
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
        
        # SIMPLIFIED: Let keyword patterns drive categorization naturally
        # No PLAID defaults that override keyword matching (Pragmatic Fix)
        
        # Special case: If description contains BANK or CREDIT CARD indicators, check debt first
        # This handles "SAINSBURYS BANK" vs "SAINSBURYS" distinction
        if any(indicator in combined_text for indicator in ["BANK", "CREDIT CARD", "CARD", "BARCLAYCARD"]):
            # Check debt patterns first for financial institutions
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
        
        # Check essential patterns BEFORE debt patterns (for non-bank transactions)
        # This prevents grocery stores from being miscategorized as credit card/catalogue debt
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
        
        # Check debt patterns AFTER essential patterns
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
            
        # IMPORTANT: Use PLAID category fallback BEFORE checking positive patterns
        # This prevents "positive" keyword collisions (e.g., CHIP vs Chipotle)
        # This preserves high-confidence PLAID categorizations (e.g., gambling, restaurants)
        # Only fall back to generic expense/other if PLAID also doesn't have a match
        if plaid_category:
            plaid_match = self._match_plaid_category(plaid_category, is_income=False)
            if plaid_match:
                return plaid_match
        
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
        
                
        # Unknown expense (only reached if no patterns matched AND no PLAID category)
        return CategoryMatch(
            category="expense",
            subcategory="other",
            confidence=0.3,
            description="Other Expense",
            match_method="default"
        )
    
    def _check_gig_economy_patterns(self, combined_text: str) -> Optional[CategoryMatch]:
        """
        Check if transaction matches gig economy patterns.
        
        Helper method to avoid duplicate gig economy checking logic.
        
        Args:
            combined_text: Combined description and merchant text (normalized)
        
        Returns:
            CategoryMatch if gig economy pattern found, None otherwise
        """
        for subcategory, patterns in self.income_patterns.items():
            if subcategory == "gig_economy":
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
        return None
    
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
    
    def _contains_salary_keywords(self, text: str) -> bool:
        """
        Check if transaction description contains salary/income-related keywords.
        
        This is used to identify legitimate salary payments that PLAID may have
        miscategorized as transfers (e.g., BANK GIRO CREDIT, FP- prefix payments).
        
        Args:
            text: Transaction description text (should be uppercase)
        
        Returns:
            True if salary keywords are found, False otherwise
        """
        if not text:
            return False
        
        # Check for salary keywords
        for keyword in self.SALARY_KEYWORDS:
            if keyword in text:
                return True
        
        # Check for FP- prefix (Faster Payments for salary)
        if text.startswith("FP-") or " FP-" in text:
            return True
        
        # Check for patterns like "COMPANY NAME LTD" or "COMPANY NAME LIMITED"
        # These often indicate employer payments
        if re.search(r'\b(LTD|LIMITED|PLC)\b', text):
            # But only if it doesn't contain obvious transfer keywords
            if not any(kw in text for kw in self.TRANSFER_EXCLUSION_KEYWORDS):
                return True
        
        return False
    
    def _is_plaid_transfer(
        self, 
        plaid_category_primary: Optional[str], 
        plaid_category_detailed: Optional[str],
        description: Optional[str] = None
    ) -> bool:
        """
        Check if transaction is a transfer based on Plaid categories.
        
        Args:
            plaid_category_primary: The primary Plaid category (e.g., "TRANSFER_IN")
            plaid_category_detailed: The detailed Plaid category (e.g., "TRANSFER_IN_ACCOUNT_TRANSFER")
            description: Optional transaction description to check for salary keywords
        
        Returns:
            True if the transaction is identified as a transfer, False otherwise
        """
        if not plaid_category_primary and not plaid_category_detailed:
            return False
        
        # Check primary category for transfer indicators
        if plaid_category_primary:
            primary_upper = plaid_category_primary.upper()
            if "TRANSFER_IN" in primary_upper or "TRANSFER_OUT" in primary_upper:
                # Before marking as transfer, check if description contains salary keywords
                # This catches legitimate salary payments that PLAID miscategorized
                if description and self._contains_salary_keywords(description.upper()):
                    return False  # Not a transfer - it's likely salary
                return True
        
        # Check detailed category for transfer indicators
        if plaid_category_detailed:
            detailed_upper = plaid_category_detailed.upper()
            # Look for transfer-related keywords in detailed category
            if "TRANSFER" in detailed_upper:
                # Before marking as transfer, check if description contains salary keywords
                if description and self._contains_salary_keywords(description.upper()):
                    return False  # Not a transfer - it's likely salary
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
            # Food and dining categories
            if "RESTAURANT" in plaid_upper or "FOOD_AND_DRINK" in plaid_upper:
                return CategoryMatch(
                    category="expense",
                    subcategory="food_dining",
                    confidence=0.85,
                    description="Food & Dining",
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
            plaid_category = (
                txn.get("personal_finance_category.detailed")
                or txn.get("plaid_category_detailed")
            )

            plaid_category_primary = (
                txn.get("personal_finance_category.primary")
                or txn.get("plaid_category_primary")
            )

            
            # Handle nested PLAID category if present
            if "personal_finance_category" in txn:
                pfc = txn.get("personal_finance_category", {})
                if isinstance(pfc, dict):
                    if not plaid_category:
                        plaid_category = pfc.get("detailed")
                    if not plaid_category_primary:
                        plaid_category_primary = pfc.get("primary")
            
            category_match = self.categorize_transaction(
                description=description,
                amount=amount,
                merchant_name=merchant_name,
                plaid_category=plaid_category,
                plaid_category_primary=plaid_category_primary
            )
            
            results.append((txn, category_match))
        
        return results
    
    def categorize_transactions_batch(
        self,
        transactions: List[Dict]
    ) -> List[Tuple[Dict, CategoryMatch]]:
        """
        Categorize a list of transactions with optimized batch processing.
        
        This method is more efficient than categorize_transactions() for large
        transaction lists because it performs recurring pattern detection once
        for the entire batch, rather than potentially analyzing patterns for
        each individual transaction.
        
        Performance Benefits:
        - Single pass for recurring income detection (O(n²) once vs. potentially per-transaction)
        - Cached pattern lookup for individual categorizations (O(1) per transaction)
        - Dramatically faster for large transaction sets (100+ transactions)
        
        Args:
            transactions: List of transaction dictionaries with:
                - 'name': Transaction description
                - 'amount': Amount (negative for credits, positive for debits)
                - 'date': Transaction date (YYYY-MM-DD)
                - 'merchant_name': Optional merchant name
                - 'personal_finance_category': Optional PLAID category (dict or flat fields)
        
        Returns:
            List of tuples (transaction, category_match)
        
        Example:
            >>> categorizer = TransactionCategorizer()
            >>> transactions = [
            ...     {"name": "ACME LTD SALARY", "amount": -2500, "date": "2024-01-25"},
            ...     {"name": "TESCO", "amount": 45.50, "date": "2024-01-26"},
            ... ]
            >>> results = categorizer.categorize_transactions_batch(transactions)
            >>> for txn, match in results:
            ...     print(f"{txn['name']}: {match.category}/{match.subcategory}")
        """
        # Step 1: Analyze batch for recurring income patterns
        # This populates the income detector's cache with recurring sources
        self.income_detector.analyze_batch(transactions)
        
        try:
            # Step 2: Categorize each transaction using cached patterns
            results = []
            
            for idx, txn in enumerate(transactions):
                description = txn.get("name", "")
                amount = txn.get("amount", 0)
                merchant_name = txn.get("merchant_name")
                plaid_category = (
                    txn.get("personal_finance_category.detailed")
                    or txn.get("plaid_category_detailed")
                )

                plaid_category_primary = (
                    txn.get("personal_finance_category.primary")
                    or txn.get("plaid_category_primary")
        )

                
                # Handle nested PLAID category if present
                if "personal_finance_category" in txn:
                    pfc = txn.get("personal_finance_category", {})
                    if isinstance(pfc, dict):
                        if not plaid_category:
                            plaid_category = pfc.get("detailed")
                        if not plaid_category_primary:
                            plaid_category_primary = pfc.get("primary")
                
                # Use optimized batch categorization
                category_match = self._categorize_transaction_from_batch(
                    description=description,
                    amount=amount,
                    transaction_index=idx,
                    merchant_name=merchant_name,
                    plaid_category=plaid_category,
                    plaid_category_primary=plaid_category_primary
                )
                
                results.append((txn, category_match))
            
            return results
        
        finally:
            # Step 3: Clean up cache to avoid memory leaks
            self.income_detector.clear_batch_cache()
    
    def _categorize_transaction_from_batch(
        self,
        description: str,
        amount: float,
        transaction_index: int,
        merchant_name: Optional[str] = None,
        plaid_category: Optional[str] = None,
        plaid_category_primary: Optional[str] = None
    ) -> CategoryMatch:
        """
        Categorize a single transaction using cached batch patterns.
        
        Internal method used by categorize_transactions_batch(). Uses the
        income detector's cached recurring patterns for efficient categorization.
        
        Args:
            description: Transaction description/name
            amount: Transaction amount (negative = credit, positive = debit)
            transaction_index: Index in the batch (for pattern lookup)
            merchant_name: Optional merchant name from PLAID
            plaid_category: Optional PLAID category (personal_finance_category.detailed)
            plaid_category_primary: Optional PLAID primary category
        
        Returns:
            CategoryMatch with categorization result
        """
        # Normalize text for matching
        text = self._normalize_text(description)
        merchant_text = self._normalize_text(merchant_name) if merchant_name else ""
        combined_text = f"{text} {merchant_text}".strip()
        
        # Determine if income or expense
        is_credit = amount < 0
        
        if is_credit:
            return self._categorize_income_from_batch(
                combined_text, 
                text, 
                amount, 
                transaction_index,
                plaid_category, 
                plaid_category_primary
            )
        else:
            return self._categorize_expense(combined_text, text, plaid_category)
    
    def _categorize_income_from_batch(
        self,
        combined_text: str,
        description: str,
        amount: float,
        transaction_index: int,
        plaid_category: Optional[str],
        plaid_category_primary: Optional[str] = None
    ) -> CategoryMatch:
        """
        Categorize an income transaction using cached batch patterns.
        
        Internal method that uses the optimized is_likely_income_from_batch()
        which leverages pre-computed recurring patterns.
        """
        # STEP 0A: Check strict PLAID categories FIRST (before any other logic)
        strict_match = self._check_strict_plaid_categories(plaid_category)
        if strict_match:
            return strict_match
        
        # STEP 0B: Check if this is a known expense service (same as non-batch)
        for service in self.KNOWN_EXPENSE_SERVICES:
            if service in combined_text:
                if plaid_category_primary:
                    plaid_primary_upper = plaid_category_primary.upper()
                    if "TRANSFER" in plaid_primary_upper:
                        return CategoryMatch(
                            category="transfer",
                            subcategory="internal",
                            confidence=0.90,
                            description="Internal Transfer",
                            match_method="plaid",
                            weight=0.0,
                            is_stable=False
                        )
                    # CRITICAL: Check for LOAN_PAYMENTS to prevent loan disbursements from being income
                    if "LOAN_PAYMENTS" in plaid_primary_upper:
                        return CategoryMatch(
                            category="income",
                            subcategory="loans",
                            confidence=0.95,
                            description="Loan Payments/Disbursements",
                            match_method="plaid",
                            weight=0.0,
                            is_stable=False
                        )
                return CategoryMatch(
                    category="income",
                    subcategory="other",
                    confidence=0.5,
                    description="Other Income",
                    match_method="known_service_exclusion",
                    weight=1.0,
                    is_stable=False
                )
        
        # STEP 1: Check PLAID categories for loan/transfer indicators (same as non-batch)
        if plaid_category or plaid_category_primary:
            plaid_cat_upper = (plaid_category or "").upper()
            plaid_primary_upper = (plaid_category_primary or "").upper()
            
            # Check for LOAN_PAYMENTS category - these are loan disbursements/refunds, NOT income
            if "LOAN_PAYMENTS" in plaid_primary_upper or "LOAN_PAYMENTS" in plaid_cat_upper:
                return CategoryMatch(
                    category="income",
                    subcategory="loans",
                    confidence=0.95,
                    description="Loan Payments/Disbursements",
                    match_method="plaid",
                    weight=0.0,
                    is_stable=False
                )
            
            if "CASH_ADVANCES" in plaid_cat_upper or "ADVANCES" in plaid_cat_upper or "LOANS" in plaid_cat_upper:
                return CategoryMatch(
                    category="income",
                    subcategory="loans",
                    confidence=0.95,
                    description="Loan Payments/Disbursements",
                    match_method="plaid",
                    weight=0.0,
                    is_stable=False
                )
        
        # SIMPLIFIED: Use same logic as non-batch (Pragmatic Fix)
        # Just delegate to simplified income detector
        is_income, confidence, reason = self.income_detector.is_likely_income_from_batch(
            description=description,
            amount=amount,
            transaction_index=transaction_index,
            plaid_category_primary=plaid_category_primary,
            plaid_category_detailed=plaid_category
        )
        
        # If PLAID identifies as income with high confidence, trust it
        if is_income and confidence >= 0.85:
            # Determine subcategory based on reason
            if "wages" in reason or "salary" in reason:
                return CategoryMatch(
                    category="income",
                    subcategory="salary",
                    confidence=confidence,
                    description="Salary & Wages",
                    match_method=f"batch_plaid_{reason}",
                    weight=1.0,
                    is_stable=True
                )
            else:
                # Generic PLAID income - check if it matches specific patterns
                gig_match = self._check_gig_economy_patterns(combined_text)
                if gig_match:
                    gig_match.match_method = f"batch_{gig_match.match_method}"
                    return gig_match
                # Not gig economy, return as other income with lower weight
                return CategoryMatch(
                    category="income",
                    subcategory="other",
                    confidence=0.7,
                    description="Other Income",
                    match_method=f"batch_plaid_{reason}",
                    weight=0.5,  # Lower weight for uncertain income
                    is_stable=False
                )
        
        # Check income patterns (keyword matching ONLY)
        for subcategory, patterns in self.income_patterns.items():
            match = self._match_patterns(combined_text, patterns)
            if match:
                match_method, match_confidence = match
                
                return CategoryMatch(
                    category="income",
                    subcategory=subcategory,
                    confidence=match_confidence,
                    description=patterns.get("description", subcategory),
                    match_method=match_method,
                    weight=patterns.get("weight", 1.0),
                    is_stable=patterns.get("is_stable", False)
                )
        
        # Check for transfers (only if NOT identified as income above)
        if self._is_plaid_transfer(plaid_category_primary, plaid_category, description):
            return CategoryMatch(
                category="transfer",
                subcategory="internal",
                confidence=0.95,
                description="Internal Transfer",
                match_method="plaid",
                weight=0.0,
                is_stable=False
            )
        
        # Check if it's a transfer based on keywords (fallback)
        if self._is_transfer(combined_text):
            return CategoryMatch(
                category="transfer",
                subcategory="internal",
                confidence=0.9,
                description="Internal Transfer",
                match_method="keyword",
                weight=0.0,
                is_stable=False
            )
        
        # Unknown income (default with low weight)
        return CategoryMatch(
            category="income",
            subcategory="other",
            confidence=0.5,
            description="Other Income",
            match_method="default",
            weight=0.5,  # Lower weight for unverifiable income
            is_stable=False
        )
    
    def get_category_summary(
        self, 
        categorized_transactions: List[Tuple[Dict, CategoryMatch]]
    ) -> Dict:
        """
        Generate a summary of categorized transactions.
        
        Returns:
            Dictionary with category totals and counts
        """
        # Get most recent transaction date to calculate lookback periods
        # This determines the reference point for time-based filtering
        recent_date = None
        for txn, _ in categorized_transactions:
            txn_date_str = txn.get("date", "")
            if txn_date_str:
                try:
                    txn_date = datetime.strptime(txn_date_str, "%Y-%m-%d")
                    if recent_date is None or txn_date > recent_date:
                        recent_date = txn_date
                except ValueError:
                    continue
        
        # If no valid dates found, use current date as fallback
        # This ensures the function works even with malformed data,
        # though in production all transactions should have valid dates
        if recent_date is None:
            recent_date = datetime.now()
        
        # Calculate lookback dates for time-based filtering
        hcstc_cutoff = recent_date - timedelta(days=90)  # 90 days for HCSTC
        failed_payment_cutoff = recent_date - timedelta(days=45)  # 45 days for failed payments
        bank_charges_cutoff = recent_date - timedelta(days=90)  # 90 days for bank charges
        new_credit_cutoff = recent_date - timedelta(days=90)  # 90 days for new credit
        
        summary = {
            "income": {
                "salary": {"total": 0.0, "count": 0},
                "benefits": {"total": 0.0, "count": 0},
                "pension": {"total": 0.0, "count": 0},
                "gig_economy": {"total": 0.0, "count": 0},
                "loans": {"total": 0.0, "count": 0},
                "other": {"total": 0.0, "count": 0},
            },
            "debt": {
                "hcstc_payday": {
                    "total": 0.0, 
                    "count": 0, 
                    "lenders": set(),
                    "lenders_90d": set(),  # Track lenders in last 90 days
                    "credit_providers_90d": set(),  # All credit providers in last 90 days
                },
                "other_loans": {
                    "total": 0.0, 
                    "count": 0,
                    "providers_90d": set(),
                },
                "credit_cards": {
                    "total": 0.0, 
                    "count": 0,
                    "providers_90d": set(),
                },
                "bnpl": {
                    "total": 0.0, 
                    "count": 0,
                    "providers_90d": set(),
                },
                "catalogue": {
                    "total": 0.0, 
                    "count": 0,
                    "providers_90d": set(),
                },
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
                "failed_payments": {
                    "total": 0.0, 
                    "count": 0,
                    "count_45d": 0,  # Count in last 45 days
                },
                "debt_collection": {"total": 0.0, "count": 0, "dcas": set()},
                "bank_charges": {
                    "total": 0.0, 
                    "count": 0,
                    "count_90d": 0,  # Count in last 90 days
                },
            },
            "positive": {
                "savings": {"total": 0.0, "count": 0},
            },
            "transfer": {
                "internal": {"total": 0.0, "count": 0},
                "external": {"total": 0.0, "count": 0},
            },
            "other": {"total": 0.0, "count": 0},
        }
        
        for txn, match in categorized_transactions:
            amount = abs(txn.get("amount", 0))
            category = match.category
            subcategory = match.subcategory
            
            # Parse transaction date
            txn_date = None
            txn_date_str = txn.get("date", "")
            if txn_date_str:
                try:
                    txn_date = datetime.strptime(txn_date_str, "%Y-%m-%d")
                except ValueError:
                    pass
            
            if category in summary and subcategory in summary.get(category, {}):
                # Apply weight ONLY for income (to discount uncertain sources)
                # For expenses, debt, risk, etc., always use full amount for accurate affordability
                if category == "income":
                    summary[category][subcategory]["total"] += (amount * match.weight)
                else:
                    summary[category][subcategory]["total"] += amount
                summary[category][subcategory]["count"] += 1
                
                # Track distinct HCSTC lenders (all time and 90 days)
                if category == "debt" and subcategory == "hcstc_payday":
                    merchant = txn.get("merchant_name") or txn.get("name", "")
                    # Normalize to canonical lender name to avoid counting same lender multiple times
                    canonical_lender = self._normalize_hcstc_lender(merchant)
                    if canonical_lender:
                        summary[category][subcategory]["lenders"].add(canonical_lender)
                        
                        # Track 90-day HCSTC lenders
                        if txn_date and txn_date >= hcstc_cutoff:
                            summary[category][subcategory]["lenders_90d"].add(canonical_lender)
                            summary[category][subcategory]["credit_providers_90d"].add(canonical_lender)
                    else:
                        # Fallback for unrecognized HCSTC lenders
                        merchant_key = merchant.upper()[:20]
                        summary[category][subcategory]["lenders"].add(merchant_key)
                        if txn_date and txn_date >= hcstc_cutoff:
                            summary[category][subcategory]["lenders_90d"].add(merchant_key)
                            summary[category][subcategory]["credit_providers_90d"].add(merchant_key)
                
                # Track credit providers in last 90 days for new credit burst detection
                if category == "debt" and txn_date and txn_date >= new_credit_cutoff:
                    merchant = txn.get("merchant_name") or txn.get("name", "")
                    merchant_key = merchant.upper()[:20]
                    if subcategory in ["other_loans", "credit_cards", "bnpl", "catalogue"]:
                        summary[category][subcategory]["providers_90d"].add(merchant_key)
                        summary["debt"]["hcstc_payday"]["credit_providers_90d"].add(merchant_key)
                
                # Track distinct DCAs
                if category == "risk" and subcategory == "debt_collection":
                    merchant = txn.get("merchant_name") or txn.get("name", "")
                    summary[category][subcategory]["dcas"].add(
                        merchant.upper()[:20]
                    )
                
                # Track failed payments in last 45 days
                if category == "risk" and subcategory == "failed_payments":
                    if txn_date and txn_date >= failed_payment_cutoff:
                        summary[category][subcategory]["count_45d"] += 1
                
                # Track bank charges in last 90 days
                if category == "risk" and subcategory == "bank_charges":
                    if txn_date and txn_date >= bank_charges_cutoff:
                        summary[category][subcategory]["count_90d"] += 1
            
            elif category == "transfer":
                if subcategory in summary["transfer"]:
                    summary["transfer"][subcategory]["total"] += amount
                    summary["transfer"][subcategory]["count"] += 1
                else:
                    # Fallback for any unexpected subcategory
                    if "other" not in summary["transfer"]:
                        summary["transfer"]["other"] = {"total": 0.0, "count": 0}
                    summary["transfer"]["other"]["total"] += amount
                    summary["transfer"]["other"]["count"] += 1
            else:
                summary["other"]["total"] += amount
                summary["other"]["count"] += 1
        
        # Convert sets to counts and consolidate new credit providers
        if "lenders" in summary["debt"]["hcstc_payday"]:
            summary["debt"]["hcstc_payday"]["distinct_lenders"] = len(
                summary["debt"]["hcstc_payday"]["lenders"]
            )
            del summary["debt"]["hcstc_payday"]["lenders"]
        
        if "lenders_90d" in summary["debt"]["hcstc_payday"]:
            summary["debt"]["hcstc_payday"]["distinct_lenders_90d"] = len(
                summary["debt"]["hcstc_payday"]["lenders_90d"]
            )
            del summary["debt"]["hcstc_payday"]["lenders_90d"]
        
        # Calculate total distinct credit providers in last 90 days
        all_credit_providers_90d = summary["debt"]["hcstc_payday"]["credit_providers_90d"].copy()
        for subcategory in ["other_loans", "credit_cards", "bnpl", "catalogue"]:
            all_credit_providers_90d.update(summary["debt"][subcategory].get("providers_90d", set()))
            # Clean up the individual sets
            if "providers_90d" in summary["debt"][subcategory]:
                del summary["debt"][subcategory]["providers_90d"]
        
        summary["debt"]["hcstc_payday"]["new_credit_providers_90d"] = len(all_credit_providers_90d)
        del summary["debt"]["hcstc_payday"]["credit_providers_90d"]
        
        if "dcas" in summary["risk"]["debt_collection"]:
            summary["risk"]["debt_collection"]["distinct_dcas"] = len(
                summary["risk"]["debt_collection"]["dcas"]
            )
            del summary["risk"]["debt_collection"]["dcas"]
        
        return summary
