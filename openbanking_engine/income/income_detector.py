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

from sympy import intervals


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
    """Detects income through layered logic: exclusions → PLAID → TRANSFER_IN promotion → recurring patterns → keywords."""

    PAYROLL_KEYWORDS = [
        "SALARY", "WAGES", "PAYROLL", "NET PAY", "WAGE",
        "PAYSLIP", "EMPLOYER", "EMPLOYERS",
        "BGC", "BANK GIRO CREDIT", "CONTRACT PAY", "MONTHLY PAY", "WEEKLY PAY",
        "BACS CREDIT", "FASTER PAYMENT", "FP-",
        "EMPLOYMENT", "PAYCHECK"
    ]

    BENEFIT_KEYWORDS = [
        "UNIVERSAL CREDIT", " UC ", "DWP", "HMRC",
        "CHILD BENEFIT", "PIP", "DLA", "ESA", "JSA",
        "PENSION CREDIT", "HOUSING BENEFIT",
        "TAX CREDIT", "WORKING TAX", "CHILD TAX",
        "CARERS ALLOWANCE", "ATTENDANCE ALLOWANCE",
        "BEREAVEMENT", "MATERNITY ALLOWANCE"
    ]

    PENSION_KEYWORDS = [
        "PENSION", "ANNUITY", "STATE PENSION", "RETIREMENT",
        "NEST", "AVIVA", "LEGAL AND GENERAL", "SCOTTISH WIDOWS",
        "STANDARD LIFE", "PRUDENTIAL", "ROYAL LONDON", "AEGON"
    ]

    EXCLUSION_KEYWORDS = [
        "OWN ACCOUNT", "INTERNAL", "SELF TRANSFER",
        "FROM SAVINGS", "FROM CURRENT", "MOVED FROM",
        "MOVED TO", "BETWEEN ACCOUNTS", "INTERNAL TFR",
        "ISA TRANSFER", "SAVINGS TRANSFER"
    ]

    LOAN_KEYWORDS = [
        "LENDING STREAM", "LENDINGSTREAM", "DRAFTY",
        "MR LENDER", "MRLENDER", "MONEYBOAT", "CREDITSPRING",
        "CASHFLOAT", "QUIDMARKET", "QUID MARKET", "LOANS 2 GO", "LOANS2GO",
        "LOAN DISBURSEMENT", "LOAN ADVANCE",
        "PAYDAY LOAN", "SHORT TERM LOAN",
        "POLAR CREDIT", "118 118 MONEY", "CASHASAP",
        "BAMBOO", "BAMBOO LTD",
        "FERNOVO",
        "OAKBROOK", "OAKBROOK FINANCE", "OAKBROOK FINANCE LIMITED",
        "CREDIT UNION", "CU "

    ]

    LARGE_PAYMENT_THRESHOLD = 500.0

    LONG_NUMBER_THRESHOLD = 8
    LONG_ID_THRESHOLD = 12

    WEEKLY_MIN_DAYS = 5
    WEEKLY_MAX_DAYS = 9
    FORTNIGHTLY_MIN_DAYS = 11
    FORTNIGHTLY_MAX_DAYS = 17
    MONTHLY_MIN_DAYS = 25
    MONTHLY_MAX_DAYS = 35

    SALARY_TIGHT_VARIANCE = 0.05
    SALARY_LOOSE_VARIANCE = 0.30

    def __init__(self, min_amount: float = 50.0, min_occurrences: int = 3):
        self.min_amount = min_amount
        self.min_occurrences = min_occurrences
        self._cached_recurring_sources: List[RecurringIncomeSource] = []
        self._transaction_index_map: Dict[int, RecurringIncomeSource] = {}
        self._cache_valid = False

    # ----------------------------
    # Normalization + keyword tests
    # ----------------------------
    def _normalize_description(self, description: str) -> str:
        if not description:
            return ""

        desc = str(description).upper().strip()

        desc = re.sub(r'^(FP-|FASTER PAYMENTS?|BGC|BACS)\s*', '', desc)

        desc = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '', desc)
        desc = re.sub(r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b', '', desc)

        desc = re.sub(r'\bREF\s*\d+\b', '', desc)
        desc = re.sub(rf'\b\d{{{self.LONG_NUMBER_THRESHOLD},}}\b', '', desc)
        desc = re.sub(rf'\b[A-Z0-9]{{{self.LONG_ID_THRESHOLD},}}\b', '', desc)

        desc = re.sub(r'\bLIMITED\b', 'LTD', desc)
        desc = re.sub(r'\bCORPORATION\b', 'CORP', desc)

        desc = re.sub(r'\s+(SALARY|WAGES?|PAYMENT|PAYROLL|PAY)$', '', desc)
        desc = ' '.join(desc.split())
        return desc

    def matches_payroll_patterns(self, description: str) -> bool:
        if not description:
            return False
        d = description.upper()
        if d.startswith("FP-") or " FP-" in d:
            return True
        return any(k in d for k in self.PAYROLL_KEYWORDS)

    def matches_benefit_patterns(self, description: str) -> bool:
        if not description:
            return False
        d = description.upper()
        return any(k in d for k in self.BENEFIT_KEYWORDS)

    def _matches_pension_patterns(self, description: str) -> bool:
        if not description:
            return False
        d = description.upper()
        return any(k in d for k in self.PENSION_KEYWORDS)

    def _looks_like_internal_transfer(self, description: str) -> bool:
        d = (description or "").upper()
        return any(k in d for k in self.EXCLUSION_KEYWORDS)

    def _looks_like_loan_disbursement(self, description: str, plaid_category_detailed: Optional[str]) -> bool:
        d = (description or "").upper()
        if any(k in d for k in self.LOAN_KEYWORDS):
            return True
        # If PLAID explicitly says transfer-in cash advances / loans, treat as NOT income
        if (plaid_category_detailed or "").upper() == "TRANSFER_IN_CASH_ADVANCES_AND_LOANS":
            return True
        return False

    # ----------------------------
    # Recurring detection
    # ----------------------------
    def find_recurring_income_sources(self, transactions: List[Dict]) -> List[RecurringIncomeSource]:
        income_candidates = []
        for idx, txn in enumerate(transactions):
            amount = txn.get("amount", 0)
            if amount < 0 and abs(amount) >= self.min_amount:
                income_candidates.append((idx, txn))

        if len(income_candidates) < self.min_occurrences:
            return []

        description_groups = defaultdict(list)
        for idx, txn in income_candidates:
            normalized_desc = self._normalize_description(txn.get("name", ""))
            if not normalized_desc:
                continue
            description_groups[normalized_desc].append((idx, txn))

        recurring_sources: List[RecurringIncomeSource] = []

        for desc_pattern, group in description_groups.items():
            if len(group) < self.min_occurrences:
                continue

            amounts = []
            dates = []
            indices = []

            for idx, txn in group:
                a = abs(txn.get("amount", 0))
                ds = txn.get("date", "")
                if not ds:
                    continue
                try:
                    dt = datetime.strptime(ds, "%Y-%m-%d")
                except ValueError:
                    continue
                amounts.append(a)
                dates.append(dt)
                indices.append(idx)

            if len(amounts) < self.min_occurrences or len(dates) < self.min_occurrences:
                continue

            avg_amount = sum(amounts) / len(amounts)
            if avg_amount == 0:
                continue

            amount_variance = max(abs(a - avg_amount) / avg_amount for a in amounts)

            dates_sorted = sorted(dates)
            intervals = [(dates_sorted[i] - dates_sorted[i - 1]).days for i in range(1, len(dates_sorted))]
            if not intervals:
                continue

            avg_interval = sum(intervals) / len(intervals)

            is_weekly = self.WEEKLY_MIN_DAYS <= avg_interval <= self.WEEKLY_MAX_DAYS
            is_fortnightly = self.FORTNIGHTLY_MIN_DAYS <= avg_interval <= self.FORTNIGHTLY_MAX_DAYS
            is_monthly = self.MONTHLY_MIN_DAYS <= avg_interval <= self.MONTHLY_MAX_DAYS

            if not (is_weekly or is_fortnightly or is_monthly):
                continue

            day_of_month_consistent = False
            if is_monthly and len(dates_sorted) >= 3:
                days = [d.day for d in dates_sorted]
                avg_day = sum(days) / len(days)
                day_variance = max(abs(d - avg_day) for d in days)
                if day_variance <= 3:
                    day_of_month_consistent = True

            # enforce variance thresholds
            if is_monthly and day_of_month_consistent:
                if amount_variance > self.SALARY_TIGHT_VARIANCE:
                    continue
            else:
                if amount_variance > self.SALARY_LOOSE_VARIANCE:
                    continue

            # std dev
            variance = sum((a - avg_amount) ** 2 for a in amounts) / len(amounts)
            std_dev = variance ** 0.5

            source_type, confidence = self._classify_income_source(
                description=desc_pattern,
                amount=avg_amount,
                occurrence_count=len(amounts),
                frequency_days=avg_interval,
                day_of_month_consistent=day_of_month_consistent
            )

            if confidence <= 0:
                continue

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

        recurring_sources.sort(key=lambda x: x.confidence, reverse=True)
        return recurring_sources

    def _classify_income_source(
        self,
        description: str,
        amount: float,
        occurrence_count: int,
        frequency_days: float,
        day_of_month_consistent: bool = False
    ) -> Tuple[str, float]:
        desc_upper = (description or "").upper()

        if any(k in desc_upper for k in self.EXCLUSION_KEYWORDS):
            return ("unknown", 0.0)
        if any(k in desc_upper for k in self.LOAN_KEYWORDS):
            return ("unknown", 0.0)

        base_conf = min(0.7, 0.4 + (occurrence_count * 0.1))

        if self.matches_payroll_patterns(description):
            if (self.WEEKLY_MIN_DAYS <= frequency_days <= self.WEEKLY_MAX_DAYS or
                self.FORTNIGHTLY_MIN_DAYS <= frequency_days <= self.FORTNIGHTLY_MAX_DAYS):
                return ("salary", min(0.97, base_conf + 0.27))
            if self.MONTHLY_MIN_DAYS <= frequency_days <= self.MONTHLY_MAX_DAYS:
                if day_of_month_consistent:
                    return ("salary", min(0.97, base_conf + 0.32))
                return ("salary", min(0.95, base_conf + 0.22))
            return ("salary", min(0.92, base_conf + 0.18))

        if self.matches_benefit_patterns(description):
            if self.MONTHLY_MIN_DAYS <= frequency_days <= self.MONTHLY_MAX_DAYS:
                return ("benefits", min(0.95, base_conf + 0.25))
            return ("benefits", min(0.90, base_conf + 0.15))

        if self._matches_pension_patterns(description):
            if self.MONTHLY_MIN_DAYS <= frequency_days <= self.MONTHLY_MAX_DAYS:
                return ("pension", min(0.95, base_conf + 0.25))
            return ("pension", min(0.90, base_conf + 0.15))

        # company suffix heuristic
        if re.search(r"\b(LTD|LIMITED|PLC|LLP|INC|CORP)\b", desc_upper):
            if self.MONTHLY_MIN_DAYS <= frequency_days <= self.MONTHLY_MAX_DAYS:
                if day_of_month_consistent:
                    return ("salary", min(0.90, base_conf + 0.25))
                return ("salary", min(0.85, base_conf + 0.15))
            if self.FORTNIGHTLY_MIN_DAYS <= frequency_days <= self.FORTNIGHTLY_MAX_DAYS:
                return ("salary", min(0.85, base_conf + 0.15))
            return ("salary", min(0.78, base_conf + 0.10))

        # behavioural salary detection without keywords
        if amount >= 200 and self.MONTHLY_MIN_DAYS <= frequency_days <= self.MONTHLY_MAX_DAYS and day_of_month_consistent:
            return ("salary", min(0.95, base_conf + 0.30))
        if amount >= 200 and self.FORTNIGHTLY_MIN_DAYS <= frequency_days <= self.FORTNIGHTLY_MAX_DAYS:
            return ("salary", min(0.90, base_conf + 0.20))
        if amount >= 200 and self.WEEKLY_MIN_DAYS <= frequency_days <= self.WEEKLY_MAX_DAYS:
            return ("salary", min(0.85, base_conf + 0.15))

        return ("unknown", min(0.70, base_conf + 0.10))

    # ----------------------------
    # TRANSFER_IN promotion
    # ----------------------------
    def _is_transfer_in(self, plaid_category_primary: Optional[str], plaid_category_detailed: Optional[str]) -> bool:
        p = (plaid_category_primary or "").upper()
        d = (plaid_category_detailed or "").upper()
        return ("TRANSFER_IN" in p) or d.startswith("TRANSFER_IN")

    def _transfer_in_promotion(
        self,
        description: str,
        amount: float,
        plaid_category_primary: Optional[str],
        plaid_category_detailed: Optional[str],
        all_transactions: Optional[List[Dict]] = None,
        current_txn_index: Optional[int] = None,
    ) -> Tuple[bool, float, str]:
        if amount >= 0:
            return (False, 0.0, "not_credit")
        if not self._is_transfer_in(plaid_category_primary, plaid_category_detailed):
            return (False, 0.0, "not_transfer_in")

        if self._looks_like_internal_transfer(description):
            return (False, 0.0, "transfer_in_excluded_internal")
        if self._looks_like_loan_disbursement(description, plaid_category_detailed):
            return (False, 0.0, "transfer_in_excluded_loan")

        # strong signals
        if self.matches_payroll_patterns(description):
            return (True, 0.94, "transfer_in_promoted_payroll_keyword")
        if self.matches_benefit_patterns(description):
            return (True, 0.88, "transfer_in_promoted_benefit_keyword")
        if self._matches_pension_patterns(description):
            return (True, 0.88, "transfer_in_promoted_pension_keyword")

        # company suffix + meaningful size
        desc = (description or "").upper()
        if re.search(r"\b(LTD|LIMITED|PLC|LLP|INC|CORP)\b", desc) and abs(amount) >= self.LARGE_PAYMENT_THRESHOLD:
            return (True, 0.84, "transfer_in_promoted_company_suffix_large")

        # fallback recurrence check (use batch if provided)
        if all_transactions and current_txn_index is not None:
            try:
                this_norm = self._normalize_description(description)
                this_amt = abs(amount)
                if not this_norm or this_amt <= 0:
                    return (False, 0.0, "transfer_in_not_promoted")

                dates = []
                for i, t in enumerate(all_transactions):
                    if i == current_txn_index:
                        continue
                    a = t.get("amount", 0)
                    if a >= 0:
                        continue
                    if abs(a) < self.min_amount:
                        continue
                    if self._normalize_description(t.get("name", "")) != this_norm:
                        continue
                    if abs(abs(a) - this_amt) / this_amt > 0.25:
                        continue

                    ds = t.get("date")
                    if not ds:
                        continue
                    try:
                        dates.append(datetime.strptime(ds, "%Y-%m-%d"))
                    except ValueError:
                        continue

                if len(dates) >= 2:
                    dates_sorted = sorted(dates)
                    intervals = [(dates_sorted[i] - dates_sorted[i-1]).days for i in range(1, len(dates_sorted))]
                    if intervals:
                        avg = sum(intervals) / len(intervals)
                        if (self.WEEKLY_MIN_DAYS <= avg <= self.WEEKLY_MAX_DAYS or
                            self.FORTNIGHTLY_MIN_DAYS <= avg <= self.FORTNIGHTLY_MAX_DAYS or
                            self.MONTHLY_MIN_DAYS <= avg <= self.MONTHLY_MAX_DAYS):
                            return (True, 0.82, "transfer_in_promoted_recurring_pattern")
            except Exception:
                pass

        return (False, 0.0, "transfer_in_not_promoted")
    


    # ----------------------------
    # Batch cache
    # ----------------------------
    def analyze_batch(self, transactions: List[Dict]) -> None:
        """Build recurring pattern cache for fast per-transaction lookups."""
        self.clear_batch_cache()

        sources = self.find_recurring_income_sources(transactions)
        self._cached_recurring_sources = sources

        idx_map: Dict[int, RecurringIncomeSource] = {}
        for src in sources:
            for idx in src.transaction_indices:
                idx_map[idx] = src

        self._transaction_index_map = idx_map
        self._cache_valid = True

    def clear_batch_cache(self) -> None:
        self._cached_recurring_sources = []
        self._transaction_index_map = {}
        self._cache_valid = False

    # ----------------------------
    # Public API
    # ----------------------------
    def is_likely_income(
        self,
        description: str,
        amount: float,
        plaid_category_primary: Optional[str] = None,
        plaid_category_detailed: Optional[str] = None,
        all_transactions: Optional[List[Dict]] = None,
        current_txn_index: Optional[int] = None
    ) -> Tuple[bool, float, str]:

        # credits only (PLAID uses negative for money-in)
        if amount >= 0:
            return (False, 0.0, "not_credit")

        # hard exclusions first
        if self._looks_like_internal_transfer(description):
            return (False, 0.0, "excluded_internal_transfer")
        if self._looks_like_loan_disbursement(description, plaid_category_detailed):
            return (False, 0.0, "excluded_loan_disbursement")

        # 1) PLAID income is strong
        if plaid_category_detailed:
            d = plaid_category_detailed.upper()
            if "INCOME_WAGES" in d or ("INCOME" in d and ("SALARY" in d or "PAYROLL" in d)):
                return (True, 0.96, "plaid_income_wages")
            if "INCOME" in d:
                return (True, 0.88, "plaid_income_detailed")

        if plaid_category_primary and "INCOME" in plaid_category_primary.upper():
            return (True, 0.86, "plaid_income_primary")

        # 2) Transfer-in promotion (critical for your mislabelled salaries)
        promoted, p_conf, p_reason = self._transfer_in_promotion(
            description=description,
            amount=amount,
            plaid_category_primary=plaid_category_primary,
            plaid_category_detailed=plaid_category_detailed,
            all_transactions=all_transactions,
            current_txn_index=current_txn_index,
        )
        if promoted:
            return (True, p_conf, p_reason)

        # 3) Recurring-pattern support (if we have batch cache)
        if self._cache_valid and current_txn_index is not None:
            src = self._transaction_index_map.get(current_txn_index)
            if src and src.confidence >= 0.80:
                return (True, min(0.92, src.confidence), f"recurring_{src.source_type}")

        # 4) Keyword fallback (rescues remaining misclassified credits)
        if self.matches_payroll_patterns(description):
            return (True, 0.80, "keyword_payroll")
        if self.matches_benefit_patterns(description):
            return (True, 0.75, "keyword_benefits")
        if self._matches_pension_patterns(description):
            return (True, 0.75, "keyword_pension")

        # default
        return (False, 0.0, "no_income_signals")

    def is_likely_income_from_batch(
        self,
        description: str,
        amount: float,
        transaction_index: int,
        plaid_category_primary: Optional[str] = None,
        plaid_category_detailed: Optional[str] = None
    ) -> Tuple[bool, float, str]:
        return self.is_likely_income(
            description=description,
            amount=amount,
            plaid_category_primary=plaid_category_primary,
            plaid_category_detailed=plaid_category_detailed,
            all_transactions=None,                # engine can pass if you wire it
            current_txn_index=transaction_index
        )
    def is_recurring_like(
        self,
        description: str,
        amount: float,
        all_transactions: Optional[List[Dict]],
        current_txn_index: Optional[int],
        min_similar: int = 2,          # "2 other occurrences" = 3 total incl current
        amount_tolerance: float = 0.25 # 25% band
    ) -> bool:
        """
        Returns True if this credit/debit looks recurring based on normalized description,
        similar amount, and cadence roughly weekly/fortnightly/monthly.
        """
        if not all_transactions or current_txn_index is None:
            return False
        this_norm = self._normalize_description(description or "")
        if not this_norm:
            return False

        this_amt = abs(amount)
        if this_amt <= 0:
            return False
        dates = []
        for i, t in enumerate(all_transactions):
            if i == current_txn_index:
                continue
            a = t.get("amount", 0)
            if abs(a) < self.min_amount:
                continue

            # same normalized name
            name = t.get("name", "")
            if self._normalize_description(name) != this_norm:
                continue

            # similar amount
            if abs(abs(a) - this_amt) / this_amt > amount_tolerance:
                continue

            ds = t.get("date")
            if not ds:
                continue
            try:
                dates.append(datetime.strptime(ds, "%Y-%m-%d"))
            except ValueError:
                continue
        # Need at least N similar other occurrences
        if len(dates) < min_similar:
            return False

        dates_sorted = sorted(dates)
        intervals = [(dates_sorted[i] - dates_sorted[i - 1]).days for i in range(1, len(dates_sorted))]
        if not intervals:
            return False

        avg = sum(intervals) / len(intervals)
        is_weekly = self.WEEKLY_MIN_DAYS <= avg <= self.WEEKLY_MAX_DAYS
        is_fortnightly = self.FORTNIGHTLY_MIN_DAYS <= avg <= self.FORTNIGHTLY_MAX_DAYS
        is_monthly = self.MONTHLY_MIN_DAYS <= avg <= self.MONTHLY_MAX_DAYS

        return is_weekly or is_fortnightly or is_monthly
