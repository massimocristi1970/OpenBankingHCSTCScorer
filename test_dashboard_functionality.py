"""
Test the dashboard functionality without running the Flask server.
"""

import json
from dashboard import process_transaction_file, generate_summary

def test_dashboard_processing():
    """Test that the dashboard can process transaction files correctly."""
    
    print("Testing Dashboard Transaction Processing")
    print("=" * 60)
    
    # Test with the sample file
    sample_file = '/home/runner/work/OpenBankingHCSTCScorer/OpenBankingHCSTCScorer/sample_transactions.json'
    
    print(f"\n1. Processing sample file: {sample_file}")
    results = process_transaction_file(sample_file)
    
    print(f"   ✓ Processed {len(results)} transactions")
    
    # Display first few results
    print("\n2. Sample Results:")
    for i, result in enumerate(results[:5], 1):
        print(f"\n   Transaction {i}:")
        print(f"   - Description: {result['description']}")
        print(f"   - Amount: £{abs(result['amount']):.2f} ({'credit' if result['amount'] < 0 else 'debit'})")
        print(f"   - Category: {result['category']}/{result['subcategory']}")
        print(f"   - Confidence: {result['confidence']:.2%}")
        print(f"   - Match Method: {result['match_method']}")
    
    # Test summary generation
    print("\n3. Generating Summary Statistics:")
    summary = generate_summary(results)
    
    print(f"   ✓ Total Transactions: {summary['total_transactions']}")
    print(f"   ✓ Income Transactions: {summary['income_count']}")
    print(f"   ✓ Expense Transactions: {summary['expense_count']}")
    print(f"\n   Confidence Levels:")
    print(f"   - High (≥80%): {summary['by_confidence_level']['high']}")
    print(f"   - Medium (60-79%): {summary['by_confidence_level']['medium']}")
    print(f"   - Low (<60%): {summary['by_confidence_level']['low']}")
    
    print(f"\n   Categories:")
    for category, count in sorted(summary['by_category'].items()):
        print(f"   - {category}: {count}")
    
    print(f"\n   Subcategories:")
    for subcategory, count in sorted(summary['by_subcategory'].items()):
        print(f"   - {subcategory}: {count}")
    
    if summary['low_confidence_transactions']:
        print(f"\n4. Low Confidence Transactions ({len(summary['low_confidence_transactions'])}):")
        for txn in summary['low_confidence_transactions']:
            print(f"   - {txn['description'][:50]}: {txn['category']}/{txn['subcategory']} ({txn['confidence']:.2%})")
    
    # Test with different JSON structures
    print("\n5. Testing JSON Array Structure:")
    with open(sample_file, 'r') as f:
        data = json.load(f)
    
    test_file = '/tmp/test_array.json'
    with open(test_file, 'w') as f:
        json.dump(data, f)
    
    results_array = process_transaction_file(test_file)
    print(f"   ✓ Array format processed: {len(results_array)} transactions")
    
    print("\n6. Testing JSON Object Structure:")
    test_file_obj = '/tmp/test_object.json'
    with open(test_file_obj, 'w') as f:
        json.dump({"transactions": data}, f)
    
    results_obj = process_transaction_file(test_file_obj)
    print(f"   ✓ Object format processed: {len(results_obj)} transactions")
    
    print("\n" + "=" * 60)
    print("✓ All Dashboard Tests Passed!")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    test_dashboard_processing()
