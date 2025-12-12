# Monthly Income and Expense Calculation Fix

## Problem Statement

The system previously **hardcoded `months_of_data = 3`** and divided all category totals by this fixed value, regardless of how much data was actually provided. This caused incorrect monthly income/expense calculations.

### Example Issue

From user testing with actual transaction data (March 2025 - May 2025 = 3 months):
- Fuller Smith & Turner salary total: **£4,599.73** 
- System showed monthly income: **£1,664.76** (incorrect - inflated by using wrong divisor)
- Expected monthly: £4,599.73 / 3 = **£1,533.24**
- Difference: **£131.52 per month extra** (unexplained inflation)

The same issue applied to expense calculations which were also artificially inflated.

## Solution Implemented

### 1. Automatic Month Calculation

Added `_calculate_months_of_data()` method to `MetricsCalculator` class:
- Finds earliest and latest transaction dates
- Calculates unique calendar months between them (e.g., Jan, Feb, Mar = 3 months)
- Returns the actual month count

```python
def _calculate_months_of_data(self, transactions: List[Dict]) -> int:
    """
    Calculate the number of unique months covered by transactions.
    
    For example:
    - March 1 to March 31: 1 month
    - March 1 to May 31: 3 months (March, April, May)
    - Jan 15 to Dec 20: 12 months
    """
    # Implementation details in feature_builder.py
```

### 2. Updated Constructor

`MetricsCalculator.__init__()` now accepts optional parameters:
- `months_of_data`: Explicit override (for testing/API compatibility)
- `transactions`: Transaction list to auto-calculate from

**Priority order:**
1. If `months_of_data` is explicitly provided → use it
2. Else if `transactions` is provided → calculate automatically
3. Else → default to 3 (backward compatibility)

```python
calculator = MetricsCalculator(transactions=transactions)  # Auto-calculate
calculator = MetricsCalculator(months_of_data=6)  # Manual override
calculator = MetricsCalculator()  # Defaults to 3 (backward compatible)
```

### 3. Integration Updates

- **`run_open_banking_scoring()`**: Now passes transactions to calculator for auto-calculation
- **`hcstc_batch_processor.py`**: Updated to use automatic calculation per application
- **`app.py`**: Added UI toggle for auto-calculation (default: on) with manual override option

## Results

### Scenario 1: 3 Months (March-May 2025)
- Total salary: £4,599.73
- Monthly income: £1,533.24 ✓ (was incorrectly inflated before)

### Scenario 2: 6 Months
- If 6 months of data provided → divides by 6 (not 3) ✓

### Scenario 3: 12 Months
- If 12 months of data provided → divides by 12 (not 3) ✓

## Backward Compatibility

✅ Explicit `months_of_data` parameter still works (for testing/API)
✅ Default to 3 months when no parameters provided
✅ Manual override always takes precedence

## Testing

Comprehensive tests added in `tests/test_month_calculation_fix.py`:
- Test 3, 6, 12 month calculations
- Test partial months (counted as full months)
- Test real-world Fuller Smith & Turner scenario
- Test backward compatibility
- Test invalid date handling

All tests pass ✓

## Files Modified

1. `openbanking_engine/scoring/feature_builder.py` - Core calculation logic
2. `openbanking_engine/__init__.py` - Main entry point integration
3. `hcstc_batch_processor.py` - Batch processing integration
4. `app.py` - UI controls for auto-calculation
5. `tests/test_month_calculation_fix.py` - Comprehensive test suite

## Usage Examples

### Auto-calculation (Recommended)
```python
from openbanking_engine import run_open_banking_scoring

transactions = [
    {"date": "2025-03-15", "amount": -2500, "name": "SALARY"},
    {"date": "2025-04-15", "amount": -2500, "name": "SALARY"},
    {"date": "2025-05-15", "amount": -2500, "name": "SALARY"},
]

result = run_open_banking_scoring(
    transactions=transactions,
    requested_amount=500,
    requested_term=3
)

# Automatically calculates 3 months from March-May date range
# Monthly income = £7,500 / 3 = £2,500
```

### Manual Override (Testing/Edge Cases)
```python
calculator = MetricsCalculator(
    months_of_data=6,  # Force 6 months
    transactions=transactions  # Will be ignored
)
```

### Batch Processing
```python
processor = HCSTCBatchProcessor(
    default_loan_amount=500,
    default_loan_term=4
    # months_of_data omitted = auto-calculate per file
)
```

## Future Considerations

- Month calculation is based on calendar months, not rolling 30-day periods
- Partial months are counted as full months (e.g., Jan 25 - Feb 5 = 2 months)
- Empty transactions or all invalid dates fall back to default of 3 months
- Invalid date strings are skipped gracefully in the calculation
