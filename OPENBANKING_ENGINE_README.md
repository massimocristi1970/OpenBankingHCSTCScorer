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

## Future Enhancements

Potential areas for extension:

1. **PFC Mapping**: Implement CSV-based PFC mapping for custom categorizations
2. **ML Models**: Add machine learning models for enhanced categorization
3. **Real-time Scoring**: Implement streaming/real-time transaction scoring
4. **Multi-currency**: Support for non-GBP currencies
5. **API Layer**: REST API wrapper for the scoring engine
6. **Caching**: Add caching for frequently accessed patterns and configs

## Support

For questions or issues with the new module structure:
1. Review this README
2. Check the example_openbanking_usage.py for code examples
3. Run existing tests to validate setup
4. Refer to inline documentation in module files
