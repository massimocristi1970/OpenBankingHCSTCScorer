"""
Test to verify the dashboard is truly non-intrusive and doesn't modify core behavior.
"""

import json
from transaction_categorizer import TransactionCategorizer
from dashboard import process_transaction_file

def test_non_intrusive():
    """Verify dashboard doesn't change categorization behavior."""
    
    print("Testing Non-Intrusive Behavior")
    print("=" * 60)
    
    # Create test transaction
    test_txn = {
        "name": "BANK GIRO CREDIT TEST CORP",
        "amount": -2500.00,
        "date": "2024-01-25"
    }
    
    # 1. Categorize directly with TransactionCategorizer
    print("\n1. Direct categorization (without dashboard):")
    categorizer = TransactionCategorizer()
    direct_result = categorizer.categorize_transaction(
        description=test_txn["name"],
        amount=test_txn["amount"]
    )
    print(f"   Category: {direct_result.category}/{direct_result.subcategory}")
    print(f"   Confidence: {direct_result.confidence:.2%}")
    print(f"   Method: {direct_result.match_method}")
    
    # 2. Save test transaction to file and process through dashboard
    print("\n2. Processing through dashboard:")
    test_file = '/tmp/test_non_intrusive.json'
    with open(test_file, 'w') as f:
        json.dump([test_txn], f)
    
    dashboard_results = process_transaction_file(test_file)
    dashboard_result = dashboard_results[0]
    print(f"   Category: {dashboard_result['category']}/{dashboard_result['subcategory']}")
    print(f"   Confidence: {dashboard_result['confidence']:.2%}")
    print(f"   Method: {dashboard_result['match_method']}")
    
    # 3. Categorize directly again to ensure state wasn't changed
    print("\n3. Direct categorization again (after dashboard):")
    categorizer2 = TransactionCategorizer()
    second_result = categorizer2.categorize_transaction(
        description=test_txn["name"],
        amount=test_txn["amount"]
    )
    print(f"   Category: {second_result.category}/{second_result.subcategory}")
    print(f"   Confidence: {second_result.confidence:.2%}")
    print(f"   Method: {second_result.match_method}")
    
    # 4. Verify results are consistent
    print("\n4. Verification:")
    
    # Note: match_method might differ slightly (batch_behavioral vs behavioral)
    # but the core categorization should be the same
    checks = [
        ("Category", direct_result.category, dashboard_result['category']),
        ("Subcategory", direct_result.subcategory, dashboard_result['subcategory']),
        ("Confidence", direct_result.confidence, dashboard_result['confidence']),
    ]
    
    all_passed = True
    for name, val1, val2 in checks:
        match = val1 == val2
        status = "✓" if match else "✗"
        print(f"   {status} {name}: {val1} == {val2}")
        if not match:
            all_passed = False
    
    # Verify categorizer state is unchanged
    state_unchanged = (
        direct_result.category == second_result.category and
        direct_result.subcategory == second_result.subcategory and
        direct_result.confidence == second_result.confidence
    )
    
    print(f"\n   {'✓' if state_unchanged else '✗'} Categorizer state unchanged after dashboard use")
    
    if all_passed and state_unchanged:
        print("\n" + "=" * 60)
        print("✓ NON-INTRUSIVE TEST PASSED")
        print("Dashboard does not modify core categorization behavior!")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("✗ TEST FAILED")
        print("Dashboard may be affecting core behavior")
        print("=" * 60)
        return False

if __name__ == '__main__':
    success = test_non_intrusive()
    exit(0 if success else 1)
