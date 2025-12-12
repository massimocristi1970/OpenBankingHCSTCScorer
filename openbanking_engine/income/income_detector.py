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
    day_of_month_consistent: bool = False  # Whether payment day is consistent (±3 days)


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
    # Note: These are common UK HCSTC lenders and loan-related terms
    # Kept separate from transaction_categorizer.HCSTC_LENDER_CANONICAL_NAMES
    # to avoid circular imports and maintain simple exclusion logic
    LOAN_KEYWORDS = [
        "LENDING STREAM", "LENDINGSTREAM", "DRAFTY",
        "MR LENDER", "MRLENDER", "MONEYBOAT", "CREDITSPRING",
        "CASHFLOAT", "QUIDMARKET", "QUID MARKET", "LOANS 2 GO", "LOANS2GO",
        "LOAN DISBURSEMENT", "LOAN ADVANCE",
        "PAYDAY LOAN", "SHORT TERM LOAN",
        "POLAR CREDIT", "118 118 MONEY", "CASHASAP"
    ]
    
    # Minimum amount threshold for large payments (used in company payment detection)
    LARGE_PAYMENT_THRESHOLD = 500.0
    
    # Thresholds for removing long number sequences and transaction IDs from descriptions
    # These help normalize descriptions while preserving meaningful employer names
    LONG_NUMBER_THRESHOLD = 8  # Remove number sequences with 8+ digits
    LONG_ID_THRESHOLD = 12  # Remove alphanumeric IDs with 12+ characters
    
    # Payment frequency thresholds (in days)
    # These define the acceptable ranges for different payment cadences
    WEEKLY_MIN_DAYS = 5        # Weekly payments: 7 days ±2 days tolerance
    WEEKLY_MAX_DAYS = 9
    FORTNIGHTLY_MIN_DAYS = 11  # Fortnightly payments: 14 days ±3 days tolerance
    FORTNIGHTLY_MAX_DAYS = 17
    MONTHLY_MIN_DAYS = 25      # Monthly payments: 28-31 days ±3 days tolerance
    MONTHLY_MAX_DAYS = 35
    
    # Variance thresholds for salary detection
    SALARY_TIGHT_VARIANCE = 0.05  # 5% variance for tight patterns (monthly with consistent day)
    SALARY_LOOSE_VARIANCE = 0.30  # 30% variance for other recurring patterns
    
    def __init__(self, min_amount: float = 50.0, min_occurrences: int = 3):
        """
        Initialize the income detector.
        
        Args:
            min_amount: Minimum transaction amount (in currency units) to consider 
                       for income detection. Transactions below this are ignored.
                       Default is £50.
            min_occurrences: Minimum number of similar transactions required to 
                           establish a recurring pattern. Default is 3 for salary classification.
                           
                           **Breaking Change Note**: Changed from 2 to 3 to improve salary
                           detection accuracy and reduce false positives. If you need the
                           previous behavior, explicitly pass min_occurrences=2 when
                           initializing IncomeDetector.
        """
        self.min_amount = min_amount
        self.min_occurrences = min_occurrences
        # Cache for batch analysis - stores recurring income patterns
        self._cached_recurring_sources: List[RecurringIncomeSource] = []
        # Index mapping for O(1) transaction lookup
        self._transaction_index_map: Dict[int, RecurringIncomeSource] = {}
        self._cache_valid = False
    
    def find_recurring_income_sources(
        self, 
        transactions: List[Dict]
    ) -> List[RecurringIncomeSource]:
        """
        [DEPRECATED] Find recurring income sources by analyzing transaction patterns.
        
        This method is no longer used in the simplified PLAID-first approach.
        Returns empty list for backward compatibility only.
        
        Args:
            transactions: List of transaction dictionaries (NOT USED)
        
        Returns:
            Empty list (behavioral detection disabled in Pragmatic Fix)
        """
        return []
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
            
            # Check if amounts are similar
            avg_amount = sum(amounts) / len(amounts)
            
            # Guard against division by zero
            if avg_amount == 0:
                continue
            
            amount_variance = max(abs(a - avg_amount) / avg_amount for a in amounts)
            
            # Calculate frequency (average days between payments)
            if len(dates) >= 2:
                dates_sorted = sorted(dates)
                intervals = []
                for i in range(1, len(dates_sorted)):
                    interval = (dates_sorted[i] - dates_sorted[i-1]).days
                    intervals.append(interval)
                
                avg_interval = sum(intervals) / len(intervals)
                
                # Check if interval matches common pay periods using class constants
                is_weekly = self.WEEKLY_MIN_DAYS <= avg_interval <= self.WEEKLY_MAX_DAYS
                is_fortnightly = self.FORTNIGHTLY_MIN_DAYS <= avg_interval <= self.FORTNIGHTLY_MAX_DAYS
                is_monthly = self.MONTHLY_MIN_DAYS <= avg_interval <= self.MONTHLY_MAX_DAYS
                
                is_regular_interval = is_weekly or is_fortnightly or is_monthly
                
                if not is_regular_interval:
                    continue
                
                # For monthly payments, check for day-of-month consistency (±3 days)
                # This helps detect salary payments on specific days like "15th of month"
                day_of_month_consistent = False
                if is_monthly and len(dates_sorted) >= 3:
                    days_of_month = [d.day for d in dates_sorted]
                    avg_day = sum(days_of_month) / len(days_of_month)
                    day_variance = max(abs(d - avg_day) for d in days_of_month)
                    if day_variance <= 3:  # Within ±3 days
                        day_of_month_consistent = True
                
                # Apply stricter variance threshold for salary-like patterns
                # Use class constants for variance thresholds
                if is_monthly and day_of_month_consistent:
                    # Tight variance for salary-like monthly payments
                    if amount_variance > self.SALARY_TIGHT_VARIANCE:
                        continue
                else:
                    # Standard variance for other recurring payments
                    if amount_variance > self.SALARY_LOOSE_VARIANCE:
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
                avg_interval,
                day_of_month_consistent
            )
            
            recurring_sources.append(RecurringIncomeSource(
                description_pattern=desc_pattern,
                amount_avg=avg_amount,
                amount_std_dev=std_dev,
                frequency_days=avg_interval,
                occurrence_count=len(amounts),
                transaction_indices=indices,
                confidence=confidence,
                source_type=source_type,
                day_of_month_consistent=day_of_month_consistent
            ))
        
        # Sort by confidence (highest first)
        recurring_sources.sort(key=lambda x: x.confidence, reverse=True)
        

    
    def _normalize_description(self, description: str) -> str:
        """
        Normalize transaction description for grouping.
        
        Removes dates, reference numbers, and other variable parts to group
        similar transactions together, while preserving employer context.
        """
        if not description:
            return ""
        
        desc = description.upper().strip()
        
        # Remove common prefixes but preserve the core employer name
        desc = re.sub(r'^(FP-|FASTER PAYMENTS?|BGC|BACS)\s*', '', desc)
        
        # Remove dates (various formats)
        desc = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '', desc)
        desc = re.sub(r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b', '', desc)
        
        # Remove reference numbers (patterns like "REF 123456", "209074 40964700")
        desc = re.sub(r'\bREF\s*\d+\b', '', desc)
        
        # Remove long number sequences BUT preserve short account numbers
        # that might be part of employer name variations
        desc = re.sub(rf'\b\d{{{self.LONG_NUMBER_THRESHOLD},}}\b', '', desc)
        
        # Remove transaction IDs (long alphanumeric sequences)
        desc = re.sub(rf'\b[A-Z0-9]{{{self.LONG_ID_THRESHOLD},}}\b', '', desc)
        
        # Preserve company suffixes (LTD, LIMITED, PLC) as they indicate employer
        # Normalize common variations to group related transactions
        desc = re.sub(r'\bLIMITED\b', 'LTD', desc)
        desc = re.sub(r'\bCORPORATION\b', 'CORP', desc)
        
        # Remove trailing "SALARY", "WAGES", "PAYMENT" keywords to group variations
        # e.g., "BBC MONTHLY SALARY" and "BBC MONTHLY" should match
        desc = re.sub(r'\s+(SALARY|WAGES?|PAYMENT|PAYROLL|PAY)$', '', desc)
        
        # Normalize whitespace
        desc = ' '.join(desc.split())
        
        return desc
    
    def _classify_income_source(
        self, 
        description: str, 
        amount: float, 
        occurrence_count: int,
        frequency_days: float,
        day_of_month_consistent: bool = False
    ) -> Tuple[str, float]:
        """
        [DEPRECATED] Classify income source type and calculate confidence.
        
        This method is no longer used in the simplified PLAID-first approach.
        Returns default values for backward compatibility only.
        
        Args:
            description: NOT USED
            amount: NOT USED
            occurrence_count: NOT USED
            frequency_days: NOT USED
            day_of_month_consistent: NOT USED
        
        Returns:
            Tuple of ("unknown", 0.0) - behavioral classification disabled
        """
        return ("unknown", 0.0)
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
            if (self.WEEKLY_MIN_DAYS <= frequency_days <= self.WEEKLY_MAX_DAYS or 
                self.FORTNIGHTLY_MIN_DAYS <= frequency_days <= self.FORTNIGHTLY_MAX_DAYS):
                return ("salary", min(0.95, base_confidence + 0.25))
            # Monthly salary with consistent day
            elif self.MONTHLY_MIN_DAYS <= frequency_days <= self.MONTHLY_MAX_DAYS:
                if day_of_month_consistent:
                    return ("salary", min(0.95, base_confidence + 0.30))
                return ("salary", min(0.95, base_confidence + 0.20))
            return ("salary", min(0.90, base_confidence + 0.15))
        
        # Check for benefits patterns
        if self.matches_benefit_patterns(description):
            # Benefits are typically monthly
            if self.MONTHLY_MIN_DAYS <= frequency_days <= self.MONTHLY_MAX_DAYS:
                return ("benefits", min(0.95, base_confidence + 0.25))
            return ("benefits", min(0.90, base_confidence + 0.15))
        
        # Check for pension patterns
        if self._matches_pension_patterns(description):
            # Pensions are typically monthly
            if self.MONTHLY_MIN_DAYS <= frequency_days <= self.MONTHLY_MAX_DAYS:
                return ("pension", min(0.95, base_confidence + 0.25))
            return ("pension", min(0.90, base_confidence + 0.15))
        
        # Check for company name patterns (LTD, PLC, etc.)
        if re.search(r'\b(LTD|LIMITED|PLC|CORP|CORPORATION|INC)\b', desc_upper):
            # Likely employer payment
            if self.MONTHLY_MIN_DAYS <= frequency_days <= self.MONTHLY_MAX_DAYS:
                if day_of_month_consistent:
                    # Monthly payment from company with consistent day = very likely salary
                    return ("salary", min(0.90, base_confidence + 0.25))
                return ("salary", min(0.85, base_confidence + 0.15))
            elif self.FORTNIGHTLY_MIN_DAYS <= frequency_days <= self.FORTNIGHTLY_MAX_DAYS:
                return ("salary", min(0.85, base_confidence + 0.15))
            return ("salary", min(0.75, base_confidence + 0.10))
        
        # Behavioral salary detection (no explicit keywords required)
        # Regular payment with reasonable amount (£200+) and monthly cadence with consistent day
        # Note: Tight variance (<= 5%) is already enforced in find_recurring_income_sources()
        # for monthly patterns with day_of_month_consistent=True
        if amount >= 200 and self.MONTHLY_MIN_DAYS <= frequency_days <= self.MONTHLY_MAX_DAYS and day_of_month_consistent:
            # Likely salary even without explicit keywords
            # Behavioral analysis shows tight variance + consistent day = salary pattern
            return ("salary", min(0.95, base_confidence + 0.30))
        
        # Regular fortnightly payment with reasonable amount (£200+)
        # Fortnightly is a common UK salary pattern
        if amount >= 200 and self.FORTNIGHTLY_MIN_DAYS <= frequency_days <= self.FORTNIGHTLY_MAX_DAYS:
            # Likely salary even without explicit keywords
            return ("salary", min(0.90, base_confidence + 0.20))
        
        # Regular weekly payment with reasonable amount (£200+)
        # Weekly is less common for salary but still used
        if amount >= 200 and self.WEEKLY_MIN_DAYS <= frequency_days <= self.WEEKLY_MAX_DAYS:
            return ("salary", min(0.85, base_confidence + 0.15))
        
        # Regular payment with reasonable amount (£200+) and monthly cadence
        if amount >= 200 and self.MONTHLY_MIN_DAYS <= frequency_days <= self.MONTHLY_MAX_DAYS:
            return ("unknown", min(0.70, base_confidence + 0.10))
        

    
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
        Determine if a transaction is likely income using PLAID-first approach.
        
        SIMPLIFIED APPROACH (Pragmatic Fix):
        1. Check PLAID INCOME_WAGES first → return (True, 0.95, "plaid_income_wages")
        2. Check PLAID INCOME category → return (True, 0.85, "plaid_income_general")
        3. Otherwise, fall back to keyword matching in categorization engine
        4. NO behavioral/recurring pattern logic
        
        Args:
            description: Transaction description
            amount: Transaction amount (should be negative for credits)
            plaid_category_primary: PLAID primary category
            plaid_category_detailed: PLAID detailed category
            all_transactions: NOT USED (kept for backward compatibility)
            current_txn_index: NOT USED (kept for backward compatibility)
        
        Returns:
            Tuple of (is_likely_income, confidence, reason)
        """
        if amount >= 0:  # Not a credit
            return (False, 0.0, "not_credit")
        
        # 1. Check PLAID INCOME_WAGES first (highest confidence)
        if plaid_category_detailed:
            detailed_upper = plaid_category_detailed.upper()
            if "INCOME_WAGES" in detailed_upper:
                return (True, 0.95, "plaid_income_wages")
            # Check for other specific income types in detailed category
            if "INCOME" in detailed_upper:
                if "SALARY" in detailed_upper or "PAYROLL" in detailed_upper:
                    return (True, 0.95, "plaid_income_wages")
                elif "BENEFIT" in detailed_upper or "GOVERNMENT" in detailed_upper:
                    return (True, 0.85, "plaid_income_general")
                elif "PENSION" in detailed_upper or "RETIREMENT" in detailed_upper:
                    return (True, 0.85, "plaid_income_general")
                else:
                    return (True, 0.85, "plaid_income_general")
        
        # 2. Check PLAID primary category for INCOME
        if plaid_category_primary:
            if "INCOME" in plaid_category_primary.upper():
                return (True, 0.85, "plaid_income_general")
        
        # 3. Fall back to keyword matching (handled by categorization engine)
        # Return False here to let the engine handle it
        return (False, 0.0, "no_plaid_income")
    
    def analyze_batch(self, transactions: List[Dict]) -> None:
        """
        [DEPRECATED] Analyze a batch of transactions to detect recurring income patterns.
        
        This method is no longer used in the simplified PLAID-first approach.
        Does nothing - kept for backward compatibility only.
        
        Args:
            transactions: List of transaction dictionaries (NOT USED)
        """
        pass
    
    def clear_batch_cache(self) -> None:
        """
        Clear the cached batch analysis results.
        
        Call this when starting analysis of a new batch of transactions.
        """
        self._cached_recurring_sources = []
        self._transaction_index_map = {}
        self._cache_valid = False
    
    def is_likely_income_from_batch(
        self,
        description: str,
        amount: float,
        transaction_index: int,
        plaid_category_primary: Optional[str] = None,
        plaid_category_detailed: Optional[str] = None
    ) -> Tuple[bool, float, str]:
        """
        Determine if a transaction is likely income using PLAID-first approach.
        
        SIMPLIFIED APPROACH (Pragmatic Fix):
        Same as is_likely_income() - no batch-specific logic needed.
        
        Args:
            description: Transaction description
            amount: Transaction amount (should be negative for credits)
            transaction_index: NOT USED (kept for backward compatibility)
            plaid_category_primary: PLAID primary category
            plaid_category_detailed: PLAID detailed category
        
        Returns:
            Tuple of (is_likely_income, confidence, reason)
        """
        # Just delegate to the simplified is_likely_income method
        return self.is_likely_income(
            description=description,
            amount=amount,
            plaid_category_primary=plaid_category_primary,
            plaid_category_detailed=plaid_category_detailed
        )
