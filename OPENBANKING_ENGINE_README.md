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
  - `DebtMetrics`: HCSTC, credit cards, BNPL; active lenders
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

#### 1. Income Quality (45 points max)

Evaluates the stability and reliability of income sources.

**Base Income Score (0-25 points):**
- £2000+ monthly: 25 points
- £1500-2000 monthly: 20 points
- £1000-1500 monthly: 15 points
- £500-1000 monthly: 10 points
- £0-500 monthly: 0 points

**Stable Income Bonus (+10 points):**
- Awarded for stable income sources with weight 1.0
- Includes: salary, benefits, pension
- Excludes: gig economy (weight 0.7), loans (weight 0.0)

**Income Consistency (+10 points):**
- Measures variance in income amounts over time
- Low variance (< 10%): 10 points
- Medium variance (10-20%): 5 points
- High variance (> 20%): 0 points

#### 2. Affordability (50 points max)

Assesses ability to repay the loan without financial hardship.

**DTI Ratio Score (0-25 points):**
- < 20% DTI: 25 points
- 20-30% DTI: 20 points
- 30-40% DTI: 15 points
- 40-50% DTI: 10 points
- 50-60% DTI: 5 points
- > 60% DTI: 0 points

**Disposable Income Score (0-25 points):**
Based on monthly disposable income (after expenses, before loan):
- £500+ disposable: 25 points
- £400-500 disposable: 20 points
- £300-400 disposable: 15 points
- £200-300 disposable: 10 points
- £100-200 disposable: 5 points
- < £100 disposable: 0 points

#### 3. Account Conduct (35 points max)

Evaluates banking behavior and financial management.

**Clean Conduct Baseline:**
- No failed payments: 35 points (baseline)
- No bank charges: 35 points (baseline)
- No overdraft issues: 35 points (baseline)

**Penalties Applied:**
- Failed payment (last 45 days): -5 points each
- Bank charge (last 90 days): -3 points each
- Frequent overdraft usage: -10 points
- Minimum score: 0 points (cannot go negative)

#### 4. Debt Profile (25 points max)

Examines existing credit commitments and HCSTC exposure.

**HCSTC Lender Count (0-15 points):**
- No HCSTC lenders: 15 points
- 1 HCSTC lender: 10 points
- 2 HCSTC lenders: 5 points
- 3+ HCSTC lenders: 0 points

**Credit Diversity Bonus (+10 points):**
- Awarded for managed credit without excess
- Requires: active credit, no excessive borrowing
- Indicates responsible credit management

#### 5. Risk Factors (20 points max)

Evaluates high-risk financial behaviors.

**No Gambling Activity (+10 points):**
- No gambling in last 90 days: 10 points
- Gambling present: 0-10 points (sliding scale)
- > 15% of income on gambling: Hard decline

**No Debt Collection Activity (+10 points):**
- No DCA activity: 10 points
- Active debt collection: 0 points
- 4+ DCAs: Hard decline

**Savings Activity Bonus (+5 points):**
- Evidence of savings behavior: +5 bonus points
- Optional enhancement to total score

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

#### Monthly Income Calculation
```
Weighted Income = Σ (Transaction Amount × Income Weight)
Monthly Income = Weighted Income / Months of Data

Income Weights:
- Salary, Benefits, Pension: 1.0 (100%)
- Gig Economy: 0.7 (70%)
- Other (unverified): 0.5-1.0 (50-100%)
- Loans, Transfers: 0.0 (0%, excluded)
```

#### Monthly Expense Calculation
```
Monthly Expenses = (Total Debt Payments + Essential Expenses) / Months

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
Expense Shock Buffer: 10% (multiplier: 1.1)
Buffered Expenses = Monthly Expenses × 1.1

Monthly Disposable = Monthly Income - Buffered Expenses
Post-Loan Disposable = Monthly Disposable - Monthly Loan Repayment

DTI Ratio = (Total Debt Payments / Gross Income) × 100
Projected DTI = ((Total Debt + New Loan Payment) / Gross Income) × 100
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
|-------------|------|----------------|----------------|-----------------|-----------------|
| £200        | 3 mo | 0.8%          | £200 (100%)    | £400            | £133.33         |
| £500        | 3 mo | 0.8%          | £500 (100%)    | £1,000          | £333.33         |
| £800        | 5 mo | 0.8%          | £800 (100%)    | £1,600          | £320.00         |
| £1,200      | 6 mo | 0.8%          | £1,200 (100%)  | £2,400          | £400.00         |
| £1,500      | 6 mo | 0.8%          | £1,500 (100%)  | £3,000          | £500.00         |

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

Scoring:
- Income Quality: 35 points (25 base + 10 stable)
- Affordability: 45 points (20 DTI + 25 disposable)
- Account Conduct: 35 points (clean record)
- Debt Profile: 25 points (15 no HCSTC + 10 diversity)
- Risk Factors: 20 points (10 no gambling + 10 no DCA)

Total Score: 160 points
Decision: APPROVE
Max Approved: £1,500 over 6 months
```

#### Example 2: REFER - Marginal Applicant
```
Monthly Income: £1,400 (benefits, stable)
Monthly Expenses: £850
Existing Debt: £250/month (1 HCSTC lender, credit card)
Bank Charges: 2 in last 90 days
Requested Loan: £400 for 3 months

Scoring:
- Income Quality: 25 points (15 base + 10 stable)
- Affordability: 30 points (15 DTI + 15 disposable)
- Account Conduct: 29 points (35 - 6 penalties)
- Debt Profile: 20 points (10 one HCSTC + 10 diversity)
- Risk Factors: 20 points (10 no gambling + 10 no DCA)

Total Score: 124 points → Adjusted to 62 after review
Decision: REFER (manual review for bank charges)
Recommendation: Review banking behavior, consider lower amount
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
- Monthly income < £1,000
- 3+ HCSTC lenders (borderline)
- 4 failed payments in 45 days

Scoring (for reference):
- Income Quality: 10 points
- Affordability: 10 points
- Account Conduct: 15 points (20 penalty applied)
- Debt Profile: 5 points
- Risk Factors: 5 points

Total Score: 45 points (but hard declined)
Decision: DECLINE
Reasons: Multiple failed payments, insufficient income, high HCSTC exposure
```

## Future Enhancements

Potential areas for extension:

1. **PFC Mapping**: Implement CSV-based PFC mapping for custom categorizations
2. **ML Models**: Add machine learning models for enhanced categorization
3. **Real-time Scoring**: Implement streaming/real-time transaction scoring
4. **Multi-currency**: Support for non-GBP currencies
5. **API Layer**: REST API wrapper for the scoring engine
6. **Caching**: Add caching for frequently accessed patterns and configs


