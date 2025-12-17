# Enhanced Categorization Features

This document describes the enhanced categorization features added to the OpenBanking HCSTC Scorer.

## Overview

The enhanced categorization system improves transaction classification through:
1. **Extended Keywords**: Additional patterns for salary, gig economy, pensions, benefits, interest, and transfers
2. **PLAID Category Preference**: Prefer detailed PLAID categories over primary for better accuracy
3. **Transfer Pairing Heuristic**: Match debit/credit pairs to avoid misclassifying transfers
4. **Quarterly Pension Support**: Recognize pension payments with 80-100 day intervals
5. **Debug Mode**: Optional detailed rationale for categorization decisions

## Extended Keywords

All keyword additions are **additive only** - no existing keywords were removed to maintain backward compatibility.

### Salary/Payroll Keywords
- **ADP**: Automatic Data Processing payroll system
- **PAYFIT**: UK payroll provider
- **SAGE PAYROLL**: Sage payroll software
- **XERO PAYRUN**: Xero accounting payrun
- **WORKDAY**: Workday HR system
- **BARCLAYS PAYMENTS**: Barclays payroll service
- **HSBC PAYROLL**: HSBC payroll service

### Gig Economy Keywords
- **UBER EATS**: Food delivery platform
- **EVRI**: Courier/delivery service
- **DPD**: Courier service
- **YODEL**: Courier service
- **ROYAL MAIL**: Royal Mail delivery
- **SHOPIFY PAYMENTS**: Shopify merchant payouts
- **STRIPE PAYOUT**: Stripe payment processor payouts
- **PAYPAL PAYOUT**: PayPal payment processor payouts

### Pension Provider Keywords
- Provider-specific patterns for: NEST, AVIVA, LEGAL AND GENERAL, SCOTTISH WIDOWS, STANDARD LIFE, PRUDENTIAL, ROYAL LONDON, AEGON

### Tax Refund Keywords
- **HMRC REFUND**: HM Revenue & Customs refund
- **TAX REFUND**: General tax refund
- **HMRC TAX REFUND**: Explicit HMRC tax refund

### Interest Income Keywords (New Category)
- **INTEREST**: Bank interest
- **GROSS INTEREST** / **GROSS INT**: Gross interest paid
- **BANK INTEREST**: Explicit bank interest
- **SAVINGS INTEREST**: Savings account interest

### Transfer Keywords (Neobanks & Internal)
- **REVOLUT**: Revolut transfers
- **MONZO**: Monzo pot transfers
- **STARLING**: Starling space transfers
- **CHASE**: Chase bank transfers
- **WISE**: Wise transfers
- **PAYPAL TOPUP**: PayPal top-up
- **POT**: Savings pot transfers
- **VAULT**: Savings vault transfers
- **ROUND UP**: Round-up savings
- **MOVE MONEY**: Internal money movement
- **INTERNAL MOVE**: Internal transfers

## PLAID Category Preference

The system now **prefers detailed PLAID categories over primary** throughout:

### In Income Detection
```python
# Before: primary checked first
if plaid_category_primary and "INCOME" in plaid_category_primary:
    return (True, 0.86, "plaid_income_primary")

# Now: detailed checked first
if plaid_category_detailed:
    d = plaid_category_detailed.upper()
    if "INCOME_WAGES" in d:
        return (True, 0.96, "plaid_detailed_income_wages")
    if "INCOME_RETIREMENT" in d:
        return (True, 0.94, "plaid_detailed_income_retirement")
```

### In Dashboard Display
The dashboard now displays detailed PLAID category first, falling back to primary only if detailed is missing:
```javascript
// Before: primary first
result.plaid_category_primary || result.plaid_category_detailed

// Now: detailed first
result.plaid_category_detailed || result.plaid_category_primary
```

## Transfer Pairing Heuristic

The transfer pairing heuristic helps identify internal transfers by matching debit/credit pairs:

### Matching Criteria
1. **Opposite Signs**: One transaction is a debit, the other is a credit
2. **Date Proximity**: Within 1-2 days of each other
3. **Amount Similarity**: Within ±10% of each other
4. **Text Overlap**: At least 30% common words in description

### Usage
```python
categorizer = TransactionCategorizer()
pair = categorizer._find_transfer_pair(
    transactions=all_transactions,
    current_idx=0,
    amount=100.00,
    description="TRANSFER TO SAVINGS",
    date_str="2024-01-15"
)
```

The method returns the matching transaction if found, or `None` otherwise.

## Quarterly Pension Tolerance

The income detector now recognizes quarterly pension payments:

### Frequency Ranges
- **Weekly**: 5-9 days
- **Fortnightly**: 11-17 days
- **Monthly**: 25-35 days
- **Quarterly**: 80-100 days ✨ NEW

### Example
```python
detector = IncomeDetector()
sources = detector.find_recurring_income_sources([
    {"name": "STATE PENSION", "amount": -500.00, "date": "2024-01-15"},
    {"name": "STATE PENSION", "amount": -500.00, "date": "2024-04-15"},
    {"name": "STATE PENSION", "amount": -500.00, "date": "2024-07-15"}
])
# Recognizes quarterly pension with 90-day interval
```

## Debug Mode

Debug mode provides detailed rationale for categorization decisions:

### Enabling Debug Mode
```python
categorizer = TransactionCategorizer(debug_mode=True)
result = categorizer.categorize_transaction(
    description="SALARY PAYMENT",
    amount=-2500.00,
    plaid_category=None,
    plaid_category_primary=None
)
print(result.debug_rationale)  # "income_detection: keyword_payroll"
```

### When Debug Mode is Off (Default)
```python
categorizer = TransactionCategorizer(debug_mode=False)  # or just TransactionCategorizer()
result = categorizer.categorize_transaction(...)
print(result.debug_rationale)  # None
```

Debug mode has **no impact on categorization behavior** - it only adds rationale information.

## Credit Card & Loan Repayment Routing

Credit card and loan repayments are automatically routed to the **debt** category:

### Examples
- `BARCLAYCARD PAYMENT` → `debt/credit_cards`
- `LOAN REPAYMENT` → `debt/other_loans`
- `CREDIT CARD PAYMENT` → `debt/credit_cards`

This prevents these transactions from being miscategorized as discretionary expenses.

## Testing

Comprehensive test suite with 28 tests covering:
- Extended salary keywords
- Extended gig economy keywords
- Interest income detection
- Tax refund detection
- Extended transfer keywords
- Quarterly pension tolerance
- PLAID detailed category preference
- Debug mode functionality
- Transfer pairing heuristic

Run tests:
```bash
python -m unittest tests.test_enhanced_categorization -v
```

## Backward Compatibility

All changes are **additive and non-breaking**:
- ✅ No existing keywords removed
- ✅ Default behavior unchanged (debug mode off by default)
- ✅ All existing tests continue to pass
- ✅ API signatures backward compatible (debug_mode is optional)

## Configuration

No configuration changes required. The enhanced features work out-of-the-box with:
- Existing transaction data
- Existing PLAID category structures
- Existing scoring logic

Simply use the updated categorizer:
```python
from openbanking_engine.categorisation.engine import TransactionCategorizer

categorizer = TransactionCategorizer()  # Enhanced features enabled
result = categorizer.categorize_transaction(
    description="UBER EATS PAYOUT",
    amount=-150.00,
    plaid_category="INCOME_GIG_ECONOMY",
    plaid_category_primary="INCOME"
)
# result.category = "income"
# result.subcategory = "gig_economy"
```

## Performance Impact

The enhanced features have minimal performance impact:
- Keyword lookups remain O(1) or O(n) with small n
- Transfer pairing is O(n²) worst case but only called when needed
- Debug mode adds negligible overhead when disabled
- All pattern matching uses efficient regex and set operations
