"""
Demo script to showcase the dashboard functionality.
This script demonstrates the dashboard by processing sample data and displaying results.
"""

import json
from dashboard import process_transaction_file, generate_summary

def demo_dashboard():
    """Run a demonstration of the dashboard functionality."""
    
    print("\n" + "=" * 80)
    print("TRANSACTION CATEGORIZATION REVIEW DASHBOARD - DEMO")
    print("=" * 80)
    
    print("\n📁 STEP 1: Loading Sample Transaction File")
    print("-" * 80)
    
    sample_file = '/home/runner/work/OpenBankingHCSTCScorer/OpenBankingHCSTCScorer/sample_transactions.json'
    with open(sample_file, 'r') as f:
        transactions = json.load(f)
    
    print(f"✓ Loaded {len(transactions)} transactions from sample_transactions.json")
    
    print("\n🔍 STEP 2: Processing Through Categorization Engine")
    print("-" * 80)
    
    results = process_transaction_file(sample_file)
    print(f"✓ Processed {len(results)} transactions successfully")
    
    print("\n📊 STEP 3: Generating Summary Statistics")
    print("-" * 80)
    
    summary = generate_summary(results)
    
    print(f"\n┌─ OVERVIEW ─────────────────────────────────────┐")
    print(f"│ Total Transactions:     {summary['total_transactions']:>3}                    │")
    print(f"│ Income Transactions:    {summary['income_count']:>3}                    │")
    print(f"│ Expense Transactions:   {summary['expense_count']:>3}                    │")
    print(f"└────────────────────────────────────────────────┘")
    
    print(f"\n┌─ CONFIDENCE LEVELS ────────────────────────────┐")
    print(f"│ High (≥80%):            {summary['by_confidence_level']['high']:>3}                    │")
    print(f"│ Medium (60-79%):        {summary['by_confidence_level']['medium']:>3}                    │")
    print(f"│ Low (<60%):             {summary['by_confidence_level']['low']:>3}                    │")
    print(f"└────────────────────────────────────────────────┘")
    
    print(f"\n┌─ CATEGORIES ───────────────────────────────────┐")
    for category, count in sorted(summary['by_category'].items()):
        print(f"│ {category:<20} {count:>3}                    │")
    print(f"└────────────────────────────────────────────────┘")
    
    print("\n📋 STEP 4: Detailed Transaction Analysis")
    print("-" * 80)
    print(f"\n{'Date':<12} {'Description':<35} {'Amount':>10} {'Category':<20} {'Conf':<6} {'Method':<20}")
    print("-" * 110)
    
    for result in results[:10]:  # Show first 10
        amount_str = f"£{abs(result['amount']):>7.2f}"
        if result['amount'] < 0:
            amount_str = f"-{amount_str}"
        else:
            amount_str = f" {amount_str}"
        
        desc = result['description'][:33] + '..' if len(result['description']) > 35 else result['description']
        cat = f"{result['category']}/{result['subcategory']}"
        conf = f"{result['confidence']:.0%}"
        method = result['match_method'][:18] + '..' if len(result['match_method']) > 20 else result['match_method']
        
        print(f"{result['date']:<12} {desc:<35} {amount_str:>10} {cat:<20} {conf:<6} {method:<20}")
    
    if len(results) > 10:
        print(f"\n... and {len(results) - 10} more transactions")
    
    print("\n🔎 STEP 5: Identifying Issues")
    print("-" * 80)
    
    if summary['low_confidence_transactions']:
        print(f"\n⚠️  Found {len(summary['low_confidence_transactions'])} low confidence transactions:")
        for txn in summary['low_confidence_transactions'][:5]:
            print(f"   • {txn['description'][:50]}")
            print(f"     Category: {txn['category']}/{txn['subcategory']} (Confidence: {txn['confidence']:.0%})")
    else:
        print("\n✓ No low confidence transactions found - all categorizations look good!")
    
    # Check for risk transactions
    risk_transactions = [r for r in results if r['risk_level']]
    if risk_transactions:
        print(f"\n⚠️  Found {len(risk_transactions)} transactions with risk flags:")
        for txn in risk_transactions:
            print(f"   • {txn['description'][:50]}")
            print(f"     Risk Level: {txn['risk_level'].upper()} - {txn['category']}/{txn['subcategory']}")
    
    print("\n📥 STEP 6: Export Capabilities")
    print("-" * 80)
    print("The dashboard can export results to:")
    print("  • CSV format - for spreadsheet analysis")
    print("  • JSON format - for programmatic processing")
    print("\nExample CSV export includes:")
    print("  date, description, amount, category, subcategory, confidence, match_method, plaid_category, ...")
    
    print("\n" + "=" * 80)
    print("✓ DEMO COMPLETE")
    print("=" * 80)
    print("\nTo use the dashboard:")
    print("  1. Run: python dashboard.py")
    print("  2. Open: http://localhost:5001")
    print("  3. Upload JSON files containing transaction data")
    print("  4. Review categorization results and identify issues")
    print("  5. Export results for further analysis")
    print("\n" + "=" * 80)

if __name__ == '__main__':
    demo_dashboard()
