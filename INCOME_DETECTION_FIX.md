# Income Miscategorization Fix - Technical Documentation

## Problem Statement

Applications were being incorrectly declined due to legitimate salary payments being miscategorized as internal transfers (TRANSFER_IN) instead of income. This caused monthly income calculations to be artificially deflated by 70-80%, triggering false "below minimum income" declines.

### Evidence
- Applications with confirmed £1,500+ income at application time showed £66-£900 monthly income in system
- Pattern: All declined applicants showed "Monthly income below minimum (£1000)" despite having salary deposits
- Root cause: PLAID categorizes some UK salary payments (BANK GIRO CREDIT, FP- prefix) as TRANSFER_IN_ACCOUNT_TRANSFER

## Solution Overview

Implemented **behavioral income detection** that identifies income through:
1. Recurring payment patterns (weekly, fortnightly, monthly intervals)
2. UK payroll keywords (BACS, BGC, BANK GIRO CREDIT, FP- prefix, etc.)
3. Government benefits detection (DWP, HMRC, Universal Credit, etc.)
4. Priority checking: Income indicators checked BEFORE transfer categorization

## Architecture Changes

### New Module: `income_detector.py`

**Purpose**: Detect income through behavioral patterns and keywords, independent of PLAID categorization.

**Key Components**:

#### 1. `IncomeDetector` Class
Main class for behavioral income detection with configurable thresholds.

```python
detector = IncomeDetector(
    min_amount=50.0,        # Minimum transaction amount to consider
    min_occurrences=2       # Minimum occurrences for recurring pattern
)
```

#### 2. `find_recurring_income_sources(transactions: List[Dict])`
Analyzes transaction patterns to identify recurring income sources.

**Detection Criteria**:
- Amount similarity: Within 30% variance
- Frequency regularity:
  - Weekly: 7±2 days (5-9 days)
  - Fortnightly: 14±3 days (11-17 days)
  - Monthly: 28-31 days (25-35 days)
- Minimum occurrences: 2+ similar payments

**Returns**: List of `RecurringIncomeSource` objects with confidence scores.

#### 3. `matches_payroll_patterns(description: str)`
Checks transaction descriptions for UK payroll keywords.

**Keywords Detected**:
- Standard: SALARY, WAGES, PAYROLL, NET PAY, EMPLOYER
- UK-specific: BGC, BANK GIRO CREDIT, BACS CREDIT, FP- prefix
- Payment types: MONTHLY PAY, WEEKLY PAY, CONTRACT PAY

#### 4. `matches_benefit_patterns(description: str)`
Identifies UK government benefit payments.

**Benefits Detected**:
- Universal Credit, DWP, HMRC
- Specific benefits: PIP, DLA, ESA, JSA, Child Benefit, Tax Credits
- Pension Credit, Housing Benefit, Carers Allowance

#### 5. `is_likely_income(...)`
Combined heuristic scoring that determines if a transaction is likely income.

**Priority Order**:
1. Exclusions (internal transfers, loan disbursements) - HIGHEST
2. PLAID INCOME category - HIGH
3. Keyword matching (payroll, benefits, pension) - HIGH
4. Company name patterns (LTD, PLC, etc.) - MEDIUM
5. Recurring patterns (if transaction list provided) - MEDIUM
6. PLAID TRANSFER category (only if not income) - LOW

**Returns**: `(is_likely_income: bool, confidence: float, reason: str)`

### Updated Module: `transaction_categorizer.py`

**Critical Change**: Income detection now happens BEFORE transfer detection.

**Old Flow** (Caused Issues):
```
1. Check PLAID TRANSFER → Mark as transfer (weight=0.0)
2. Check income patterns → Never reached for TRANSFER_IN
3. Result: Salary missed
```

**New Flow** (Fixed):
```
1. Use behavioral detector to check income indicators
2. If detected as income with confidence ≥ 0.70 → Categorize as income
3. Check traditional income patterns (keywords)
4. Check PLAID income category
5. ONLY THEN check for transfers
6. Result: Salary correctly identified
```

**Integration Point**:
```python
# _categorize_income method now calls behavioral detector first
is_income, confidence, reason = self.income_detector.is_likely_income(
    description=description,
    amount=amount,
    plaid_category_primary=plaid_category_primary,
    plaid_category_detailed=plaid_category
)

if is_income and confidence >= 0.70:
    # Categorize based on reason (salary/benefits/pension/other)
    return appropriate_income_category
```

## Test Coverage

### New Tests: `test_behavioral_income_detection.py`
24 comprehensive tests covering:

1. **Recurring Pattern Detection** (7 tests)
   - Monthly salary patterns
   - Fortnightly salary patterns
   - Weekly salary patterns
   - Monthly benefits patterns
   - Variable amounts rejection
   - Irregular intervals rejection
   - Multiple income sources

2. **Payroll Pattern Matching** (4 tests)
   - Standard salary keywords
   - UK-specific payroll keywords
   - Employer keywords
   - Non-payroll descriptions

3. **Benefits Pattern Matching** (4 tests)
   - DWP benefits
   - Specific UK benefits (PIP, DLA, ESA, etc.)
   - HMRC payments
   - Non-benefit descriptions

4. **Income vs Transfer Distinction** (5 tests)
   - Salary overrides PLAID transfer
   - Company payments detection
   - Internal transfer exclusion
   - Loan disbursement exclusion
   - PLAID income category recognition

5. **Integration Tests** (4 tests)
   - BGC salary not categorized as transfer
   - DWP benefits recognized
   - Genuine transfers still detected
   - Loan disbursements handled

### Existing Tests: All Pass
- `test_salary_miscategorization_fix.py`: 16 tests ✓
- `test_income_calculation_fix.py`: 3 tests ✓
- `test_transfer_fix.py`: 7 tests ✓
- Other tests: 25 tests ✓

**Total**: 75 tests passing

## Impact Assessment

### Positive Impact
1. **Accuracy**: Salary payments correctly identified even when PLAID miscategorizes
2. **Income Calculation**: Returns to accurate £1,500-£2,500+ range
3. **Application Approvals**: Legitimate income no longer causes false declines
4. **Behavioral Detection**: Catches income through patterns, not just keywords

### Preserved Functionality
1. **Transfer Detection**: Genuine transfers still correctly identified
2. **Gig Economy**: Still weighted at 70% (maintains conservative assessment)
3. **Loan Disbursements**: Not counted as income
4. **Risk Patterns**: All existing risk detection unchanged

## Configuration

### Configurable Parameters

**In `IncomeDetector`**:
```python
# Minimum amount threshold for income detection
min_amount: float = 50.0

# Minimum occurrences for recurring pattern
min_occurrences: int = 2

# Large payment threshold (class constant)
LARGE_PAYMENT_THRESHOLD = 500.0
```

**Pattern Detection Thresholds**:
- Amount variance tolerance: 30%
- Weekly interval: 5-9 days
- Fortnightly interval: 11-17 days
- Monthly interval: 25-35 days

### Adding New Keywords

**Payroll Keywords** (`income_detector.py` line 23):
```python
PAYROLL_KEYWORDS = [
    "SALARY", "WAGES", "PAYROLL", # Add new keywords here
    ...
]
```

**Benefit Keywords** (`income_detector.py` line 34):
```python
BENEFIT_KEYWORDS = [
    "UNIVERSAL CREDIT", "UC", "DWP", # Add new benefits here
    ...
]
```

**Exclusion Keywords** (`income_detector.py` line 55):
```python
EXCLUSION_KEYWORDS = [
    "OWN ACCOUNT", "INTERNAL", # Add new exclusions here
    ...
]
```

## Examples

### Example 1: PLAID Miscategorized Salary (Now Fixed)
```python
Transaction:
  description: "BANK GIRO CREDIT REF CHEQUERS CONTRACT"
  amount: -1241.46
  plaid_category_primary: "TRANSFER_IN"
  plaid_category: "TRANSFER_IN_ACCOUNT_TRANSFER"

Before Fix:
  → Category: transfer (weight=0.0)
  → Result: £0 income counted

After Fix:
  → Behavioral detector: payroll_keywords match
  → Category: income/salary (weight=1.0)
  → Result: £1,241.46 income counted ✓
```

### Example 2: Recurring Salary Pattern
```python
Transactions (3 months):
  Month 1: "ACME CORP LTD PAYMENT" -2500.00 (Jan 25)
  Month 2: "ACME CORP LTD PAYMENT" -2500.00 (Feb 25)
  Month 3: "ACME CORP LTD PAYMENT" -2500.00 (Mar 25)

Detection:
  → Amounts: £2,500 (0% variance)
  → Interval: ~30 days (monthly pattern)
  → Occurrences: 3
  → Company name: LTD detected
  → Confidence: 0.85
  → Category: income/salary ✓
```

### Example 3: Benefits Detection
```python
Transaction:
  description: "DWP UNIVERSAL CREDIT"
  amount: -800.00
  plaid_category_primary: "TRANSFER_IN"

Detection:
  → Behavioral detector: benefit_keywords match
  → Category: income/benefits (weight=1.0)
  → Stable income: Yes
  → Result: £800 income counted ✓
```

### Example 4: Genuine Transfer (Still Detected)
```python
Transaction:
  description: "TRANSFER FROM SAVINGS ACCOUNT"
  amount: -1000.00
  plaid_category_primary: "TRANSFER_IN"

Detection:
  → Behavioral detector: exclusion keyword match ("FROM SAVINGS")
  → Category: transfer (weight=0.0)
  → Result: £0 income counted ✓
```

## Maintenance Notes

### Future Enhancements
1. **Machine Learning**: Could train model on historical patterns
2. **Dynamic Thresholds**: Adjust variance/interval tolerances based on data
3. **Merchant Database**: Maintain database of known employers/benefit agencies
4. **Confidence Tuning**: Adjust confidence thresholds based on production data

### Monitoring Recommendations
1. Track false positive rate (legitimate transfers marked as income)
2. Track false negative rate (salary marked as transfers)
3. Monitor confidence score distribution
4. Log behavioral detector reasons for analysis

### Common Pitfalls to Avoid
1. **Don't revert checking order**: Income must be checked BEFORE transfers
2. **Don't remove salary keywords**: UK payroll terms are essential
3. **Don't increase variance threshold**: 30% is already permissive
4. **Don't skip behavioral detector**: Provides critical pattern detection

## Security Considerations

### CodeQL Analysis
✓ No security vulnerabilities detected

### Key Security Aspects
1. **Input Validation**: All transaction data validated before processing
2. **No External Calls**: Pure internal logic, no API calls
3. **No Secrets**: No credentials or sensitive data in code
4. **Safe Math Operations**: Division-by-zero guards in place
5. **Type Safety**: Strong typing throughout with Python type hints

## Performance

### Computational Complexity
- Single transaction categorization: O(k) where k = number of keyword lists
- Recurring pattern detection: O(n²) where n = number of transactions
- Recommended: Call recurring detection once per batch, not per transaction

### Optimization
Pattern detection is performed on-demand. For large transaction lists:
1. Cache recurring source detection results
2. Pass cached results to individual transaction categorization
3. Avoid repeated pattern detection for same transaction list

## Support & Contact

For questions or issues related to this fix:
1. Review this documentation
2. Check test cases in `test_behavioral_income_detection.py`
3. Examine `income_detector.py` inline comments
4. Refer to original issue description in PR

---

**Version**: 1.0  
**Last Updated**: 2025-12-10  
**Author**: GitHub Copilot Agent  
**Status**: Production Ready ✓
