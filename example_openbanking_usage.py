"""
Example usage of the OpenBanking Engine for transaction categorization and loan scoring.

This file demonstrates the main API and various usage patterns.
"""

from datetime import datetime, timedelta
from openbanking_engine import (
    # Main API
    run_open_banking_scoring,
    # Individual components
    TransactionCategorizer,
    IncomeDetector,
    MetricsCalculator,
    ScoringEngine,
    # Data classes
    CategoryMatch,
    Decision,
)


def example_1_basic_categorization():
    """Example 1: Basic transaction categorization."""
    print("=" * 60)
    print("EXAMPLE 1: Basic Transaction Categorization")
    print("=" * 60)
    
    categorizer = TransactionCategorizer()
    
    # Sample transactions
    transactions = [
        ("SALARY FROM ACME LTD", -2500.0, "INCOME_WAGES", "INCOME"),
        ("RENT TO LANDLORD", 850.0, "RENT_AND_UTILITIES_RENT", "RENT_AND_UTILITIES"),
        ("TESCO GROCERY", 65.0, "FOOD_AND_DRINK_GROCERIES", "FOOD_AND_DRINK"),
        ("BET365 GAMBLING", 50.0, "ENTERTAINMENT_GAMBLING", "ENTERTAINMENT"),
        ("LENDING STREAM PAYMENT", 120.0, "LOAN_PAYMENTS", "LOAN_PAYMENTS"),
    ]
    
    print("\nCategorizing transactions:")
    for desc, amount, plaid_cat, plaid_primary in transactions:
        result = categorizer.categorize_transaction(
            description=desc,
            amount=amount,
            plaid_category=plaid_cat,
            plaid_category_primary=plaid_primary
        )
        
        print(f"\n  {desc}")
        print(f"    Category: {result.category}/{result.subcategory}")
        print(f"    Confidence: {result.confidence:.2f}")
        print(f"    Method: {result.match_method}")
        print(f"    Weight: {result.weight}")
        if result.risk_level:
            print(f"    Risk Level: {result.risk_level}")


def example_2_complete_scoring_pipeline():
    """Example 2: Complete scoring pipeline using main API."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Complete Scoring Pipeline")
    print("=" * 60)
    
    # Generate sample transaction history (90 days)
    base_date = datetime.now() - timedelta(days=90)
    transactions = []
    
    # Monthly salary (3 months)
    for i in range(3):
        transactions.append({
            "date": (base_date + timedelta(days=i*30)).strftime("%Y-%m-%d"),
            "amount": -2500.0,
            "description": "SALARY FROM EMPLOYER",
            "merchant_name": "Employer Ltd",
            "plaid_category": "INCOME_WAGES",
            "plaid_category_primary": "INCOME"
        })
    
    # Monthly rent
    for i in range(3):
        transactions.append({
            "date": (base_date + timedelta(days=i*30 + 5)).strftime("%Y-%m-%d"),
            "amount": 850.0,
            "description": "RENT PAYMENT",
            "merchant_name": "Landlord",
            "plaid_category": "RENT_AND_UTILITIES_RENT",
            "plaid_category_primary": "RENT_AND_UTILITIES"
        })
    
    # Regular groceries
    for i in range(12):
        transactions.append({
            "date": (base_date + timedelta(days=i*7 + 2)).strftime("%Y-%m-%d"),
            "amount": 60.0 + (i % 3) * 10,
            "description": "TESCO",
            "plaid_category": "FOOD_AND_DRINK_GROCERIES",
            "plaid_category_primary": "FOOD_AND_DRINK"
        })
    
    # Utilities
    for i in range(3):
        transactions.append({
            "date": (base_date + timedelta(days=i*30 + 10)).strftime("%Y-%m-%d"),
            "amount": 120.0,
            "description": "BRITISH GAS",
            "plaid_category": "GENERAL_SERVICES_OTHER_GENERAL_SERVICES",
            "plaid_category_primary": "GENERAL_SERVICES"
        })
    
    # Credit card payment
    for i in range(3):
        transactions.append({
            "date": (base_date + timedelta(days=i*30 + 15)).strftime("%Y-%m-%d"),
            "amount": 150.0,
            "description": "BARCLAYCARD PAYMENT",
            "plaid_category": "LOAN_PAYMENTS_CREDIT_CARD_PAYMENT",
            "plaid_category_primary": "LOAN_PAYMENTS"
        })
    
    print(f"\nProcessing {len(transactions)} transactions...")
    
    # Run complete scoring
    result = run_open_banking_scoring(
        transactions=transactions,
        requested_amount=500,
        requested_term=3,
        days_covered=90
    )
    
    print(f"\n{'='*60}")
    print("SCORING RESULTS")
    print(f"{'='*60}")
    print(f"Decision: {result['decision']}")
    print(f"Score: {result['score']:.1f} / 175")
    print(f"Max Approved Amount: £{result['max_approved_amount']}")
    print(f"Max Approved Term: {result['max_approved_term']} months")
    
    if result['decline_reasons']:
        print(f"\nDecline Reasons:")
        for reason in result['decline_reasons']:
            print(f"  - {reason}")
    
    if result['referral_reasons']:
        print(f"\nReferral Reasons:")
        for reason in result['referral_reasons']:
            print(f"  - {reason}")
    
    print(f"\n{'='*60}")
    print("FINANCIAL METRICS")
    print(f"{'='*60}")
    
    income = result['metrics']['income']
    print(f"\nIncome:")
    print(f"  Monthly Income: £{income['monthly_income']:.2f}")
    print(f"  Stable Income: £{income['monthly_stable_income']:.2f}")
    print(f"  Income Stability: {income['income_stability_score']:.1f}/100")
    print(f"  Income Sources: {', '.join(income['income_sources'])}")
    
    expense = result['metrics']['expense']
    print(f"\nExpenses:")
    print(f"  Housing: £{expense['monthly_housing']:.2f}")
    print(f"  Groceries: £{expense['monthly_groceries']:.2f}")
    print(f"  Utilities: £{expense['monthly_utilities']:.2f}")
    print(f"  Total Essential: £{expense['monthly_essential_total']:.2f}")
    
    debt = result['metrics']['debt']
    print(f"\nDebt:")
    print(f"  Monthly Debt Payments: £{debt['monthly_debt_payments']:.2f}")
    print(f"  Active Credit Cards: {debt['active_credit_cards']}")
    print(f"  Active HCSTC Lenders: {debt['active_hcstc_count']}")
    
    affordability = result['metrics']['affordability']
    print(f"\nAffordability:")
    print(f"  Monthly Disposable: £{affordability['monthly_disposable']:.2f}")
    print(f"  DTI Ratio: {affordability['dti_ratio']:.1f}%")
    print(f"  Post-Loan Disposable: £{affordability['post_loan_disposable']:.2f}")
    print(f"  Estimated Repayment: £{affordability['estimated_monthly_repayment']:.2f}")
    
    risk = result['metrics']['risk']
    print(f"\nRisk Indicators:")
    print(f"  Gambling: £{risk['gambling_total']:.2f} ({risk['gambling_percentage']:.1f}%)")
    print(f"  Bank Charges: {risk['bank_charges_count']}")
    print(f"  Failed Payments: {risk['failed_payments_count']}")
    
    print(f"\n{'='*60}")
    print("SCORE BREAKDOWN")
    print(f"{'='*60}")
    breakdown = result['score_breakdown']
    print(f"  Affordability: {breakdown['affordability_score']:.1f} / 78.75")
    print(f"  Income Quality: {breakdown['income_quality_score']:.1f} / 43.75")
    print(f"  Account Conduct: {breakdown['account_conduct_score']:.1f} / 35.0")
    print(f"  Risk Indicators: {breakdown['risk_indicators_score']:.1f} / 17.5")


def example_3_individual_components():
    """Example 3: Using individual components separately."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Using Individual Components")
    print("=" * 60)
    
    # Create sample transactions
    raw_transactions = [
        {"date": "2025-01-15", "amount": -2500.0, "description": "SALARY"},
        {"date": "2025-01-16", "amount": 850.0, "description": "RENT"},
        {"date": "2025-01-17", "amount": 65.0, "description": "TESCO"},
        {"date": "2025-01-18", "amount": 120.0, "description": "BRITISH GAS"},
        {"date": "2025-01-19", "amount": 150.0, "description": "BARCLAYCARD"},
    ]
    
    # Step 1: Categorize
    print("\nStep 1: Categorizing transactions...")
    categorizer = TransactionCategorizer()
    categorized = []
    
    for txn in raw_transactions:
        result = categorizer.categorize_transaction(
            description=txn["description"],
            amount=txn["amount"]
        )
        categorized.append({
            "date": txn["date"],
            "amount": txn["amount"],
            "description": txn["description"],
            "category": result.category,
            "subcategory": result.subcategory,
            "confidence": result.confidence,
            "weight": result.weight,
            "is_stable": result.is_stable,
            "is_housing": result.is_housing,
        })
        print(f"  {txn['description']}: {result.category}/{result.subcategory}")
    
    # Step 2: Use the main API for simplicity (handles metrics calculation)
    print("\nStep 2: Running complete scoring pipeline...")
    result = run_open_banking_scoring(
        transactions=raw_transactions,
        requested_amount=500,
        requested_term=3,
        days_covered=30
    )
    
    print(f"  Decision: {result['decision']}")
    print(f"  Score: {result['score']:.1f}")
    print(f"  Monthly Income: £{result['metrics']['income']['monthly_income']:.2f}")
    print(f"  Monthly Expenses: £{result['metrics']['expense']['monthly_essential_total']:.2f}")
    print(f"  Monthly Disposable: £{result['metrics']['affordability']['monthly_disposable']:.2f}")



def example_4_income_detection():
    """Example 4: Using the behavioral income detector."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Behavioral Income Detection")
    print("=" * 60)
    
    detector = IncomeDetector()
    
    # Test various transactions
    test_cases = [
        ("SALARY FROM ACME LTD", -2500.0, "INCOME"),
        ("TRANSFER FROM SAVINGS", -1000.0, "TRANSFER_IN"),
        ("PAYPAL PAYMENT", -200.0, "TRANSFER_IN"),
        ("DWP UNIVERSAL CREDIT", -500.0, "INCOME"),
        ("UBER DRIVER EARNINGS", -150.0, "INCOME"),
    ]
    
    print("\nTesting income detection:")
    for desc, amount, plaid_primary in test_cases:
        is_income, confidence, reason = detector.is_likely_income(
            description=desc,
            amount=amount,
            plaid_category_primary=plaid_primary
        )
        
        print(f"\n  {desc}")
        print(f"    Is Income: {is_income}")
        print(f"    Confidence: {confidence:.2f}")
        print(f"    Reason: {reason}")


def example_5_backward_compatibility():
    """Example 5: Backward compatibility with old import style."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Backward Compatibility")
    print("=" * 60)
    
    # Old import style still works
    from transaction_categorizer import TransactionCategorizer as OldCategorizer
    from scoring_engine import ScoringEngine as OldEngine, Decision as OldDecision
    from metrics_calculator import MetricsCalculator as OldCalculator
    
    print("\nOld import style still works:")
    print(f"  TransactionCategorizer: {OldCategorizer}")
    print(f"  ScoringEngine: {OldEngine}")
    print(f"  MetricsCalculator: {OldCalculator}")
    print(f"  Decision enum: {OldDecision}")
    
    # Can instantiate and use
    categorizer = OldCategorizer()
    result = categorizer.categorize_transaction(
        description="SALARY PAYMENT",
        amount=-2500.0
    )
    print(f"\n  Categorized 'SALARY PAYMENT': {result.category}/{result.subcategory}")
    print("  ✓ Backward compatibility maintained!")


if __name__ == "__main__":
    """Run all examples."""
    print("\n" + "=" * 60)
    print("OpenBanking Engine - Usage Examples")
    print("=" * 60)
    
    # Run all examples
    example_1_basic_categorization()
    example_2_complete_scoring_pipeline()
    example_3_individual_components()
    example_4_income_detection()
    example_5_backward_compatibility()
    
    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
