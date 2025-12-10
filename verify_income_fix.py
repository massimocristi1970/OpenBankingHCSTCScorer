#!/usr/bin/env python3
"""
Quick verification script to demonstrate the income detection fix.

This script shows real-world examples of transactions that were previously
miscategorized, causing false declines.
"""

from transaction_categorizer import TransactionCategorizer
from income_detector import IncomeDetector


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def verify_scenario(categorizer, description, amount, plaid_primary, plaid_detailed, expected_category):
    """Verify a single transaction categorization scenario."""
    result = categorizer.categorize_transaction(
        description=description,
        amount=amount,
        plaid_category_primary=plaid_primary,
        plaid_category=plaid_detailed
    )
    
    status = "✅ PASS" if result.category == expected_category else "❌ FAIL"
    print(f"\n{status}")
    print(f"  Description: {description}")
    print(f"  Amount: £{abs(amount):,.2f}")
    print(f"  PLAID Category: {plaid_primary}/{plaid_detailed}")
    print(f"  Detected as: {result.category}/{result.subcategory}")
    print(f"  Weight: {result.weight}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Method: {result.match_method}")
    
    return result.category == expected_category


def main():
    """Run verification scenarios."""
    categorizer = TransactionCategorizer()
    detector = IncomeDetector()
    
    print_section("Income Miscategorization Fix - Verification")
    print("This script demonstrates that salary payments are now correctly")
    print("identified even when PLAID categorizes them as TRANSFER_IN.")
    
    # Track results
    passed = 0
    total = 0
    
    # Scenario 1: BGC Salary Payment (Main fix)
    print_section("Scenario 1: BANK GIRO CREDIT Salary (Previously Miscategorized)")
    total += 1
    if verify_scenario(
        categorizer,
        description="BANK GIRO CREDIT REF CHEQUERS CONTRACT",
        amount=-1241.46,
        plaid_primary="TRANSFER_IN",
        plaid_detailed="TRANSFER_IN_ACCOUNT_TRANSFER",
        expected_category="income"
    ):
        passed += 1
    
    # Scenario 2: FP- Prefix Salary
    print_section("Scenario 2: FP- Prefix Salary Payment")
    total += 1
    if verify_scenario(
        categorizer,
        description="FP-ACME CORP LTD SALARY",
        amount=-2500.00,
        plaid_primary="TRANSFER_IN",
        plaid_detailed="TRANSFER_IN_ACCOUNT_TRANSFER",
        expected_category="income"
    ):
        passed += 1
    
    # Scenario 3: DWP Benefits
    print_section("Scenario 3: DWP Benefits Payment")
    total += 1
    if verify_scenario(
        categorizer,
        description="DWP UNIVERSAL CREDIT",
        amount=-800.00,
        plaid_primary="TRANSFER_IN",
        plaid_detailed="TRANSFER_IN_ACCOUNT_TRANSFER",
        expected_category="income"
    ):
        passed += 1
    
    # Scenario 4: Genuine Transfer (Should NOT be income)
    print_section("Scenario 4: Genuine Internal Transfer (Should Stay as Transfer)")
    total += 1
    if verify_scenario(
        categorizer,
        description="TRANSFER FROM SAVINGS ACCOUNT",
        amount=-1000.00,
        plaid_primary="TRANSFER_IN",
        plaid_detailed="TRANSFER_IN_ACCOUNT_TRANSFER",
        expected_category="transfer"
    ):
        passed += 1
    
    # Scenario 5: Correctly Categorized PLAID Income
    print_section("Scenario 5: Correctly Categorized PLAID Income (Unchanged)")
    total += 1
    if verify_scenario(
        categorizer,
        description="EMPLOYER PAYMENT",
        amount=-2333.00,
        plaid_primary="INCOME",
        plaid_detailed="INCOME_WAGES",
        expected_category="income"
    ):
        passed += 1
    
    # Test recurring pattern detection
    print_section("Scenario 6: Recurring Pattern Detection")
    transactions = [
        {"name": "ACME LTD SALARY", "amount": -2500, "date": "2024-01-25"},
        {"name": "ACME LTD SALARY", "amount": -2500, "date": "2024-02-25"},
        {"name": "ACME LTD SALARY", "amount": -2500, "date": "2024-03-25"},
    ]
    
    recurring_sources = detector.find_recurring_income_sources(transactions)
    
    if len(recurring_sources) == 1:
        source = recurring_sources[0]
        print(f"\n✅ PASS")
        print(f"  Detected {source.occurrence_count} recurring payments")
        print(f"  Average amount: £{source.amount_avg:,.2f}")
        print(f"  Frequency: {source.frequency_days:.1f} days (monthly)")
        print(f"  Source type: {source.source_type}")
        print(f"  Confidence: {source.confidence:.2f}")
        passed += 1
    else:
        print(f"\n❌ FAIL - Expected 1 recurring source, found {len(recurring_sources)}")
    total += 1
    
    # Final summary
    print_section("Summary")
    print(f"\nTests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n✅ All verification scenarios passed!")
        print("The income detection fix is working correctly.")
        return 0
    else:
        print(f"\n❌ {total - passed} scenario(s) failed!")
        print("Please review the output above for details.")
        return 1


if __name__ == "__main__":
    exit(main())
