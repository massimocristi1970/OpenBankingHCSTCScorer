"""
Financial Metrics Calculator for HCSTC Loan Scoring.
Calculates income, expense, debt, affordability, and risk metrics.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from openbanking_engine.categorisation.engine import CategoryMatch
from ..config.scoring_config import PRODUCT_CONFIG


# =========================
# ===== DATA CLASSES ======
# =========================

@dataclass
class IncomeMetrics:
    total_income: float = 0.0
    monthly_income: float = 0.0
    monthly_stable_income: float = 0.0
    monthly_gig_income: float = 0.0
    effective_monthly_income: float = 0.0
    income_stability_score: float = 0.0
    income_regularity_score: float = 0.0
    has_verifiable_income: bool = False
    income_sources: List[str] = field(default_factory=list)
    monthly_income_breakdown: Dict = field(default_factory=dict)


@dataclass
class ExpenseMetrics:
    monthly_housing: float = 0.0
    monthly_council_tax: float = 0.0
    monthly_utilities: float = 0.0
    monthly_transport: float = 0.0
    monthly_groceries: float = 0.0
    monthly_communications: float = 0.0
    monthly_insurance: float = 0.0
    monthly_childcare: float = 0.0
    monthly_essential_total: float = 0.0
    monthly_discretionary_total: float = 0.0
    monthly_total_spend: float = 0.0
    mtd_total_spend: float = 0.0
    mtd_spend_vs_3m_avg_ratio: float = 0.0
    mtd_spend_flag: str = ""
    essential_breakdown: Dict = field(default_factory=dict)


@dataclass
class DebtMetrics:
    monthly_debt_payments: float = 0.0
    monthly_hcstc_payments: float = 0.0
    active_hcstc_count: int = 0
    active_hcstc_count_90d: int = 0
    monthly_bnpl_payments: float = 0.0
    monthly_credit_card_payments: float = 0.0
    monthly_other_loan_payments: float = 0.0
    total_debt_commitments: float = 0.0
    debt_breakdown: Dict = field(default_factory=dict)


@dataclass
class AffordabilityMetrics:
    debt_to_income_ratio: float = 0.0
    essential_ratio: float = 0.0
    monthly_disposable: float = 0.0
    disposable_ratio: float = 0.0
    proposed_repayment: float = 0.0
    post_loan_disposable: float = 0.0
    repayment_to_disposable_ratio: float = 0.0
    is_affordable: bool = False
    max_affordable_amount: float = 0.0


@dataclass
class BalanceMetrics:
    average_balance: float = 0.0
    minimum_balance: float = 0.0
    maximum_balance: float = 0.0
    days_in_overdraft: int = 0
    overdraft_frequency: int = 0
    end_of_month_average: float = 0.0


@dataclass
class RiskMetrics:
    gambling_total: float = 0.0
    gambling_percentage: float = 0.0
    gambling_frequency: int = 0
    failed_payments_count: int = 0
    failed_payments_count_45d: int = 0
    debt_collection_activity: int = 0
    debt_collection_distinct: int = 0
    bank_charges_count: int = 0
    bank_charges_count_90d: int = 0
    new_credit_providers_90d: int = 0
    savings_activity: float = 0.0
    has_gambling_concern: bool = False
    has_failed_payment_concern: bool = False
    has_debt_collection_concern: bool = False
    has_bank_charges_concern: bool = False
    has_new_credit_burst: bool = False


# ===============================
# ===== METRICS CALCULATOR ======
# ===============================

class MetricsCalculator:
    """Calculates financial metrics from categorized transactions."""

    def __init__(self, lookback_months: int = 3):
        self.lookback_months = lookback_months
        self.months_of_data = lookback_months  # ← restore expected attribute
        self.product_config = PRODUCT_CONFIG


    # ========= STEP A FIX =========
    def _count_unique_months(self, transactions: List[Dict]) -> int:
        """
        Count distinct (year, month) pairs in a transaction list.
        Used to normalise monthly income correctly.
        """
        months = set()
        for txn in transactions:
            date_str = txn.get("date")
            if not date_str:
                continue
            try:
                dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                months.add((dt.year, dt.month))
            except Exception:
                continue
        return max(1, len(months))
    # ==============================

    def calculate_income_metrics(
        self,
        category_summary: Dict,
        transactions: List[Dict]
    ) -> IncomeMetrics:
        """
        Calculate income-related metrics from recent income transactions.
        """

        income_data = category_summary.get("income", {})

        salary_total = income_data.get("salary", {}).get("total", 0.0)
        benefits_total = income_data.get("benefits", {}).get("total", 0.0)
        pension_total = income_data.get("pension", {}).get("total", 0.0)
        gig_total = income_data.get("gig_economy", {}).get("total", 0.0)
        other_total = income_data.get("other", {}).get("total", 0.0)

        total_income = salary_total + benefits_total + pension_total + gig_total + other_total

        # ✅ CORRECT: divide by ACTUAL income months
        actual_months = self._count_unique_months(transactions)

        monthly_stable = (salary_total + benefits_total + pension_total) / actual_months
        monthly_gig = gig_total / actual_months
        monthly_other = other_total / actual_months
        monthly_income = total_income / actual_months

        effective_monthly = monthly_stable + monthly_gig + monthly_other

        stability_score = self._calculate_income_stability(transactions)
        regularity_score = self._calculate_income_regularity(transactions)

        income_sources = []
        if salary_total > 0:
            income_sources.append("Salary")
        if benefits_total > 0:
            income_sources.append("Benefits")
        if pension_total > 0:
            income_sources.append("Pension")
        if gig_total > 0:
            income_sources.append("Gig Economy")

        has_verifiable = salary_total > 0 or benefits_total > 0 or pension_total > 0

        return IncomeMetrics(
            total_income=total_income,
            monthly_income=monthly_income,
            monthly_stable_income=monthly_stable,
            monthly_gig_income=monthly_gig,
            effective_monthly_income=effective_monthly,
            income_stability_score=stability_score,
            income_regularity_score=regularity_score,
            has_verifiable_income=has_verifiable,
            income_sources=income_sources,
            monthly_income_breakdown={
                "salary": salary_total / actual_months,
                "benefits": benefits_total / actual_months,
                "pension": pension_total / actual_months,
                "gig_economy": monthly_gig,
                "other": monthly_other,
            }
        )

        
    def _calculate_income_stability(self, transactions: List[Dict]) -> float:
        """
        Calculate income stability score based on standard deviation.
        
        Score = 100 - (StdDev / Mean * 100)
        """
        # Group income by month
        monthly_income = defaultdict(float)
        
        for txn in transactions:
            amount = txn.get("amount", 0)
            if amount >= 0:  # Not income
                continue
            
            date_str = txn.get("date", "")
            if not date_str:
                continue
            
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                month_key = date.strftime("%Y-%m")
                monthly_income[month_key] += abs(amount)
            except (ValueError, TypeError):
                continue
        
        if len(monthly_income) < 2:
            return 50.0  # Default if insufficient data
        
        values = list(monthly_income.values())
        mean_income = statistics.mean(values)
        
        if mean_income == 0:
            return 0.0
        
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        coefficient_of_variation = (std_dev / mean_income) * 100
        
        # Score calculation: 100 - CV, clamped to 0-100
        stability_score = max(0, min(100, 100 - coefficient_of_variation))
        
        return round(stability_score, 1)
    
    def _calculate_income_regularity(self, transactions: List[Dict]) -> float:
        """
        Calculate income regularity based on payment day consistency.
        
        Higher score = more consistent payment days
        """
        # Find income transactions and their days
        income_days = []
        
        for txn in transactions:
            amount = txn.get("amount", 0)
            if amount >= 0:  # Not income
                continue
            
            # Only consider larger payments (likely salary/benefits)
            if abs(amount) < 100:
                continue
            
            date_str = txn.get("date", "")
            if not date_str:
                continue
            
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                income_days.append(date.day)
            except (ValueError, TypeError):
                continue
        
        if len(income_days) < 2:
            return 50.0  # Default if insufficient data
        
        # Calculate standard deviation of payment days
        std_dev = statistics.stdev(income_days) if len(income_days) > 1 else 0
        
        # Score: Lower std_dev = higher score
        # Max regularity if std_dev <= 2 days
        if std_dev <= 2:
            return 100.0
        elif std_dev <= 5:
            return 80.0
        elif std_dev <= 10:
            return 60.0
        elif std_dev <= 15:
            return 40.0
        else:
            return 20.0
    
    def calculate_expense_metrics(
        self, 
        category_summary: Dict,
        transactions: Optional[List[Dict]] = None,
        mtd_category_summary: Optional[Dict] = None,
        mtd_transactions: Optional[List[Dict]] = None,
    ) -> ExpenseMetrics:
        """
        Calculate expense-related metrics from recent transactions.
    
        Args:
            category_summary: Category summary (should be from filtered transactions)
            transactions: Recent transactions list (for calculating actual months)
    
        Returns:
            ExpenseMetrics with monthly expense averages
        """
        essential_data = category_summary.get("essential", {})
        debt_data = category_summary.get("debt", {})
        expense_data = category_summary.get("expense", {})
    
        # Calculate actual months in the filtered period
        # Use lookback_months as the period since we're working with filtered data
        actual_months = self.lookback_months
    
        # Get monthly averages based on actual months in filtered period
        rent = essential_data.get("rent", {}).get("total", 0) / actual_months
        mortgage = essential_data.get("mortgage", {}).get("total", 0) / actual_months
        council_tax = essential_data.get("council_tax", {}).get("total", 0) / actual_months
        utilities = essential_data.get("utilities", {}).get("total", 0) / actual_months
        transport = essential_data.get("transport", {}).get("total", 0) / actual_months
        groceries = essential_data.get("groceries", {}).get("total", 0) / actual_months
        communications = essential_data.get("communications", {}).get("total", 0) / actual_months
        insurance = essential_data.get("insurance", {}).get("total", 0) / actual_months
        childcare = essential_data.get("childcare", {}).get("total", 0) / actual_months
    
        # Add other expenses that aren't in "essential" category
        other_expenses = expense_data.get("other", {}).get("total", 0) / actual_months
        food_dining = expense_data.get("food_dining", {}).get("total", 0) / actual_months
        discretionary = expense_data.get("discretionary", {}).get("total", 0) / actual_months
        
        # New expense subcategories
        unpaid = expense_data.get("unpaid", {}).get("total", 0) / actual_months
        unauthorised_overdraft = expense_data.get("unauthorised_overdraft", {}).get("total", 0) / actual_months
        gambling = expense_data.get("gambling", {}).get("total", 0) / actual_months

        # Get monthly averages - debt category
        hcstc = debt_data.get("hcstc_payday", {}).get("total", 0) / actual_months
        other_loans = debt_data.get("other_loans", {}).get("total", 0) / actual_months
        credit_cards = debt_data.get("credit_cards", {}).get("total", 0) / actual_months
        bnpl = debt_data.get("bnpl", {}).get("total", 0) / actual_months
        catalogue = debt_data.get("catalogue", {}).get("total", 0) / actual_months
    
        # Housing is rent OR mortgage (not both)
        housing = max(rent, mortgage)
    
        # Essential costs (fixed/necessary spend)
        # Include unpaid + unauthorised_overdraft as essential-like spend
        essential_total = (
            housing + council_tax + utilities + transport +
            groceries + communications + insurance + childcare +
            other_expenses + food_dining +
            unpaid + unauthorised_overdraft
        )

        # Discretionary costs (separate bucket)
        # Include gambling as discretionary-like spend
        discretionary_total = discretionary + gambling

        # Total spend used for affordability
        monthly_total_spend = essential_total + discretionary_total

    
        # --- Optional month-to-date (MTD) spend trend flag (NOT part of the averages) ---
        mtd_total_spend = 0.0
        mtd_ratio = 0.0
        mtd_flag = ""

        try:
            # Baseline: average monthly spend over the lookback window (3 complete months)
            discretionary_total_period = 0.0
            for sub, data in category_summary.get("expense", {}).items():
                discretionary_total_period += abs(float(data.get("total", 0.0)))

            monthly_discretionary = discretionary_total_period / max(self.lookback_months, 1)
            baseline_monthly_spend = essential_total + monthly_discretionary

            if mtd_category_summary:
                # MTD spend uses the same "spend" basket, excluding debt/transfers
                for cat in ("essential", "expense", "risk"):
                    for sub, data in mtd_category_summary.get(cat, {}).items():
                        mtd_total_spend += abs(float(data.get("total", 0.0)))

                if baseline_monthly_spend > 0:
                    mtd_ratio = mtd_total_spend / baseline_monthly_spend

                # Simple, explainable flag
                if mtd_ratio >= 1.25:
                    mtd_flag = "MTD spending running HIGH vs 3-month average"
                elif mtd_ratio <= 0.75 and mtd_total_spend > 0:
                    mtd_flag = "MTD spending running LOW vs 3-month average"
        except Exception:
            # Never fail expense metrics because of the optional trend flag
            mtd_total_spend = 0.0
            mtd_ratio = 0.0
            mtd_flag = ""
            
        return ExpenseMetrics(
            monthly_housing=housing,
            monthly_council_tax=council_tax,
            monthly_utilities=utilities,
            monthly_transport=transport,
            monthly_groceries=groceries,
            monthly_communications=communications,
            monthly_insurance=insurance,
            monthly_childcare=childcare,
            monthly_essential_total=essential_total,
            monthly_discretionary_total=discretionary_total,
            monthly_total_spend=monthly_total_spend,
            mtd_total_spend=mtd_total_spend,
            mtd_spend_vs_3m_avg_ratio=mtd_ratio,
            mtd_spend_flag=mtd_flag,
            essential_breakdown={
                "housing": housing,
                "council_tax":  council_tax,
                "utilities": utilities,
                "transport":  transport,
                "groceries":  groceries,
                "communications":  communications,
                "insurance": insurance,
                "childcare": childcare,
                "other_expenses": other_expenses,
                "food_dining": food_dining,
                "unpaid": unpaid,
                "unauthorised_overdraft": unauthorised_overdraft,
                "discretionary": discretionary,
                "gambling": gambling,
                "debt_payments": hcstc + other_loans + credit_cards + bnpl + catalogue,
            }
        )
    
    def calculate_debt_metrics(self, category_summary: Dict) -> DebtMetrics:
        """Calculate debt-related metrics."""
        debt_data = category_summary.get("debt", {})
        
        # Get monthly averages
        hcstc = debt_data.get("hcstc_payday", {}).get("total", 0) / self.months_of_data
        other_loans = debt_data.get("other_loans", {}).get("total", 0) / self.months_of_data
        credit_cards = debt_data.get("credit_cards", {}).get("total", 0) / self.months_of_data
        bnpl = debt_data.get("bnpl", {}).get("total", 0) / self.months_of_data
        catalogue = debt_data.get("catalogue", {}).get("total", 0) / self.months_of_data
        
        # Active HCSTC lender count (all time and 90 days)
        active_hcstc_count = debt_data.get("hcstc_payday", {}).get("distinct_lenders", 0)
        active_hcstc_count_90d = debt_data.get("hcstc_payday", {}).get("distinct_lenders_90d", 0)
        
        # Total debt commitments
        total_debt = hcstc + other_loans + credit_cards + bnpl + catalogue
        
        return DebtMetrics(
            monthly_debt_payments=total_debt,
            monthly_hcstc_payments=hcstc,
            active_hcstc_count=active_hcstc_count,
            active_hcstc_count_90d=active_hcstc_count_90d,
            monthly_bnpl_payments=bnpl,
            monthly_credit_card_payments=credit_cards,
            monthly_other_loan_payments=other_loans + catalogue,
            total_debt_commitments=total_debt,
            debt_breakdown={
                "hcstc": hcstc,
                "other_loans": other_loans,
                "credit_cards": credit_cards,
                "bnpl": bnpl,
                "catalogue": catalogue,
            }
        )
    
    def calculate_affordability_metrics(
        self,
        income_metrics: IncomeMetrics,
        expense_metrics: ExpenseMetrics,
        debt_metrics: DebtMetrics,
        loan_amount: float,
        loan_term: int
    ) -> AffordabilityMetrics:
        """Calculate affordability metrics."""
        
        effective_income = income_metrics.effective_monthly_income or 0.0
        total_spend = expense_metrics.monthly_total_spend or 0.0
        debt_payments = debt_metrics.monthly_debt_payments or 0.0
        
        # Apply expense shock buffer for income/expenses resilience assessment
        # This buffer (default 10%) accounts for potential increases in expenses
        # or temporary reductions in income, improving the robustness of 
        # affordability calculations and reducing default risk.
        expense_buffer = self.product_config.get("expense_shock_buffer", 1.1)
        essential_costs = expense_metrics.monthly_essential_total or 0.0
        discretionary_costs = expense_metrics.monthly_discretionary_total or 0.0
        buffered_expenses = (essential_costs * expense_buffer) + discretionary_costs


        
        # Debt-to-Income Ratio
        if effective_income > 0:
            dti_ratio = (debt_payments / effective_income) * 100
        else:
            dti_ratio = 100.0
        
        # Essential Ratio (using buffered expenses)
        if effective_income > 0:
            essential_ratio = (buffered_expenses / effective_income) * 100
        else:
            essential_ratio = 100.0
        
        # Disposable Income (using buffered expenses)
        monthly_disposable = effective_income - buffered_expenses - debt_payments
        
        # Disposable Ratio
        if effective_income > 0:
            disposable_ratio = (monthly_disposable / effective_income) * 100
        else:
            disposable_ratio = 0.0
        
        # Calculate proposed loan repayment
        # Monthly payment with FCA price cap (0.8% per day)
        daily_rate = self.product_config["daily_interest_rate"]
        days_per_month = 30.4  # Average days per month
        monthly_rate = daily_rate * days_per_month
        
        # Total interest capped at 100%
        total_interest = min(
            loan_amount * monthly_rate * loan_term,
            loan_amount * self.product_config["total_cost_cap"]
        )
        
        total_repayable = loan_amount + total_interest
        proposed_repayment = total_repayable / loan_term
        
        # Post-loan disposable
        post_loan_disposable = monthly_disposable - proposed_repayment

        print(
            f"[AFFORDABILITY] "
            f"Income £{effective_income:.2f} | "
            f"Expenses £{expense_metrics.monthly_total_spend:.2f} | "
            f"Debt £{debt_payments:.2f} | "
            f"Repayment £{proposed_repayment:.2f} | "
            f"Post-loan £{post_loan_disposable:.2f}"
        )


        # Repayment-to-disposable ratio (MI / reporting ONLY)
        if monthly_disposable > 0:
            repayment_to_disp = (proposed_repayment / monthly_disposable) * 100
        else:
            repayment_to_disp = 100.0

        # Minimum disposable buffer (single source of truth)
        min_buffer = self.product_config["min_disposable_buffer"]

        # Affordability decision
        # NOTE: repayment_to_disp is NOT used here
        is_affordable = (
            post_loan_disposable >= min_buffer
        )

        # Calculate max affordable amount
        max_affordable = self._calculate_max_affordable_amount(
            monthly_disposable=monthly_disposable,
            min_buffer=min_buffer,
            max_term=loan_term
        )
        
        return AffordabilityMetrics(
            debt_to_income_ratio=round(dti_ratio, 1),
            essential_ratio=round(essential_ratio, 1),
            monthly_disposable=round(monthly_disposable, 2),
            disposable_ratio=round(disposable_ratio, 1),
            proposed_repayment=round(proposed_repayment, 2),
            post_loan_disposable=round(post_loan_disposable, 2),
            repayment_to_disposable_ratio=round(repayment_to_disp, 1),
            is_affordable=is_affordable,
            max_affordable_amount=round(max_affordable, 2)
        )
    
    def _calculate_max_affordable_amount(
        self,
        monthly_disposable: float,
        min_buffer: float,
        max_term: int
    ) -> float:
        """Calculate maximum affordable loan amount."""
        # Max monthly payment = disposable - buffer
        monthly_disposable = monthly_disposable or 0.0
        max_monthly_payment = monthly_disposable - min_buffer
        
        if max_monthly_payment <= 0:
            return 0.0
        
        # Calculate max loan amount
        daily_rate = self.product_config["daily_interest_rate"]
        days_per_month = 30.4
        monthly_rate = daily_rate * days_per_month
        
        # Solve for principal: payment = (principal + principal * rate * term) / term
        # payment * term = principal * (1 + rate * term)
        # principal = payment * term / (1 + rate * term)
        total_payments = max_monthly_payment * max_term
        interest_factor = 1 + (monthly_rate * max_term)
        
        # Cap interest at 100%
        interest_factor = min(interest_factor, 2.0)  # Max 100% interest = factor of 2
        
        max_amount = total_payments / interest_factor
        
        # Cap at product maximum
        return min(max_amount, self.product_config["max_loan_amount"])
    
    def calculate_balance_metrics(
        self, 
        transactions: List[Dict],
        accounts: List[Dict]
    ) -> BalanceMetrics:
        """Calculate account balance metrics."""
        
        # Try to get balance from accounts
        balances = []
        for account in accounts:
            account_balances = account.get("balances", {})
            current = account_balances.get("current", 0) or 0.0
            available = account_balances.get("available", 0) or 0.0
            balances.append(max(current, available))
        
        # Calculate daily balances from transactions
        daily_balances = self._calculate_daily_balances(transactions, accounts)
        
        if daily_balances:
            avg_balance = statistics.mean(daily_balances)
            min_balance = min(daily_balances)
            max_balance = max(daily_balances)
            days_negative = sum(1 for b in daily_balances if b < 0)
            
            # Count times balance went from positive to negative
            overdraft_count = 0
            for i in range(1, len(daily_balances)):
                if daily_balances[i-1] >= 0 and daily_balances[i] < 0:
                    overdraft_count += 1
        else:
            avg_balance = sum(balances) / len(balances) if balances else 0
            min_balance = min(balances) if balances else 0
            max_balance = max(balances) if balances else 0
            days_negative = 0
            overdraft_count = 0
        
        return BalanceMetrics(
            average_balance=round(avg_balance, 2),
            minimum_balance=round(min_balance, 2),
            maximum_balance=round(max_balance, 2),
            days_in_overdraft=days_negative,
            overdraft_frequency=overdraft_count,
            end_of_month_average=round(avg_balance, 2)  # Simplified
        )
    
    def _calculate_daily_balances(
        self, 
        transactions: List[Dict],
        accounts: List[Dict]
    ) -> List[float]:
        """Calculate estimated daily balances from transactions."""
        # Get starting balance from accounts
        starting_balance = 0
        for account in accounts:
            balances = account.get("balances", {})
            starting_balance += balances.get("current", 0) or 0.0
        
        # Sort transactions by date
        sorted_txns = sorted(
            transactions,
            key=lambda x: x.get("date", "9999-99-99"),
            reverse=True  # Most recent first
        )
        
        if not sorted_txns:
            return [starting_balance]
        
        # Work backwards from current balance
        daily_balances = defaultdict(float)
        current_balance = starting_balance
        
        for txn in sorted_txns:
            date_str = txn.get("date", "")
            amount = txn.get("amount", 0)
            
            if not date_str:
                continue
            
            daily_balances[date_str] = current_balance
            # Reverse the transaction to get previous balance.
            # In PLAID: negative = credit (money in), positive = debit (money out).
            # To reverse: subtract the effect, so add the amount back.
            # Credit (negative): subtracting a negative adds money.
            # Debit (positive): subtracting a positive removes money.
            # Since we're working backwards from current, we add the amount.
            current_balance = current_balance + amount
        
        return list(daily_balances.values()) if daily_balances else [starting_balance]
    
    def calculate_risk_metrics(
        self, 
        category_summary: Dict,
        income_metrics: IncomeMetrics
    ) -> RiskMetrics:
        """Calculate risk indicator metrics."""
        risk_data = category_summary.get("risk", {})
        positive_data = category_summary.get("positive", {})
        
        # Gambling metrics
        gambling_total = risk_data.get("gambling", {}).get("total", 0)
        gambling_count = risk_data.get("gambling", {}).get("count", 0)
        
        total_income = income_metrics.total_income or 0.0
        if total_income > 0:
            gambling_pct = (gambling_total / total_income) * 100
        else:
            gambling_pct = 0.0
        
        # Failed payments (all time and 45 days)
        failed_count = risk_data.get("failed_payments", {}).get("count", 0)
        failed_count_45d = risk_data.get("failed_payments", {}).get("count_45d", 0)
        
        # Bank charges (all time and 90 days)
        bank_charges_count = risk_data.get("bank_charges", {}).get("count", 0)
        bank_charges_count_90d = risk_data.get("bank_charges", {}).get("count_90d", 0)
        
        # Debt collection
        dca_count = risk_data.get("debt_collection", {}).get("count", 0)
        dca_distinct = risk_data.get("debt_collection", {}).get("distinct_dcas", 0)
        
        # New credit providers in last 90 days
        debt_data = category_summary.get("debt", {})
        new_credit_providers_90d = debt_data.get("hcstc_payday", {}).get("new_credit_providers_90d", 0)
        
        # Savings activity
        savings_total = positive_data.get("savings", {}).get("total", 0)
        
        # Concern flags
        has_gambling_concern = gambling_pct > 5 or gambling_count > 5
        has_failed_payment_concern = failed_count >= 3
        has_dca_concern = dca_distinct >= 2
        has_bank_charges_concern = bank_charges_count_90d > 2  # Allow 1-2 bank charges without referral
        has_new_credit_burst = new_credit_providers_90d >= 5  # Allow up to 4 new credit providers without referral
        
        return RiskMetrics(
            gambling_total=round(gambling_total, 2),
            gambling_percentage=round(gambling_pct, 1),
            gambling_frequency=gambling_count,
            failed_payments_count=failed_count,
            failed_payments_count_45d=failed_count_45d,
            debt_collection_activity=dca_count,
            debt_collection_distinct=dca_distinct,
            bank_charges_count=bank_charges_count,
            bank_charges_count_90d=bank_charges_count_90d,
            new_credit_providers_90d=new_credit_providers_90d,
            savings_activity=round(savings_total, 2),
            has_gambling_concern=has_gambling_concern,
            has_failed_payment_concern=has_failed_payment_concern,
            has_debt_collection_concern=has_dca_concern,
            has_bank_charges_concern=has_bank_charges_concern,
            has_new_credit_burst=has_new_credit_burst
        )