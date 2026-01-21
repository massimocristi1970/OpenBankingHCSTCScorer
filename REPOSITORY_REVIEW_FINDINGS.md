# Repository Review Findings: OpenBankingHCSTCScorer

**Review Date:** January 21, 2026  
**Branch:** cursor/repository-review-findings-1b64

## Executive Summary

This document details the findings from a comprehensive code review of the OpenBankingHCSTCScorer repository. Several critical issues were identified that could affect loan decisioning and analysis accuracy.

---

## Repository Overview

The OpenBankingHCSTCScorer is a **High-Cost Short-Term Credit (HCSTC) loan scoring system** for UK lenders operating under FCA regulation. It:

- Processes Open Banking transaction data (PLAID format)
- Categorizes transactions (income, expenses, debt, risk indicators)
- Calculates financial metrics (income, expenses, affordability, balance, risk)
- Produces credit scores and automated lending decisions (APPROVE/REFER/DECLINE)
- Generates FCA-compliant loan offers with price cap enforcement

### Architecture

```
openbanking_engine/
├── categorisation/     # Transaction categorization logic
│   └── engine.py      # TransactionCategorizer class
├── config/            # Configuration
│   └── scoring_config.py  # SCORING_CONFIG, PRODUCT_CONFIG
├── income/            # Income detection
│   └── income_detector.py  # Behavioral income detection
├── patterns/          # Pattern matching
│   └── transaction_patterns.py  # INCOME, DEBT, ESSENTIAL, RISK patterns
└── scoring/           # Scoring logic
    ├── feature_builder.py  # MetricsCalculator
    └── scoring_engine.py   # ScoringEngine, Decision logic
```

---

## Critical Issues Affecting Decisioning

### 1. SCORING SCALE MISMATCH (CRITICAL)

**Location:** `scoring_config.py` vs documentation (README.md, OPENBANKING_ENGINE_README.md)

**Problem:** Documentation describes a 175-point scoring scale with rescaled thresholds, but the actual code uses a 100-point scale.

| Aspect | Documentation | Actual Code |
|--------|---------------|-------------|
| Max Score | 175 | 100 |
| Approve Threshold | ≥70 | ≥70 |
| Affordability Weight | 78.75 | 45 |
| Income Quality Weight | 43.75 | 25 |
| Account Conduct Weight | 35 | 20 |
| Risk Indicators Weight | 17.5 | 10 |

**Code Evidence (scoring_config.py):**
```python
"score_ranges": {
    "approve": {"min": 70, "max": 100, "decision": "APPROVE"},  # Not 175
    ...
}
"weights": {
    "affordability": {"total": 45, ...},  # Not 78.75
    ...
}
```

**Impact:**
- Score interpretation fundamentally different than documented
- Any integration or reporting based on documentation will be incorrect
- 9+ test failures related to this mismatch

**Recommendation:** Decide on one scoring scale and align code, documentation, and tests.

---

### 2. HCSTC LENDER THRESHOLD BUG (HIGH)

**Location:** `scoring_engine.py`, line ~318

**Problem:** The HCSTC lender count rule checks for `> 10` but the configuration specifies threshold of 6.

**Configuration (scoring_config.py):**
```python
"max_active_hcstc_lenders": {
    "threshold": 6,  # 7+ should trigger
    "action": "DECLINE",
    ...
}
```

**Actual Code (scoring_engine.py):**
```python
if (
    debt.active_hcstc_count_90d is not None
    and debt.active_hcstc_count_90d > 10  # WRONG: Should be > 6
):
    reason = (...)
    refer_reasons.append(reason)
```

**Impact:**
- Applicants with 7-10 active HCSTC lenders are NOT being flagged
- Potential regulatory risk (FCA guidelines on debt spiral prevention)
- Higher-risk applicants may be approved inappropriately

**Recommendation:** Change `> 10` to `> rule["threshold"]` (which is 6).

---

### 3. ACCOUNT TRANSFER WEIGHT INCONSISTENCY (MEDIUM)

**Location:** `categorisation/engine.py`, lines 466-470 and 489-495

**Problem:** Account transfers (`TRANSFER_IN_ACCOUNT_TRANSFER` and `TRANSFER_OUT_ACCOUNT_TRANSFER`) are assigned weight 0.75, but tests and documentation expect weight 1.0.

**Code:**
```python
if "ACCOUNT_TRANSFER" in detailed_upper:
    return CategoryMatch(
        category="income",
        subcategory="account_transfer",
        weight=0.75,  # Tests expect 1.0
        ...
    )
```

**Impact:**
- Account transfer income is discounted by 25%
- May understate total income for affordability calculations
- 8+ test failures

**Recommendation:** Clarify business intent and align code with tests (likely should be 1.0).

---

### 4. MISSING METHOD / API MISMATCH (HIGH)

**Location:** Tests reference `_check_hard_decline_rules()` but method is `_check_rule_violations()`

**Problem:**
```python
# Tests call:
decline_reasons = self.scoring_engine._check_hard_decline_rules(...)

# Actual method signature:
def _check_rule_violations(self, ...) -> Tuple[List[str], List[str]]:
```

**Impact:**
- 4 test failures with AttributeError
- Indicates API drift between tests and implementation

**Recommendation:** Update tests to use `_check_rule_violations()`.

---

### 5. CONFIGURATION KEY MISMATCH (HIGH)

**Location:** `scoring_config.py`

**Problem:** Tests expect `SCORING_CONFIG["hard_decline_rules"]` to contain rule definitions, but it's an empty dict. Rules are under `SCORING_CONFIG["rules"]`.

**Code:**
```python
"hard_decline_rules": {},  # Empty - backward compatibility alias
"rules": {
    "min_monthly_income": {"threshold": 1500, ...},
    ...
}
```

**Impact:**
- Tests fail with KeyError
- Backward compatibility layer is incomplete

**Recommendation:** Either populate `hard_decline_rules` or update tests to use `rules`.

---

## Medium-Priority Issues

### 6. Income Month Calculation Edge Cases

**Location:** `scoring/feature_builder.py`, `_filter_last_n_income_months()`

**Problem:** The current month is excluded from income calculations (correctly), but test expectations don't account for this.

**Test Failures:**
```
AssertionError: 1666.67 != 2000 within 0 places
AssertionError: 3750.0 != 2500.0 within 2 places
```

**Impact:** Income calculations may differ from expectations when transaction data spans partial months.

---

### 7. Behavioral Gate Log Message Inconsistency

**Location:** `scoring_engine.py`, line ~289

**Problem:** Code checks `< 35` but log message says `< 30`:

```python
if income.income_stability_score < 35:
    decline_reasons.append(
        f"...income stability score ({income.income_stability_score:.1f} < 30)"  # Says 30
    )
```

**Impact:** Confusing decline reason messages.

---

### 8. Duplicate Code Block

**Location:** `scoring/feature_builder.py`, `calculate_all_metrics()`, lines 821-828

**Problem:** `calculate_expense_metrics()` is called twice identically:

```python
expense_metrics = self.calculate_expense_metrics(...)  # First call
...
expense_metrics = self.calculate_expense_metrics(...)  # Duplicate call
```

**Impact:** Unnecessary computation, minor performance impact.

---

## Low-Priority Issues

### 9. Debug Logging in Production Code

**Location:** Multiple files

**Problem:** `print()` statements and debug logging enabled:

```python
print(f"RULE6_DEBUG: failed_45d={failed_45d} ...")
print(f"[DEBUG] effective_income={effective_income}...")
print(f"[AFFORDABILITY] Income £{effective_income:.2f} | ...")
```

**Impact:** Cluttered logs, potential information disclosure.

### 10. Unused Import

**Location:** `scoring_engine.py`, line 10

```python
from openbanking_engine import income  # Unused
```

---

## DTI Scoring Threshold Discrepancy

**Documentation states:**
| DTI Range | Points |
|-----------|--------|
| ≤15% | 31.5 |
| 15-25% | 26.25 |
| 25-35% | 21 |
| 35-45% | 14 |
| 45-55% | 7 |
| >55% | 0 |

**Actual Code (scoring_config.py):**
```python
"dti_ratio": [
    {"max": 30, "points": 18},
    {"max": 40, "points": 15},
    {"max": 50, "points": 12},
    {"max": 60, "points": 8},
    {"max": 70, "points": 4},
    {"max": 100, "points": 0},
]
```

**Impact:** Different scoring outcomes than documented.

---

## Test Suite Status

| Test Category | Status | Issues |
|---------------|--------|--------|
| Batch Categorization | PASS | - |
| Behavioral Income Detection | PASS | - |
| Comprehensive Categorization | PASS | - |
| Debt Time Basis | PASS | - |
| Enhanced Categorization | PASS | - |
| Income Calculation Fix | PASS | - |
| Rescaled Scoring | FAIL | Score scale mismatch |
| Scoring Configuration Updates | FAIL | Key errors, API mismatch |
| Strict PLAID Categories | FAIL | Weight mismatch |
| Transfer Fix | PARTIAL | Some weight issues |

**Test Failures Summary:**
- 27+ tests failing
- Primary causes: Score scale mismatch, API changes not reflected in tests

---

## Recommendations

### Immediate Actions (Critical)

1. **Fix HCSTC lender threshold** - Change `> 10` to `> rule["threshold"]` in `_check_rule_violations()`
2. **Align scoring scale** - Decide on 100 or 175 points and update everything consistently
3. **Fix configuration keys** - Ensure `hard_decline_rules` contains actual rules if tests expect them

### Short-Term Actions (High)

4. **Update tests** - Replace `_check_hard_decline_rules` with `_check_rule_violations`
5. **Standardize account transfer weight** - Align code and tests on 0.75 or 1.0
6. **Fix duplicate method call** - Remove duplicate `calculate_expense_metrics()` call

### Medium-Term Actions

7. **Remove debug logging** - Remove or conditionalize print statements
8. **Add configuration validation** - Validate config keys on engine initialization
9. **Update documentation** - Ensure README accurately reflects actual code behavior
10. **Fix log message** - Update behavioral gate message from 30 to 35

---

## Conclusion

The codebase is well-structured with good separation of concerns, but there are significant discrepancies between documentation and implementation that could lead to:

1. **Incorrect decisioning** - HCSTC lender count bug allows higher-risk applicants through
2. **Misaligned expectations** - Score scale documentation doesn't match reality
3. **Test rot** - Many tests are failing due to API/config drift

These issues should be addressed before production use to ensure accurate, compliant lending decisions.
