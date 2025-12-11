# OpenBanking Engine - Module Structure Documentation

## Overview

The OpenBanking Engine is a clean, professional module structure for scoring High-Cost Short-Term Credit (HCSTC) loan applications using Open Banking transaction data.

## Module Structure

```
openbanking_engine/
├── __init__.py                     # Main entry point with run_open_banking_scoring()
├── config/
│   ├── __init__.py
│   ├── scoring_config.py          # SCORING_CONFIG, PRODUCT_CONFIG
│   └── pfc_mapping_loader.py      # Plaid PFC → engine category mapping (future)
├── patterns/
│   ├── __init__.py
│   └── transaction_patterns.py    # INCOME, DEBT, ESSENTIAL, RISK, POSITIVE patterns
├── income/
│   ├── __init__.py
│   └── income_detector.py         # IncomeDetector + RecurringIncomeSource
├── categorisation/
│   ├── __init__.py
│   ├── preprocess.py              # Normalization, transfer detection
│   ├── pattern_matching.py        # Generic pattern matching utilities
│   └── engine.py                  # TransactionCategorizer (main orchestrator)
└── scoring/
    ├── __init__.py
    ├── feature_builder.py         # MetricsCalculator (aggregates features)
    └── scoring_engine.py          # ScoringEngine (applies rules & scores)
```

## Benefits

### 1. Separation of Concerns
Each module has a single, clear responsibility:
- **config**: Configuration for scoring rules and product parameters
- **patterns**: Transaction categorization patterns (keywords/regex)
- **income**: Behavioral income detection from recurring patterns
- **categorisation**: Transaction categorization orchestration
- **scoring**: Feature aggregation and scoring logic

### 2. Testability
Individual components can be unit tested in isolation:
```python
from openbanking_engine.patterns import INCOME_PATTERNS
from openbanking_engine.income import IncomeDetector
from openbanking_engine.categorisation import TransactionCategorizer
```

### 3. Maintainability
Pattern rules, config, and logic are organized and easy to find:
- Need to update HCSTC lender patterns? → `patterns/transaction_patterns.py`
- Need to change scoring thresholds? → `config/scoring_config.py`
- Need to modify income detection? → `income/income_detector.py`

### 4. Scalability
Config-driven approach allows rule changes without code modifications:
- Pattern dictionaries can be loaded from CSV
- Scoring rules defined in configuration
- New patterns added without touching core logic

### 5. Backward Compatibility
All existing code continues to work:
```python
# Old imports still work
from transaction_categorizer import TransactionCategorizer
from scoring_engine import ScoringEngine
from income_detector import IncomeDetector
from config.categorization_patterns import SCORING_CONFIG

# New imports available
from openbanking_engine import run_open_banking_scoring
from openbanking_engine.config import SCORING_CONFIG, PRODUCT_CONFIG
from openbanking_engine.patterns import INCOME_PATTERNS
```

## Usage

### Basic Usage - Main Entry Point

```python
from openbanking_engine import run_open_banking_scoring

transactions = [
    {
        "description": "ACME CORP SALARY",
        "amount": -2500.00,
        "date": "2024-01-25",
    },
    {
        "description": "TESCO STORES",
        "amount": 45.20,
        "date": "2024-01-26",
    },
    # ... more transactions
]

result = run_open_banking_scoring(
    transactions=transactions,
    loan_amount=500,
    loan_term=4,
    months_of_data=3,
    application_ref="APP-001"
)

print(f"Decision: {result.decision.value}")  # APPROVE, REFER, or DECLINE
print(f"Score: {result.score}")
print(f"Monthly Income: £{result.monthly_income}")
```

### Advanced Usage - Individual Components

```python
from openbanking_engine.categorisation import TransactionCategorizer
from openbanking_engine.scoring import MetricsCalculator, ScoringEngine

# Step 1: Categorize transactions
categorizer = TransactionCategorizer()
categorized = categorizer.categorize_transactions(transactions)
category_summary = categorizer.get_category_summary(categorized)

# Step 2: Calculate metrics
calculator = MetricsCalculator(months_of_data=3)
metrics = calculator.calculate_all_metrics(
    category_summary=category_summary,
    transactions=transactions,
    accounts=[],
    loan_amount=500,
    loan_term=4
)

# Step 3: Score application
engine = ScoringEngine()
result = engine.score_application(
    metrics=metrics,
    requested_amount=500,
    requested_term=4,
    application_ref="APP-001"
)
```

### Configuration Management

```python
from openbanking_engine.config import SCORING_CONFIG, PRODUCT_CONFIG

# Access scoring rules
hard_decline_rules = SCORING_CONFIG["hard_decline_rules"]
min_income = hard_decline_rules["min_monthly_income"]

# Access product parameters
max_loan = PRODUCT_CONFIG["max_loan_amount"]
available_terms = PRODUCT_CONFIG["available_terms"]
```

### Pattern Customization

```python
from openbanking_engine.patterns import INCOME_PATTERNS, DEBT_PATTERNS

# Access income patterns
salary_keywords = INCOME_PATTERNS["salary"]["keywords"]
salary_regex = INCOME_PATTERNS["salary"]["regex_patterns"]

# Access debt patterns
hcstc_lenders = DEBT_PATTERNS["hcstc_payday"]["keywords"]
```

## Migration Guide

### For Existing Code

No changes required! All existing imports continue to work through backward compatibility wrappers:

```python
# These still work exactly as before
from transaction_categorizer import TransactionCategorizer
from scoring_engine import ScoringEngine
from income_detector import IncomeDetector
from metrics_calculator import MetricsCalculator
from config.categorization_patterns import SCORING_CONFIG, PRODUCT_CONFIG
```

### For New Code

Use the new module structure for cleaner imports:

```python
# Recommended for new code
from openbanking_engine import run_open_banking_scoring
from openbanking_engine.config import SCORING_CONFIG, PRODUCT_CONFIG
from openbanking_engine.patterns import INCOME_PATTERNS, DEBT_PATTERNS
from openbanking_engine.categorisation import TransactionCategorizer
from openbanking_engine.scoring import ScoringEngine, MetricsCalculator
from openbanking_engine.income import IncomeDetector
```

## Testing

All existing tests continue to pass:

```bash
# Run all tests
python -m unittest discover -s . -p 'test_*.py'

# Run specific test modules
python -m unittest test_behavioral_income_detection
python -m unittest test_plaid_categorization_preservation
python -m unittest test_batch_categorization
```

## Future Enhancements

1. **PFC Mapping CSV**: Load Plaid category mappings from external CSV
   - Location: `openbanking_engine/config/pfc_mapping_loader.py`
   - Use: `load_pfc_mapping("path/to/mapping.csv")`

2. **Pattern Extraction**: Move preprocessing logic into reusable functions
   - Location: `openbanking_engine/categorisation/preprocess.py`
   - Functions: `normalize_text()`, `detect_internal_transfers()`

3. **Enhanced Pattern Matching**: Improve scoring-based pattern matching
   - Location: `openbanking_engine/categorisation/pattern_matching.py`
   - Functions: `match_pattern_dict()`, `match_keywords()`

4. **Comprehensive Logging**: Add structured logging throughout
5. **Error Handling**: Improve error messages and validation
6. **Documentation**: Add docstrings to all functions
7. **Type Hints**: Complete type annotations for all modules

## Key Features

### Config-Driven Design
- **SCORING_CONFIG**: Weights, thresholds, hard decline rules
- **PRODUCT_CONFIG**: Loan limits, terms, interest rates
- **Pattern dictionaries**: Keyword and regex rules for categorization

### Pattern Matching
- Keyword matching with fuzzy search support
- Regex pattern matching
- Scoring-based best match selection (regex +2, keyword +1)
- PLAID category integration

### Income Detection
- Recurring pattern detection (weekly, monthly)
- Payroll keyword analysis
- Benefits and pension identification
- Gig economy income weighting (70%)

### Transaction Categorization
- Income types: salary, benefits, pension, gig economy
- Debt types: HCSTC, loans, credit cards, BNPL, catalogue
- Essential expenses: rent, mortgage, utilities, transport, groceries
- Risk indicators: gambling, bank charges, failed payments, debt collection
- Positive indicators: savings activity

### Scoring Logic
- **Hard decline rules**: Quick elimination before detailed scoring
- **Score-based limits**: Maps score to max loan amount and term
- **Affordability assessment**: DTI, disposable income, post-loan affordability
- **Risk evaluation**: Gambling, HCSTC history, failed payments
- **Account conduct**: Balance management, overdraft usage

## Audit Trail

All categorization decisions include:
- **Category & subcategory**: Primary classification
- **Confidence score**: 0.0-1.0 indicating match quality
- **Match method**: keyword, regex, fuzzy, or plaid
- **Risk level**: For risk indicators
- **Weight**: Income multiplier (e.g., 0.7 for gig economy)

This enables full explainability for regulatory compliance and customer queries.

## Support

For questions or issues with the OpenBanking Engine:
1. Check this documentation
2. Review inline code comments
3. Run tests to verify expected behavior
4. Examine example usage in `run_open_banking_scoring()`

## Version

OpenBanking Engine v1.0.0 - December 2024
