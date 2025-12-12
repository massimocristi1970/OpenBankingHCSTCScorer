"""
Simple examples demonstrating the OpenBanking Engine backward compatibility.

All existing imports continue to work as before.
"""

# Example 1: Basic categorization still works
print("=" * 60)
print("Example 1: Basic Transaction Categorization")
print("=" * 60)

from transaction_categorizer import TransactionCategorizer

categorizer = TransactionCategorizer()

# Categorize some transactions
transactions = [
    ("SALARY FROM ACME LTD", -2500.0),
    ("RENT TO LANDLORD", 850.0),
    ("TESCO GROCERY", 65.0),
    ("BET365 GAMBLING", 50.0),
    ("LENDING STREAM", 120.0),
]

print("\nCategorizing transactions:")
for desc, amount in transactions:
    result = categorizer.categorize_transaction(
        description=desc,
        amount=amount
    )
    print(f"  {desc:30} -> {result.category}/{result.subcategory} (conf: {result.confidence:.2f})")

# Example 2: Using new openbanking_engine imports
print("\n" + "=" * 60)
print("Example 2: New OpenBanking Engine Imports")
print("=" * 60)

from openbanking_engine import (
    TransactionCategorizer,
    IncomeDetector,
    MetricsCalculator,
    ScoringEngine,
)

print("\nAll classes imported successfully from openbanking_engine:")
print(f"  - TransactionCategorizer: {TransactionCategorizer}")
print(f"  - IncomeDetector: {IncomeDetector}")
print(f"  - MetricsCalculator: {MetricsCalculator}")
print(f"  - ScoringEngine: {ScoringEngine}")

# Example 3: Behavioral income detection
print("\n" + "=" * 60)
print("Example 3: Behavioral Income Detection")
print("=" * 60)

from openbanking_engine import IncomeDetector

detector = IncomeDetector()

test_cases = [
    ("SALARY FROM ACME LTD", -2500.0, "INCOME"),
    ("TRANSFER FROM SAVINGS", -1000.0, "TRANSFER_IN"),
    ("PAYPAL PAYMENT", -200.0, "TRANSFER_IN"),
    ("DWP UNIVERSAL CREDIT", -500.0, "INCOME"),
]

print("\nTesting income detection:")
for desc, amount, plaid_primary in test_cases:
    is_income, confidence, reason = detector.is_likely_income(
        description=desc,
        amount=amount,
        plaid_category_primary=plaid_primary
    )
    status = "✓ INCOME" if is_income else "✗ NOT INCOME"
    print(f"  {desc:30} -> {status:15} (conf: {confidence:.2f}, reason: {reason})")

print("\n" + "=" * 60)
print("✓ All examples completed successfully!")
print("=" * 60)
print("\nThe openbanking_engine module structure is working!")
print("All backward compatibility maintained.")
