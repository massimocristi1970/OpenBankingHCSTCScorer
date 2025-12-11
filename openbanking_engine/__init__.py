"""
OpenBanking HCSTC Scoring Engine - Main Entry Point

A clean, professional module for scoring High-Cost Short-Term Credit (HCSTC) loan
applications using Open Banking transaction data.

Module Structure:
- config/: Configuration for scoring rules and product parameters
- patterns/: Transaction categorization patterns (income, debt, expenses, risk)
- income/: Behavioral income detection
- categorisation/: Transaction categorization orchestration
- scoring/: Feature aggregation and scoring logic

Example Usage:
    >>> from openbanking_engine import run_open_banking_scoring
    >>> result = run_open_banking_scoring(
    ...     transactions=transactions,
    ...     loan_amount=500,
    ...     loan_term=4
    ... )
    >>> print(result.decision)  # APPROVE, REFER, or DECLINE
"""

from typing import Dict, List, Optional

# Import from submodules
from .config import SCORING_CONFIG, PRODUCT_CONFIG
from .patterns import (
    INCOME_PATTERNS,
    TRANSFER_PATTERNS,
    DEBT_PATTERNS,
    ESSENTIAL_PATTERNS,
    RISK_PATTERNS,
    POSITIVE_PATTERNS,
)
from .income import IncomeDetector, RecurringIncomeSource
from .categorisation import TransactionCategorizer, CategoryMatch
from .scoring import (
    Decision,
    RiskLevel,
    ScoreBreakdown,
    LoanOffer,
    ScoringResult,
    ScoringEngine,
    IncomeMetrics,
    ExpenseMetrics,
    DebtMetrics,
    AffordabilityMetrics,
    BalanceMetrics,
    RiskMetrics,
    MetricsCalculator,
)

__version__ = "1.0.0"

__all__ = [
    # Main entry point
    "run_open_banking_scoring",
    # Config
    "SCORING_CONFIG",
    "PRODUCT_CONFIG",
    # Patterns
    "INCOME_PATTERNS",
    "TRANSFER_PATTERNS",
    "DEBT_PATTERNS",
    "ESSENTIAL_PATTERNS",
    "RISK_PATTERNS",
    "POSITIVE_PATTERNS",
    # Income detection
    "IncomeDetector",
    "RecurringIncomeSource",
    # Categorization
    "TransactionCategorizer",
    "CategoryMatch",
    # Scoring
    "Decision",
    "RiskLevel",
    "ScoreBreakdown",
    "LoanOffer",
    "ScoringResult",
    "ScoringEngine",
    "IncomeMetrics",
    "ExpenseMetrics",
    "DebtMetrics",
    "AffordabilityMetrics",
    "BalanceMetrics",
    "RiskMetrics",
    "MetricsCalculator",
]


def run_open_banking_scoring(
    transactions: List[Dict],
    loan_amount: float,
    loan_term: int,
    months_of_data: int = 3,
    application_ref: str = "N/A"
) -> ScoringResult:
    """
    Main entry point for Open Banking HCSTC scoring.
    
    This function orchestrates the complete scoring pipeline:
    1. Categorize all transactions using TransactionCategorizer
    2. Calculate financial metrics using MetricsCalculator
    3. Apply scoring rules and hard declines using ScoringEngine
    4. Return comprehensive scoring result with decision
    
    Args:
        transactions: List of transaction dicts with fields:
            - description (str): Transaction description
            - amount (float): Transaction amount (negative for credits/income)
            - date (str): Transaction date in ISO format
            - merchant_name (str, optional): Merchant name from PLAID
            - plaid_category (str, optional): PLAID detailed category
            - plaid_category_primary (str, optional): PLAID primary category
            - current_balance (float, optional): Account balance after transaction
        loan_amount: Requested loan amount in GBP (£200-£1,500)
        loan_term: Requested loan term in months (3, 4, 5, or 6)
        months_of_data: Number of months of transaction data provided (default 3)
        application_ref: Application reference identifier (default "N/A")
    
    Returns:
        ScoringResult object containing:
            - decision: APPROVE, REFER, or DECLINE
            - score: Overall credit score (0-175)
            - risk_level: LOW, MEDIUM, HIGH, or VERY_HIGH
            - loan_offer: Approved loan details (if approved)
            - score_breakdown: Detailed score components
            - monthly_income: Monthly income estimate
            - monthly_expenses: Monthly expense total
            - monthly_disposable: Disposable income
            - post_loan_disposable: Disposable after loan repayment
            - risk_flags: List of identified risk indicators
            - decline_reasons: List of reasons for decline (if applicable)
            - processing_notes: Additional processing information
    
    Example:
        >>> transactions = [
        ...     {
        ...         "description": "ACME CORP SALARY",
        ...         "amount": -2500.00,
        ...         "date": "2024-01-25",
        ...     },
        ...     {
        ...         "description": "TESCO",
        ...         "amount": 45.20,
        ...         "date": "2024-01-26",
        ...     }
        ... ]
        >>> result = run_open_banking_scoring(
        ...     transactions=transactions,
        ...     loan_amount=500,
        ...     loan_term=4
        ... )
        >>> print(f"Decision: {result.decision}")
        >>> print(f"Score: {result.score}")
    """
    # Step 1: Categorize all transactions
    categorizer = TransactionCategorizer()
    categorized_transactions = []
    
    for txn in transactions:
        category_match = categorizer.categorize_transaction(
            description=txn.get("description", ""),
            amount=txn.get("amount", 0.0),
            merchant_name=txn.get("merchant_name"),
            plaid_category=txn.get("plaid_category"),
            plaid_category_primary=txn.get("plaid_category_primary")
        )
        
        # Add categorization to transaction
        categorized_txn = txn.copy()
        categorized_txn.update({
            "category": category_match.category,
            "subcategory": category_match.subcategory,
            "confidence": category_match.confidence,
            "match_method": category_match.match_method,
            "risk_level": category_match.risk_level,
            "weight": category_match.weight,
            "is_stable": category_match.is_stable,
            "is_housing": category_match.is_housing,
        })
        categorized_transactions.append(categorized_txn)
    
    # Step 2: Calculate financial metrics
    calculator = MetricsCalculator()
    
    # Calculate metrics
    income_metrics = calculator.calculate_income_metrics(
        categorized_transactions,
        months_of_data
    )
    
    expense_metrics = calculator.calculate_expense_metrics(
        categorized_transactions,
        months_of_data
    )
    
    debt_metrics = calculator.calculate_debt_metrics(
        categorized_transactions,
        months_of_data
    )
    
    affordability_metrics = calculator.calculate_affordability_metrics(
        income_metrics,
        expense_metrics,
        debt_metrics,
        loan_amount,
        loan_term
    )
    
    balance_metrics = calculator.calculate_balance_metrics(
        categorized_transactions
    )
    
    risk_metrics = calculator.calculate_risk_metrics(
        categorized_transactions,
        income_metrics.monthly_income
    )
    
    # Step 3: Apply scoring engine
    scoring_engine = ScoringEngine()
    
    result = scoring_engine.score_application(
        application_ref=application_ref,
        loan_amount=loan_amount,
        loan_term=loan_term,
        income_metrics=income_metrics,
        expense_metrics=expense_metrics,
        debt_metrics=debt_metrics,
        affordability_metrics=affordability_metrics,
        balance_metrics=balance_metrics,
        risk_metrics=risk_metrics
    )
    
    return result
