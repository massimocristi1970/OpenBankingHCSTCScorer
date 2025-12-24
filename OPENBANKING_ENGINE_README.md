# OpenBanking Engine - Professional Module Structure

## Overview

The OpenBanking Engine is a professional, modular system for categorizing UK consumer banking transactions and scoring HCSTC (High-Cost Short-Term Credit) loan applications. The codebase has been refactored into a clean, domain-driven module structure.

## Module Structure

```
openbanking_engine/
├── __init__.py                    # Main entry point with run_open_banking_scoring()
├── config/
│   ├── __init__.py
│   ├── scoring_config.py         # SCORING_CONFIG, PRODUCT_CONFIG
│   └── pfc_mapping_loader.py     # CSV loader for PFC mappings
├── patterns/
│   ├── __init__.py
│   └── transaction_patterns.py   # All pattern dictionaries (INCOME, DEBT, etc.)
├── income/
│   ├── __init__.py
│   └── income_detector.py        # IncomeDetector class for behavioral detection
├── categorisation/
│   ├── __init__.py
│   ├── preprocess.py             # Text normalization, HCSTC lender mapping
│   ├── pattern_matching.py       # Generic pattern matcher (keyword, regex, fuzzy)
│   └── engine.py                 # TransactionCategorizer orchestration
└── scoring/
    ├── __init__.py
    ├── feature_builder.py        # MetricsCalculator (from metrics_calculator.py)
    └── scoring_engine.py         # ScoringEngine with decision logic
```

## Key Components

### 1. Configuration Layer (`config/`)

**scoring_config.py**

- `SCORING_CONFIG`: Score ranges, weights, thresholds, decline rules
- `PRODUCT_CONFIG`: Loan parameters (amounts, terms, interest rates)

**pfc_mapping_loader.py**

- Utility for loading Personal Finance Category (PFC) mappings from CSV
- Enables custom categorization mappings

### 2. Pattern Layer (`patterns/`)

**transaction_patterns.py**

- `INCOME_PATTERNS`: Salary, benefits, pension, gig economy, loans
- `TRANSFER_PATTERNS`: Internal transfers, own account movements
- `DEBT_PATTERNS`: HCSTC/payday lenders, credit cards, BNPL, catalogue credit
- `ESSENTIAL_PATTERNS`: Rent, mortgage, utilities, groceries, transport
- `RISK_PATTERNS`: Gambling, bank charges, failed payments, debt collection
- `POSITIVE_PATTERNS`: Savings activity

### 3. Income Detection Layer (`income/`)

**income_detector.py**

- `IncomeDetector`: Behavioral income detection through recurring patterns
- `RecurringIncomeSource`: Data structure for detected income sources
- Analyzes transaction history to identify legitimate salary/benefits
- Distinguishes income from transfers and loan disbursements

### 4. Categorisation Layer (`categorisation/`)

**preprocess.py**

- Text normalization (uppercase, trimming)
- HCSTC lender name canonicalization
- Internal transfer detection
- PFC mapping utilities

**pattern_matching.py**

- Generic pattern matching engine
- Supports keyword, regex, and fuzzy matching
- Returns match method and confidence score

**engine.py**

- `TransactionCategorizer`: Main categorization orchestrator
- Multi-step categorization pipeline:
  1. Known expense service check
  2. PLAID category validation
  3. Behavioral income detection
  4. Pattern-based matching
  5. Fallback categorization
- Handles PLAID categories and preserves high-confidence signals
- Special handling for loan disbursements and transfers

### 5. Scoring Layer (`scoring/`)

**feature_builder.py** (formerly metrics_calculator.py)

- `MetricsCalculator`: Calculates all financial metrics
- Metric types:
  - `IncomeMetrics`: Total, monthly, stable, gig income; stability scores
  - `ExpenseMetrics`: Housing, utilities, transport, groceries, essentials
  - `DebtMetrics`: HCSTC, credit cards, BNPL; active lenders (from same period as expenses)
  - `AffordabilityMetrics`: Disposable income, DTI ratio, post-loan affordability
  - `BalanceMetrics`: Average balance, overdraft usage, negative balance days
  - `RiskMetrics`: Gambling, bank charges, failed payments, debt collection

**scoring_engine.py**

- `ScoringEngine`: Loan application scoring
- Components:
  - Affordability scoring (DTI, disposable income, post-loan affordability)
  - Income quality scoring (stability, regularity, verification)
  - Account conduct scoring (failed payments, overdraft, balance management)
  - Risk indicators scoring (gambling, HCSTC history)
- Hard decline rules (minimum income, max lenders, max gambling, etc.)
- Mandatory referral rules (bank charges, new credit providers)
- Score-based loan amount and term determination

## Main API

### `run_open_banking_scoring()`

The primary entry point for the scoring system:

```python
from openbanking_engine import run_open_banking_scoring

result = run_open_banking_scoring(
    transactions=[
        {
            "date": "2025-01-15",
            "amount": -2500.0,  # Negative = credit (money in)
            "description": "SALARY FROM ACME LTD",
            "merchant_name": "ACME Ltd",
            "plaid_category": "INCOME_WAGES",
            "plaid_category_primary": "INCOME"
        },
        {
            "date": "2025-01-16",
            "amount": 850.0,  # Positive = debit (money out)
            "description": "RENT TO LANDLORD",
            "merchant_name": "Property Management",
            "plaid_category": "RENT_AND_UTILITIES_RENT",
            "plaid_category_primary": "RENT_AND_UTILITIES"
        }
    ],
    requested_amount=500,
    requested_term=3,
    days_covered=90
)

print(result["decision"])  # "APPROVE", "REFER", or "DECLINE"
print(result["score"])     # Numerical score (0-175)
print(result["max_approved_amount"])  # Maximum approvable amount
```

## Backward Compatibility

All root-level files have been converted to backward compatibility wrappers:

- `transaction_categorizer.py` → imports from `openbanking_engine.categorisation.engine`
- `income_detector.py` → imports from `openbanking_engine.income.income_detector`
- `metrics_calculator.py` → imports from `openbanking_engine.scoring.feature_builder`
- `scoring_engine.py` → imports from `openbanking_engine.scoring.scoring_engine`
- `config/categorization_patterns.py` → imports from `openbanking_engine.patterns` and `openbanking_engine.config`

**Existing code continues to work without changes:**

```python
# Old import style still works
from transaction_categorizer import TransactionCategorizer
from scoring_engine import ScoringEngine, Decision

# New import style
from openbanking_engine import TransactionCategorizer, ScoringEngine, Decision
from openbanking_engine import run_open_banking_scoring
```

## Usage Examples

### Example 1: Basic Categorization

```python
from openbanking_engine import TransactionCategorizer

categorizer = TransactionCategorizer()

# Categorize a salary payment
result = categorizer.categorize_transaction(
    description="SALARY FROM EMPLOYER LTD",
    amount=-2500.0,
    merchant_name="Employer Ltd",
    plaid_category="INCOME_WAGES",
    plaid_category_primary="INCOME"
)

print(f"Category: {result.category}")           # "income"
print(f"Subcategory: {result.subcategory}")     # "salary"
print(f"Confidence: {result.confidence}")       # 0.95
print(f"Weight: {result.weight}")               # 1.0
print(f"Is Stable: {result.is_stable}")         # True
```

### Example 2: Complete Scoring Pipeline

```python
from openbanking_engine import run_open_banking_scoring

# Sample transaction data
transactions = [
    {"date": "2025-01-01", "amount": -2500.0, "description": "SALARY"},
    {"date": "2025-01-05", "amount": 850.0, "description": "RENT"},
    {"date": "2025-01-07", "amount": 120.0, "description": "TESCO"},
    {"date": "2025-01-10", "amount": 80.0, "description": "BRITISH GAS"},
]

# Run complete scoring
result = run_open_banking_scoring(
    transactions=transactions,
    requested_amount=500,
    requested_term=3,
    days_covered=90
)

# Check decision
if result["decision"] == "APPROVE":
    print(f"Approved for £{result['max_approved_amount']} over {result['max_approved_term']} months")
elif result["decision"] == "REFER":
    print(f"Refer for manual review: {result['referral_reasons']}")
else:
    print(f"Declined: {result['decline_reasons']}")

# Access metrics
print(f"Monthly Income: £{result['metrics']['income']['monthly_income']}")
print(f"DTI Ratio: {result['metrics']['affordability']['dti_ratio']}%")
print(f"Disposable: £{result['metrics']['affordability']['monthly_disposable']}")
```

### Example 3: Using Individual Components

```python
from openbanking_engine import (
    TransactionCategorizer,
    MetricsCalculator,
    ScoringEngine
)

# Step 1: Categorize transactions
categorizer = TransactionCategorizer()
categorized = []
for txn in transactions:
    result = categorizer.categorize_transaction(
        description=txn["description"],
        amount=txn["amount"]
    )
    categorized.append({
        "date": txn["date"],
        "amount": txn["amount"],
        "category": result.category,
        "subcategory": result.subcategory,
        "weight": result.weight,
        "is_stable": result.is_stable,
    })

# Step 2: Calculate metrics
calculator = MetricsCalculator()
metrics = calculator.calculate_all_metrics(
    categorized_transactions=categorized,
    days_covered=90
)

# Step 3: Score application
engine = ScoringEngine()
scoring_result = engine.score_application(
    income_metrics=metrics["income"],
    expense_metrics=metrics["expense"],
    debt_metrics=metrics["debt"],
    affordability_metrics=metrics["affordability"],
    balance_metrics=metrics["balance"],
    risk_metrics=metrics["risk"],
    requested_amount=500,
    requested_term=3
)

print(f"Decision: {scoring_result.decision.value}")
print(f"Score: {scoring_result.score}")
```

### Account Transfer Categorization (Updated 2025-12-22)

**PLAID Account Transfers:**

- `TRANSFER_IN_ACCOUNT_TRANSFER` → `income/account_transfer` (weight=1. 0)
- `TRANSFER_OUT_ACCOUNT_TRANSFER` → `expense/account_transfer` (weight=1.0)

**Keyword-Based Transfers:**

- Pattern-matched transfers (e.g., "OWN ACCOUNT") → `transfer/internal` (weight=0.0)

**Rationale:**
PLAID's `ACCOUNT_TRANSFER` category indicates legitimate bank-to-bank transfers that should be included in affordability calculations, unlike internal pot/savings movements which are excluded via keyword matching.

**Impact on Scoring:**

- Account transfers are now included in income/expense totals
- Affects DTI, disposable income, and affordability calculations
- Provides more accurate view of cash flow vs previous exclusion approach

## Design Principles

### 1. Domain-Driven Structure

- Code organized by functional domain (patterns, income, categorisation, scoring)
- Clear separation of concerns
- Each module has a single responsibility

### 2. Preserved Business Logic

- All existing algorithms and calculations maintained
- No changes to scoring rules or categorization patterns
- Backward compatible with existing tests

### 3. Clean Imports

- Relative imports within openbanking_engine package
- Absolute imports from outside
- Clear dependency tree

### 4. Professional Organization

- Configuration separated from logic
- Patterns separated from matching logic
- Feature calculation separated from scoring

## Migration Notes

### What Changed

1. **Structure**: Code moved from monolithic root files to modular package
2. **Imports**: Internal imports updated to use relative imports
3. **Entry Point**: New `run_open_banking_scoring()` function for clean API

### What Stayed the Same

1. **Algorithms**: All categorization and scoring logic preserved
2. **Tests**: All existing tests pass without modification
3. **Public API**: Root-level imports continue to work via wrappers
4. **Patterns**: All pattern definitions unchanged

## Testing

All tests continue to pass with the new structure:

```bash
# Run all tests
python -m unittest discover -s . -p "test_*.py"

# Run specific test suites
python -m unittest test_behavioral_income_detection
python -m unittest test_batch_categorization
python -m unittest test_loan_disbursement_fix
python -m unittest test_plaid_categorization_preservation
```

## Benefits of New Structure

1. **Maintainability**: Easier to find and modify specific functionality
2. **Testability**: Can test individual components in isolation
3. **Extensibility**: Easy to add new categorization patterns or scoring rules
4. **Documentation**: Clear module boundaries make documentation easier
5. **Collaboration**: Team members can work on different modules independently
6. **Professional**: Industry-standard package structure

## Scoring System Documentation

### Overview - 175 Point Scale

The HCSTC scoring system evaluates loan applications on a **175-point scale** (previously 100 points, rescaled by 1.75x). The system balances affordability, income quality, account conduct, and risk indicators to make responsible lending decisions.

**Decision Thresholds:**

- **APPROVE**: 70-175 points - Auto-approved for requested amount/term
- **REFER**: 45-69 points - Manual underwriter review required
- **DECLINE**: 0-44 points - Automatic rejection

### Score Breakdown (175 Points Maximum)

**Component Weights:**

- Affordability: 78.75 points (45%)
- Income Quality: 43.75 points (25%)
- Account Conduct: 35 points (20%)
- Risk Indicators: 17.5 points (10%)

#### 1. Income Quality (43.75 points max)

Evaluates the stability and reliability of income sources.

**Income Stability (0-21 points):**

- 90%+ stability score: 21 points
- 75-89% stability: 17.5 points
- 60-74% stability: 12.25 points
- 40-59% stability: 7 points
- < 40% stability: 0 points
- Stability based on: income type weights, consistency, verification

**Income Regularity (0-14 points):**

- Measures consistency of income timing and amounts
- Calculated from income regularity score (0-100%)
- Points = (regularity_score / 100) × 14
- Maximum: 14 points

**Income Verification (0-8.75 points):**

- Verifiable income (salary, benefits, pension): 8.75 points
- Unverifiable income (other sources): 3.5 points
- Based on income source identification and PLAID categories

#### 2. Affordability (78.75 points max)

Assesses ability to repay the loan without financial hardship.

**DTI Ratio Score (0-31.5 points):**

- < 15% DTI: 31.5 points
- 15-25% DTI: 26.25 points
- 25-35% DTI: 21 points
- 35-45% DTI: 14 points
- 45-55% DTI: 7 points
- > 55% DTI: 0 points

**Disposable Income Score (0-26.25 points):**
Based on monthly disposable income (after expenses, before loan):

- £400+ disposable: 26.25 points
- £300-400 disposable: 22.75 points
- £200-300 disposable: 17.5 points
- £100-200 disposable: 10.5 points
- £50-100 disposable: 5.25 points
- < £50 disposable: 0 points

**Post-Loan Affordability (0-21 points):**

- Calculated as: (post_loan_disposable / 50) × 21
- Maximum: 21 points (£50+ post-loan disposable)
- Ensures adequate buffer after loan repayment

#### 3. Account Conduct (35 points max)

Evaluates banking behavior and financial management.

**Failed Payments (0-14 points):**

- No failed payments: 14 points
- Each failed payment: -3.5 points
- Minimum: 0 points

**Overdraft Usage (0-12.25 points):**

- No overdraft days: 12.25 points
- 1-5 days in overdraft: 8.75 points
- 6-15 days in overdraft: 5.25 points
- 16+ days in overdraft: 0 points

**Balance Management (0-8.75 points):**

- Average balance ≥ £500: 8.75 points
- Average balance £200-£500: 5.25 points
- Average balance £0-£200: 1.75 points
- Average balance < £0: 0 points

#### 4. Risk Indicators (17.5 points max)

Evaluates high-risk financial behaviors.

**Gambling Activity (0-8.75 points):**

- 0% gambling: 8.75 points
- 0-2% gambling: 5.25 points
- 2-5% gambling: 0 points
- 5-10% gambling: -5.25 points (penalty)
- > 10% gambling: -8.75 points (penalty)
- > 15% gambling: Hard decline

**HCSTC History (0-8.75 points):**

- No HCSTC lenders: 8.75 points
- 1 HCSTC lender: 3.5 points
- 2+ HCSTC lenders: 0 points
- 7+ HCSTC lenders: Hard decline

### Hard Decline Rules

These rules trigger **instant rejection** regardless of score:

1. **Minimum Income**: Monthly income < £1,000
2. **No Verified Income**: No identifiable income source and income < £300
3. **Excessive HCSTC**: 7+ active HCSTC lenders in last 90 days
4. **Gambling Threshold**: Gambling > 15% of monthly income
5. **Insufficient Affordability**: Post-loan disposable income < £0 (after 10% expense buffer)
6. **Failed Payments**: 6+ failed payments in last 45 days
7. **Debt Collection**: 4+ distinct debt collection agencies
8. **DTI Too High**: Projected DTI > 75% with new loan

### Mandatory Referral Rules

These trigger manual review (not automatic decline):

1. **Bank Charges**: 3+ bank charges in last 90 days
2. **New Credit Providers**: 5+ new credit providers in last 90 days
3. **Score in REFER range**: 45-69 points

### Affordability Calculation Details

#### Time Period Consistency

**All affordability metrics use the same time basis for fair comparison:**

```
Lookback Period: Last 3 complete calendar months (configurable)
- Income calculations: Based on last N months with income transactions
- Expense calculations: Based on last N complete calendar months
- Debt calculations: Based on last N complete calendar months

This ensures:
- Monthly debt = Total debt (last 3 months) / 3
- Monthly expenses = Total expenses (last 3 months) / 3
- Consistent affordability: Income - Expenses - Debt
```

**Example with concentrated recent debt:**

```
Scenario: 12 months of transaction history
- £1,800 in credit card payments (all in last 3 months)
- Lookback period: 3 months

Correct Calculation:
  Monthly credit card = £1,800 / 3 months = £600/month ✓

Incorrect (old approach):
  Monthly credit card = £1,800 / 12 months = £150/month ✗
  (Understates debt by 4x!)
```

#### Monthly Income Calculation

```
Weighted Income = Σ (Transaction Amount × Income Weight)
Monthly Income = Weighted Income / Lookback Months

Income Weights:
- Salary, Benefits, Pension: 1.0 (100%)
- Gig Economy: 1.0 (100%)
- Other (unverified): 0.5-1.0 (50-100%)
- Loans, Transfers: 0.0 (0%, excluded)
```

#### Monthly Expense Calculation

```
Monthly Expenses = (Essential Expenses + Discretionary Expenses) / Lookback Months
Monthly Debt = (Total Debt Payments) / Lookback Months

Essential Expenses Include:
- Rent/Mortgage (housing costs)
- Council Tax
- Utilities (gas, electric, water)
- Communications (phone, internet, TV licence)
- Transport (fuel, public transport, parking)
- Groceries (food shopping)
- Insurance premiums
- Childcare costs

Debt Payments Include:
- HCSTC/payday loan payments
- Credit card payments
- BNPL payments
- Catalogue credit payments
- Other loan payments

Note: Debt payments are calculated separately from expenses using the same
lookback period to ensure consistent monthly averages.
```

#### Loan Repayment Calculation (FCA Compliant)

```
Daily Interest Rate: 0.8% (FCA cap)
Total Cost Cap: 100% of loan amount (FCA cap)

Monthly Repayment = Loan Amount × (1 + Total Cost) / Term Months
Example: £500 loan for 3 months = £500 × 2.0 / 3 = £333.33/month
```

#### Disposable Income & DTI

```
Monthly Disposable Income (Reported to User): Monthly Disposable = Monthly Income - Actual Expenses - Debt Payments

Affordability Assessment (Internal Stress Test): Expense Shock Buffer: 10% on essential expenses only Buffered Essential Expenses = Essential Expenses × 1.1 Buffered Total Expenses = (Essential × 1.1) + Discretionary

Post-Loan Disposable = Monthly Disposable - Monthly Loan Repayment Affordability Check: Post-Loan Disposable ≥ £50 (minimum buffer)

Note: The 10% shock buffer is applied ONLY for affordability decisions to ensure customers can still afford the loan if essential expenses increase. The monthly disposable income shown to customers uses actual expenses without the buffer.

DTI Ratio = (Total Debt Payments / Gross Income) × 100 Projected DTI = ((Total Debt + New Loan Payment) / Gross Income) × 100
```

### Product Parameters

**Loan Amounts:**

- Minimum: £200
- Maximum: £1,500
- Available in £50 increments

**Loan Terms:**

- Available terms: 3, 4, 5, or 6 months
- Equal monthly installments
- No early repayment penalties

**Interest & Fees:**

- Daily interest rate: 0.8% per day (FCA maximum)
- Total cost cap: 100% of loan amount (FCA maximum)
- No hidden fees or charges
- Transparent pricing

**Score-Based Loan Limits:**

- Score 149+: Max £1,500 over 6 months
- Score 123-148: Max £1,200 over 6 months
- Score 105-122: Max £800 over 5 months
- Score 88-104: Max £500 over 4 months
- Score 70-87: Max £300 over 3 months

**Example Calculations:**

| Loan Amount | Term | Daily Interest | Total Cost Cap | Total Repayable | Monthly Payment |
| ----------- | ---- | -------------- | -------------- | --------------- | --------------- |
| £200        | 3 mo | 0.8%           | £200 (100%)    | £400            | £133.33         |
| £500        | 3 mo | 0.8%           | £500 (100%)    | £1,000          | £333.33         |
| £800        | 5 mo | 0.8%           | £800 (100%)    | £1,600          | £320.00         |
| £1,200      | 6 mo | 0.8%           | £1,200 (100%)  | £2,400          | £400.00         |
| £1,500      | 6 mo | 0.8%           | £1,500 (100%)  | £3,000          | £500.00         |

### FCA Compliance Features

The scoring system implements FCA responsible lending requirements:

**1. Price Cap Enforcement**

- Daily interest capped at 0.8% (FCA maximum)
- Total cost capped at 100% of loan amount
- No charges for late payment beyond cost cap
- Transparent, standardized pricing

**2. Affordability Assessment**

- Comprehensive income verification
- Essential expense consideration
- 10% expense shock buffer for resilience
- Post-loan disposable income check
- DTI ratio monitoring and limits

**3. Income Verification**

- Stable income sources prioritized (weight 1.0)
- PLAID category integration for verification
- Employment income preferred over gig economy
- Loan disbursements excluded (weight 0.0)
- Minimum income thresholds enforced

**4. Responsible Lending Checks**

- Gambling activity monitoring (hard decline at >15%)
- Debt spiral detection (7+ HCSTC lenders)
- Failed payment history review (45-day window)
- Debt collection agency checks
- Bank charge monitoring

**5. Forbearance & Support**

- Clear decline reasons provided
- Referral to manual review when appropriate
- No risk-based pricing (fixed rate product)
- Consumer protection compliance

**6. Creditworthiness Assessment**

- Multi-factor scoring (not just credit score)
- Account conduct evaluation
- Behavioral analysis of banking patterns
- 90-day transaction history analysis
- Comprehensive risk assessment

### Decision Examples

#### Example 1: APPROVE - Strong Applicant

```
Monthly Income: £2,100 (salary, stable)
Monthly Expenses: £950 (rent, utilities, groceries)
Existing Debt: £200/month (credit card)
Requested Loan: £500 for 3 months
Average Balance: £600
No overdraft usage

Scoring:
- Affordability: 70 points (31.5 DTI + 26.25 disposable + 12 post-loan)
- Income Quality: 40 points (21 stability + 12 regularity + 8.75 verification)
- Account Conduct: 35 points (14 no failed + 12.25 no overdraft + 8.75 balance)
- Risk Indicators: 17.5 points (8.75 no gambling + 8.75 no HCSTC)

Total Score: 162.5 points
Decision: APPROVE
Max Approved: £1,500 over 6 months
Post-Loan Disposable: £617/month
```

#### Example 2: REFER - Marginal Applicant

```
Monthly Income: £1,400 (benefits, stable)
Monthly Expenses: £850
Existing Debt: £250/month (1 HCSTC lender, credit card)
Requested Loan: £400 for 3 months
Failed Payments: 2 in last 90 days
Average Balance: £150

Scoring:
- Affordability: 50 points (21 DTI + 22.75 disposable + 6 post-loan)
- Income Quality: 32 points (17.5 stability + 10 regularity + 8.75 verification)
- Account Conduct: 21 points (7 failed penalty + 12.25 no overdraft + 1.75 balance)
- Risk Indicators: 12.25 points (8.75 no gambling + 3.5 one HCSTC)

Total Score: 115.25 points → REFER due to failed payments
Decision: REFER (manual review for failed payments and bank charges)
Recommendation: Review banking behavior, consider lower amount (£300)
```

#### Example 3: DECLINE - High Risk

```
Monthly Income: £900 (gig economy, unstable)
Monthly Expenses: £650
Existing Debt: £380/month (3 HCSTC lenders)
Failed Payments: 4 in last 45 days
Gambling: £85/month (9.4% of income)
Requested Loan: £500 for 3 months

Hard Decline Triggers:
✗ Monthly income < £1,000
✗ 4 failed payments in 45 days (threshold: 5)
✗ 3 HCSTC lenders (borderline - threshold: 6)

Scoring (for reference only):
- Affordability: 12 points (low DTI score, minimal disposable)
- Income Quality: 15 points (low stability, no verification)
- Account Conduct: 0 points (14-point penalty for failed payments)
- Risk Indicators: -3.5 points (0 HCSTC + negative gambling penalty)

Total Score: 23.5 points
Decision: DECLINE (hard decline for income < £1,000)
Reasons: Insufficient income, multiple failed payments, high HCSTC exposure
```

## Future Enhancements

Potential areas for extension:

1. **PFC Mapping**: Implement CSV-based PFC mapping for custom categorizations
2. **ML Models**: Add machine learning models for enhanced categorization
3. **Real-time Scoring**: Implement streaming/real-time transaction scoring
4. **Multi-currency**: Support for non-GBP currencies
5. **API Layer**: REST API wrapper for the scoring engine
6. **Caching**: Add caching for frequently accessed patterns and configs
