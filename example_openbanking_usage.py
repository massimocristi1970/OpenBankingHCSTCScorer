"""
Example usage of the OpenBanking Engine.

This example demonstrates how to use the new openbanking_engine module
to score loan applications using Open Banking transaction data.
"""

from openbanking_engine import run_open_banking_scoring

def example_basic_usage():
    """Basic example using the main entry point."""
    print("=" * 80)
    print("Example 1: Basic Usage with run_open_banking_scoring()")
    print("=" * 80)
    
    # Sample transactions for a typical applicant
    transactions = [
        # Monthly salary
        {"description": "ACME CORP SALARY", "amount": -2500.00, "date": "2024-01-25"},
        {"description": "ACME CORP SALARY", "amount": -2500.00, "date": "2024-02-25"},
        {"description": "ACME CORP SALARY", "amount": -2500.00, "date": "2024-03-25"},
        
        # Rent payments
        {"description": "LANDLORD RENT", "amount": 850.00, "date": "2024-01-01"},
        {"description": "LANDLORD RENT", "amount": 850.00, "date": "2024-02-01"},
        {"description": "LANDLORD RENT", "amount": 850.00, "date": "2024-03-01"},
        
        # Utilities
        {"description": "BRITISH GAS", "amount": 65.00, "date": "2024-01-15"},
        {"description": "BRITISH GAS", "amount": 68.00, "date": "2024-02-15"},
        {"description": "BRITISH GAS", "amount": 62.00, "date": "2024-03-15"},
        
        # Groceries
        {"description": "TESCO STORES", "amount": 120.50, "date": "2024-01-05"},
        {"description": "TESCO STORES", "amount": 135.20, "date": "2024-01-12"},
        {"description": "TESCO STORES", "amount": 145.80, "date": "2024-01-19"},
        {"description": "SAINSBURYS", "amount": 98.40, "date": "2024-02-08"},
        {"description": "TESCO STORES", "amount": 112.30, "date": "2024-02-15"},
        
        # Transport
        {"description": "SHELL PETROL", "amount": 45.00, "date": "2024-01-10"},
        {"description": "TFL OYSTER", "amount": 35.00, "date": "2024-01-20"},
    ]
    
    # Score the application
    result = run_open_banking_scoring(
        transactions=transactions,
        loan_amount=500,
        loan_term=4,
        months_of_data=3,
        application_ref="EXAMPLE-001"
    )
    
    # Display results
    print(f"\nApplication Reference: {result.application_ref}")
    print(f"Decision: {result.decision.value}")
    print(f"Score: {result.score:.2f} / 175")
    print(f"Risk Level: {result.risk_level.value}")
    print(f"\nFinancial Summary:")
    print(f"  Monthly Income:     £{result.monthly_income:,.2f}")
    print(f"  Monthly Expenses:   £{result.monthly_expenses:,.2f}")
    print(f"  Disposable Income:  £{result.monthly_disposable:,.2f}")
    print(f"  Post-Loan Disposable: £{result.post_loan_disposable:,.2f}")
    
    if result.loan_offer:
        print(f"\nLoan Offer:")
        print(f"  Approved Amount:    £{result.loan_offer.approved_amount:,.2f}")
        print(f"  Term:               {result.loan_offer.approved_term} months")
        print(f"  Monthly Repayment:  £{result.loan_offer.monthly_repayment:,.2f}")
        print(f"  Total Repayable:    £{result.loan_offer.total_repayable:,.2f}")
        print(f"  APR:                {result.loan_offer.apr:.1f}%")
    
    if result.decline_reasons:
        print(f"\nDecline Reasons:")
        for reason in result.decline_reasons:
            print(f"  - {reason}")
    
    if result.risk_flags:
        print(f"\nRisk Flags:")
        for flag in result.risk_flags:
            print(f"  - {flag}")
    
    print()


def example_advanced_usage():
    """Advanced example using individual components."""
    print("=" * 80)
    print("Example 2: Advanced Usage with Individual Components")
    print("=" * 80)
    
    from openbanking_engine.categorisation import TransactionCategorizer
    from openbanking_engine.scoring import MetricsCalculator, ScoringEngine
    
    # Sample transactions
    transactions = [
        {"name": "EMPLOYER SALARY", "amount": -3000.00, "date": "2024-01-25"},
        {"name": "TESCO", "amount": 150.00, "date": "2024-01-26"},
        {"name": "RENT", "amount": 900.00, "date": "2024-01-28"},
    ]
    
    # Step 1: Categorize transactions
    print("\nStep 1: Transaction Categorization")
    categorizer = TransactionCategorizer()
    categorized = categorizer.categorize_transactions(transactions)
    
    for txn, match in categorized:
        print(f"  {txn['name']:30s} → {match.category}/{match.subcategory} "
              f"(confidence: {match.confidence:.2f}, method: {match.match_method})")
    
    # Step 2: Generate category summary
    print("\nStep 2: Category Summary")
    category_summary = categorizer.get_category_summary(categorized)
    
    income_total = sum(
        cat_data.get("total", 0) 
        for cat_data in category_summary.get("income", {}).values()
        if isinstance(cat_data, dict)
    )
    print(f"  Total Income: £{abs(income_total):,.2f}")
    
    # Step 3: Calculate metrics
    print("\nStep 3: Financial Metrics")
    calculator = MetricsCalculator(months_of_data=3)
    metrics = calculator.calculate_all_metrics(
        category_summary=category_summary,
        transactions=transactions,
        accounts=[],
        loan_amount=500,
        loan_term=4
    )
    
    print(f"  Monthly Income:    £{metrics['income'].monthly_income:,.2f}")
    print(f"  Monthly Expenses:  £{metrics['expenses'].monthly_essential_total:,.2f}")
    print(f"  Disposable:        £{metrics['affordability'].monthly_disposable:,.2f}")
    
    # Step 4: Score application
    print("\nStep 4: Scoring")
    engine = ScoringEngine()
    result = engine.score_application(
        metrics=metrics,
        requested_amount=500,
        requested_term=4,
        application_ref="EXAMPLE-002"
    )
    
    print(f"  Decision: {result.decision.value}")
    print(f"  Score: {result.score:.2f}")
    print()


def example_configuration():
    """Example showing configuration access."""
    print("=" * 80)
    print("Example 3: Configuration Access")
    print("=" * 80)
    
    from openbanking_engine.config import SCORING_CONFIG, PRODUCT_CONFIG
    from openbanking_engine.patterns import INCOME_PATTERNS, DEBT_PATTERNS
    
    print("\nProduct Configuration:")
    print(f"  Min Loan:       £{PRODUCT_CONFIG['min_loan_amount']:,}")
    print(f"  Max Loan:       £{PRODUCT_CONFIG['max_loan_amount']:,}")
    print(f"  Available Terms: {PRODUCT_CONFIG['available_terms']}")
    print(f"  Daily Interest:  {PRODUCT_CONFIG['daily_interest_rate'] * 100}%")
    
    print("\nScoring Configuration:")
    hard_declines = SCORING_CONFIG['hard_decline_rules']
    print(f"  Min Monthly Income:      £{hard_declines['min_monthly_income']:,}")
    print(f"  Max Active HCSTC:        {hard_declines['max_active_hcstc_lenders']}")
    print(f"  Max Gambling %:          {hard_declines['max_gambling_percentage']}%")
    print(f"  Max Failed Payments:     {hard_declines['max_failed_payments']}")
    
    print("\nIncome Pattern Examples:")
    salary_keywords = INCOME_PATTERNS['salary']['keywords'][:5]
    print(f"  Salary Keywords: {', '.join(salary_keywords)}")
    
    print("\nDebt Pattern Examples:")
    hcstc_lenders = DEBT_PATTERNS['hcstc_payday']['keywords'][:5]
    print(f"  HCSTC Lenders: {', '.join(hcstc_lenders)}")
    print()


if __name__ == "__main__":
    # Run all examples
    example_basic_usage()
    example_advanced_usage()
    example_configuration()
    
    print("=" * 80)
    print("All examples completed successfully!")
    print("=" * 80)
