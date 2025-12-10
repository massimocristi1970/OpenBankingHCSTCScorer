"""
Behavioral Income Detection Module for HCSTC Loan Scoring.

Detects income through recurring patterns, payroll keywords, and behavioral analysis.
This module helps identify legitimate salary payments that PLAID may have miscategorized
as TRANSFER_IN by analyzing transaction patterns and descriptions.
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class RecurringIncomeSource:
    """Represents a detected recurring income source."""
    description_pattern: str
    amount_avg: float
    amount_std_dev: float
    frequency_days: float  # Average days between payments
    occurrence_count: int
    transaction_indices: List[int]  # Indices in original transaction list
    confidence: float  # 0.0 to 1.0
    source_type: str  # 'salary', 'benefits', 'pension', 'unknown'


class IncomeDetector:
    """Detects income through behavioral patterns and keywords."""
    
    # UK Payroll Keywords (expanded from TransactionCategorizer)
    PAYROLL_KEYWORDS = [
        "SALARY", "WAGES", "PAYROLL", "NET PAY", "WAGE", 
        "PAYSLIP", "EMPLOYER", "EMPLOYERS",
        "BGC", "BANK GIRO CREDIT", "CHEQUERS CONTRACT",
        "CONTRACT PAY", "MONTHLY PAY", "WEEKLY PAY",
        "BACS CREDIT", "FASTER PAYMENT", "FP-",
        "EMPLOYMENT", "PAYCHECK"
    ]
    
    # UK Government Benefits Keywords
    BENEFIT_KEYWORDS = [
        "UNIVERSAL CREDIT", "UC", "DWP", "HMRC", 
        "CHILD BENEFIT", "PIP", "DLA", "ESA", "JSA",
        "PENSION CREDIT", "HOUSING BENEFIT",
        "TAX CREDIT", "WORKING TAX", "CHILD TAX",
        "CARERS ALLOWANCE", "ATTENDANCE ALLOWANCE",
        "BEREAVEMENT", "MATERNITY ALLOWANCE"
    ]
    
    # Pension Keywords
    PENSION_KEYWORDS = [
        "PENSION", "ANNUITY", "STATE PENSION", "RETIREMENT",
        "NEST", "AVIVA", "LEGAL AND GENERAL", "SCOTTISH WIDOWS",
        "STANDARD LIFE", "PRUDENTIAL", "ROYAL LONDON", "AEGON"
    ]
    
    # Keywords that indicate NOT income (internal transfers)
    EXCLUSION_KEYWORDS = [
        "OWN ACCOUNT", "INTERNAL", "SELF TRANSFER",
        "FROM SAVINGS", "FROM CURRENT", "MOVED FROM",
        "MOVED TO", "BETWEEN ACCOUNTS", "INTERNAL TFR",
        "ISA TRANSFER", "SAVINGS TRANSFER"
    ]
    
    # Loan disbursement keywords (not income)
    LOAN_KEYWORDS = [
        "LENDING STREAM", "LENDINGSTREAM", "DRAFTY",
        "MR LENDER", "MONEYBOAT", "CREDITSPRING",
        "CASHFLOAT", "QUIDMARKET", "LOANS 2 GO",
        "LOAN DISBURSEMENT", "LOAN ADVANCE",
        "PAYDAY LOAN", "SHORT TERM LOAN"
    ]
    
    def __init__(self, min_amount: float = 50.0, min_occurrences: int = 2):
        """
        Initialize the income detector.
        
        Args:
            min_amount: Minimum transaction amount to consider for income detection
            min_occurrences: Minimum number of occurrences to consider as recurring
        """
        self.min_amount = min_amount
        self.min_occurrences = min_occurrences
    
    def find_recurring_income_sources(
        self, 
        transactions: List[Dict]
    ) -> List[RecurringIncomeSource]:
        """
        Find recurring income sources by analyzing transaction patterns.
        
        Groups similar transactions by amount and description, then identifies
        those with regular intervals (weekly, fortnightly, monthly, etc.).
        
        Args:
            transactions: List of transaction dictionaries with 'amount', 'date', 'name'
        
        Returns:
            List of RecurringIncomeSource objects
        """
        # Filter to credit transactions (negative amounts in PLAID format)
        # and above minimum amount threshold
        income_candidates = []
        for idx, txn in enumerate(transactions):
            amount = txn.get("amount", 0)
            if amount < 0 and abs(amount) >= self.min_amount:
                income_candidates.append((idx, txn))
        
        if len(income_candidates) < self.min_occurrences:
            return []
        
        # Group transactions by normalized description
        description_groups = defaultdict(list)
        for idx, txn in income_candidates:
            normalized_desc = self._normalize_description(txn.get("name", ""))
            description_groups[normalized_desc].append((idx, txn))
        
        # Analyze each group for recurring patterns
        recurring_sources = []
        for desc_pattern, group in description_groups.items():
            if len(group) < self.min_occurrences:
                continue
            
            # Extract amounts and dates
            amounts = []
            dates = []
            indices = []
            
            for idx, txn in group:
                amount = abs(txn.get("amount", 0))
                date_str = txn.get("date", "")
                
                if date_str:
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                        amounts.append(amount)
                        dates.append(date)
                        indices.append(idx)
                    except ValueError:
                        continue
            
            if len(amounts) < self.min_occurrences or len(dates) < self.min_occurrences:
                continue
            
            # Check if amounts are similar (within 30% variance)
            avg_amount = sum(amounts) / len(amounts)
            amount_variance = max(abs(a - avg_amount) / avg_amount for a in amounts)
            
            if amount_variance > 0.30:  # More than 30% variance
                continue
            
            # Calculate frequency (average days between payments)
            if len(dates) >= 2:
                dates_sorted = sorted(dates)
                intervals = []
                for i in range(1, len(dates_sorted)):
                    interval = (dates_sorted[i] - dates_sorted[i-1]).days
                    intervals.append(interval)
                
                avg_interval = sum(intervals) / len(intervals)
                
                # Check if interval matches common pay periods
                # Weekly: 7±2 days, Fortnightly: 14±3 days, 
                # Monthly: 28-31 days, 4-weekly: 28±3 days
                is_regular_interval = (
                    (5 <= avg_interval <= 9) or      # Weekly
                    (11 <= avg_interval <= 17) or    # Fortnightly
                    (25 <= avg_interval <= 35)       # Monthly/4-weekly
                )
                
                if not is_regular_interval:
                    continue
            else:
                avg_interval = 0
            
            # Calculate standard deviation
            if len(amounts) > 1:
                variance = sum((a - avg_amount) ** 2 for a in amounts) / len(amounts)
                std_dev = variance ** 0.5
            else:
                std_dev = 0
            
            # Determine source type and confidence
            source_type, confidence = self._classify_income_source(
                desc_pattern, 
                avg_amount, 
                len(amounts),
                avg_interval
            )
            
            recurring_sources.append(RecurringIncomeSource(
                description_pattern=desc_pattern,
                amount_avg=avg_amount,
                amount_std_dev=std_dev,
                frequency_days=avg_interval,
                occurrence_count=len(amounts),
                transaction_indices=indices,
                confidence=confidence,
                source_type=source_type
            ))
        
        # Sort by confidence (highest first)
        recurring_sources.sort(key=lambda x: x.confidence, reverse=True)
        
        return recurring_sources
    
    def _normalize_description(self, description: str) -> str:
        """
        Normalize transaction description for grouping.
        
        Removes dates, reference numbers, and other variable parts to group
        similar transactions together.
        """
        if not description:
            return ""
        
        desc = description.upper().strip()
        
        # Remove common prefixes
        desc = re.sub(r'^(FP-|FASTER PAYMENTS?|BGC|BACS)\s*', '', desc)
        
        # Remove dates (various formats)
        desc = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '', desc)
        desc = re.sub(r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b', '', desc)
        
        # Remove reference numbers (patterns like "REF 123456", "209074 40964700")
        desc = re.sub(r'\bREF\s*\d+\b', '', desc)
        desc = re.sub(r'\b\d{6,}\b', '', desc)  # Long number sequences
        
        # Remove transaction IDs
        desc = re.sub(r'\b[A-Z0-9]{10,}\b', '', desc)
        
        # Normalize whitespace
        desc = ' '.join(desc.split())
        
        return desc
    
    def _classify_income_source(
        self, 
        description: str, 
        amount: float, 
        occurrence_count: int,
        frequency_days: float
    ) -> Tuple[str, float]:
        """
        Classify income source type and calculate confidence.
        
        Returns:
            Tuple of (source_type, confidence)
        """
        desc_upper = description.upper()
        
        # Check for exclusions first (these are NOT income)
        if any(keyword in desc_upper for keyword in self.EXCLUSION_KEYWORDS):
            return ("unknown", 0.0)
        
        if any(keyword in desc_upper for keyword in self.LOAN_KEYWORDS):
            return ("unknown", 0.0)
        
        # Base confidence from occurrence count and regularity
        base_confidence = min(0.7, 0.4 + (occurrence_count * 0.1))
        
        # Check for payroll patterns
        if self.matches_payroll_patterns(description):
            # Higher confidence for weekly/fortnightly (typical salary patterns)
            if 5 <= frequency_days <= 9 or 11 <= frequency_days <= 17:
                return ("salary", min(0.95, base_confidence + 0.25))
            # Monthly salary
            elif 25 <= frequency_days <= 35:
                return ("salary", min(0.95, base_confidence + 0.20))
            return ("salary", min(0.90, base_confidence + 0.15))
        
        # Check for benefits patterns
        if self.matches_benefit_patterns(description):
            # Benefits are typically monthly
            if 25 <= frequency_days <= 35:
                return ("benefits", min(0.95, base_confidence + 0.25))
            return ("benefits", min(0.90, base_confidence + 0.15))
        
        # Check for pension patterns
        if self._matches_pension_patterns(description):
            # Pensions are typically monthly
            if 25 <= frequency_days <= 35:
                return ("pension", min(0.95, base_confidence + 0.25))
            return ("pension", min(0.90, base_confidence + 0.15))
        
        # Check for company name patterns (LTD, PLC, etc.)
        if re.search(r'\b(LTD|LIMITED|PLC|CORP|CORPORATION|INC)\b', desc_upper):
            # Likely employer payment
            if 25 <= frequency_days <= 35:  # Monthly
                return ("salary", min(0.85, base_confidence + 0.15))
            elif 11 <= frequency_days <= 17:  # Fortnightly
                return ("salary", min(0.85, base_confidence + 0.15))
            return ("salary", min(0.75, base_confidence + 0.10))
        
        # Regular payment with reasonable amount (£200+) and monthly cadence
        if amount >= 200 and 25 <= frequency_days <= 35:
            return ("unknown", min(0.70, base_confidence + 0.10))
        
        return ("unknown", base_confidence)
    
    def matches_payroll_patterns(self, description: str) -> bool:
        """
        Check if transaction description matches UK payroll patterns.
        
        Args:
            description: Transaction description (will be uppercased internally)
        
        Returns:
            True if payroll keywords found, False otherwise
        """
        if not description:
            return False
        
        desc_upper = description.upper()
        
        # Check for payroll keywords
        for keyword in self.PAYROLL_KEYWORDS:
            if keyword in desc_upper:
                return True
        
        # Check for FP- prefix (Faster Payments for salary)
        if desc_upper.startswith("FP-") or " FP-" in desc_upper:
            return True
        
        return False
    
    def matches_benefit_patterns(self, description: str) -> bool:
        """
        Check if transaction description matches UK government benefit patterns.
        
        Args:
            description: Transaction description (will be uppercased internally)
        
        Returns:
            True if benefit keywords found, False otherwise
        """
        if not description:
            return False
        
        desc_upper = description.upper()
        
        # Check for benefit keywords
        for keyword in self.BENEFIT_KEYWORDS:
            if keyword in desc_upper:
                return True
        
        return False
    
    def _matches_pension_patterns(self, description: str) -> bool:
        """
        Check if transaction description matches pension patterns.
        
        Args:
            description: Transaction description (will be uppercased internally)
        
        Returns:
            True if pension keywords found, False otherwise
        """
        if not description:
            return False
        
        desc_upper = description.upper()
        
        # Check for pension keywords
        for keyword in self.PENSION_KEYWORDS:
            if keyword in desc_upper:
                return True
        
        return False
    
    def is_likely_income(
        self, 
        description: str, 
        amount: float,
        plaid_category_primary: Optional[str] = None,
        plaid_category_detailed: Optional[str] = None,
        all_transactions: Optional[List[Dict]] = None,
        current_txn_index: Optional[int] = None
    ) -> Tuple[bool, float, str]:
        """
        Determine if a transaction is likely income using combined heuristics.
        
        This is the main entry point for income detection. It combines:
        1. PLAID category analysis (if INCOME category, high confidence)
        2. Keyword matching (payroll, benefits, pension)
        3. Recurring pattern detection (if full transaction list provided)
        4. Exclusion rules (transfers, loans)
        
        Args:
            description: Transaction description
            amount: Transaction amount (should be negative for credits)
            plaid_category_primary: PLAID primary category
            plaid_category_detailed: PLAID detailed category
            all_transactions: Optional full transaction list for pattern analysis
            current_txn_index: Index of current transaction in all_transactions
        
        Returns:
            Tuple of (is_likely_income, confidence, reason)
        """
        if amount >= 0:  # Not a credit
            return (False, 0.0, "not_credit")
        
        desc_upper = description.upper() if description else ""
        
        # 1. Check for exclusions first
        for keyword in self.EXCLUSION_KEYWORDS:
            if keyword in desc_upper:
                return (False, 0.0, "internal_transfer")
        
        for keyword in self.LOAN_KEYWORDS:
            if keyword in desc_upper:
                return (False, 0.0, "loan_disbursement")
        
        # 2. Check PLAID INCOME category (highest priority)
        if plaid_category_detailed:
            detailed_upper = plaid_category_detailed.upper()
            if "INCOME" in detailed_upper:
                # Return specific reason based on detailed category
                if "WAGES" in detailed_upper or "SALARY" in detailed_upper or "PAYROLL" in detailed_upper:
                    return (True, 0.95, "plaid_income_salary")
                elif "BENEFIT" in detailed_upper or "GOVERNMENT" in detailed_upper:
                    return (True, 0.95, "plaid_income_benefits")
                elif "PENSION" in detailed_upper or "RETIREMENT" in detailed_upper:
                    return (True, 0.95, "plaid_income_pension")
                else:
                    return (True, 0.95, "plaid_income_category")
        
        if plaid_category_primary:
            if "INCOME" in plaid_category_primary.upper():
                return (True, 0.95, "plaid_income_category")
        
        # 3. Check keyword matching (high confidence)
        if self.matches_payroll_patterns(description):
            return (True, 0.90, "payroll_keywords")
        
        if self.matches_benefit_patterns(description):
            return (True, 0.90, "benefit_keywords")
        
        if self._matches_pension_patterns(description):
            return (True, 0.90, "pension_keywords")
        
        # 4. Check for company name patterns
        if re.search(r'\b(LTD|LIMITED|PLC|CORP|CORPORATION|INC)\b', desc_upper):
            # Company payment, but check it's not marked as transfer by PLAID
            if plaid_category_primary and "TRANSFER" in plaid_category_primary.upper():
                # Company name but PLAID says transfer - need more evidence
                if abs(amount) >= 500:  # Large regular amount
                    return (True, 0.75, "company_payment_large_amount")
                return (False, 0.0, "company_transfer_ambiguous")
            return (True, 0.80, "company_payment")
        
        # 5. Check recurring patterns if full transaction list provided
        if all_transactions and current_txn_index is not None:
            recurring_sources = self.find_recurring_income_sources(all_transactions)
            
            # Check if current transaction is part of a recurring pattern
            for source in recurring_sources:
                if current_txn_index in source.transaction_indices:
                    if source.confidence >= 0.70:
                        return (True, source.confidence, f"recurring_{source.source_type}")
        
        # 6. If PLAID says TRANSFER but no other indicators, not income
        if plaid_category_primary and "TRANSFER" in plaid_category_primary.upper():
            return (False, 0.0, "plaid_transfer_category")
        
        if plaid_category_detailed and "TRANSFER" in plaid_category_detailed.upper():
            return (False, 0.0, "plaid_transfer_category")
        
        # 7. Default: unknown
        return (False, 0.0, "insufficient_evidence")
