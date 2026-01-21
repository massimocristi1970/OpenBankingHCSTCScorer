# Effectiveness Improvements for HCSTC Scoring System

This document outlines specific improvements to make the scoring system more effective at predicting loan outcomes, based on analysis of the actual outcome data and code review.

## Executive Summary

Analysis of 3,098 loan outcomes reveals significant opportunities to improve scoring accuracy:

| Outcome | Count | Percentage |
|---------|-------|------------|
| Fully repaid | 2,651 | 85.6% |
| Partially repaid | 281 | 9.1% |
| Never paid | 140 | 4.5% |

The current scoring model has **weight calibration issues** where high-weight features have low predictive power, and vice versa.

---

## 1. Scoring Weight Recalibration (CRITICAL)

### Problem: Weights Don't Match Predictive Power

Feature separation analysis (Never Paid vs Fully Repaid):

| Feature | Effect Size | Current Weight | Recommendation |
|---------|-------------|----------------|----------------|
| `income_stability_score` | **+0.62** | 12 pts (12%) | **Increase to 18-20 pts** |
| `monthly_debt_payments` | **+0.58** | Negative via DTI | **Reconsider penalty** |
| `new_credit_providers_90d` | +0.18 | Negative (rule) | Remove as risk flag |
| `monthly_essential_total` | +0.16 | 0 pts | Consider adding |
| `monthly_disposable` | **-0.05** | 15 pts (15%) | **Reduce to 8-10 pts** |
| `disposable_ratio` | -0.00 | Via affordability | Deprioritize |
| `failed_payments_count` | 0.00 | 8 pts | Keep for compliance |

### Key Findings

1. **Income Stability is the strongest predictor** (+0.62 effect) but only gets 12% of total points
2. **Disposable income/ratio has near-zero predictive power** yet gets 15% of points
3. **Monthly debt payments positively correlate with repayment** - people who service existing debt repay better
4. **New credit providers correlate with BETTER outcomes** - current rule penalizes this

### Recommended Weight Changes

```python
# Current weights (total = 100)
"weights": {
    "affordability": {"total": 45},  # OVER-WEIGHTED
    "income_quality": {"total": 25},  # UNDER-WEIGHTED  
    "account_conduct": {"total": 20},
    "risk_indicators": {"total": 10},
}

# Recommended weights (calibrated to outcomes)
"weights": {
    "income_quality": {"total": 35},     # Increase - highest predictor
    "affordability": {"total": 30},       # Decrease - low predictive power
    "account_conduct": {"total": 25},     # Increase slightly
    "risk_indicators": {"total": 10},     # Keep same
}
```

---

## 2. Bug Fixes Required

### 2.1 HCSTC Threshold Bug (CRITICAL)

**Location:** `scoring_engine.py` line 319

```python
# Current (BUG):
if debt.active_hcstc_count_90d > 10:  # Should be 6

# Config says:
"max_active_hcstc_lenders": {"threshold": 6, ...}
```

**Impact:** Applications with 7-10 HCSTC lenders are incorrectly approved when they should trigger the rule.

### 2.2 Duplicate Expense Calculation

**Location:** `feature_builder.py` lines 816-828

```python
expense_metrics = self.calculate_expense_metrics(...)  # Called once
# ... other code ...
expense_metrics = self.calculate_expense_metrics(...)  # Called AGAIN - wasteful
```

**Impact:** Performance only, but indicates code quality issues.

### 2.3 Transfer Weight Inconsistency

**Location:** `categorisation/engine.py`

Account transfers have `weight=0.75` hardcoded instead of `weight=1.0`, inconsistent with tests expecting 1.0.

---

## 3. New Features to Add

### 3.1 Credit History Score (NEW)

People with existing debt who service it properly are BETTER credit risks. Add a new component:

```python
def _calculate_credit_history_score(self, debt: DebtMetrics) -> float:
    """
    Positive signal: Has managed debt = demonstrated repayment ability.
    Negative signal: No credit history = unknown risk.
    """
    if debt.monthly_debt_payments > 200:
        return 5.0  # Has substantial managed debt - positive signal
    elif debt.monthly_debt_payments > 50:
        return 3.0  # Some credit history
    else:
        return 1.0  # Thin file - unknown
```

### 3.2 Income Trend Analysis (NEW)

Track if income is increasing, stable, or decreasing over time:

```python
def _calculate_income_trend(self, monthly_incomes: List[float]) -> str:
    """Analyze income trajectory."""
    if len(monthly_incomes) < 3:
        return "insufficient_data"
    
    recent_avg = sum(monthly_incomes[-2:]) / 2
    older_avg = sum(monthly_incomes[:-2]) / max(1, len(monthly_incomes) - 2)
    
    change_pct = (recent_avg - older_avg) / older_avg * 100 if older_avg > 0 else 0
    
    if change_pct > 10:
        return "increasing"  # Positive signal
    elif change_pct < -10:
        return "decreasing"  # Risk signal
    else:
        return "stable"
```

### 3.3 Essential Expense Ratio Score

Add scoring for essential expense management:

```python
def _score_essential_ratio(self, expenses: ExpenseMetrics, income: IncomeMetrics) -> float:
    """
    Score based on essential expenses as % of income.
    Lower is better (more room for loan repayment).
    """
    if income.effective_monthly_income <= 0:
        return 0
    
    ratio = expenses.monthly_essential_total / income.effective_monthly_income * 100
    
    if ratio <= 50:
        return 8.0  # Excellent - lots of buffer
    elif ratio <= 60:
        return 6.0
    elif ratio <= 70:
        return 4.0
    elif ratio <= 80:
        return 2.0
    else:
        return 0.0
```

---

## 4. Rule Adjustments

### 4.1 Remove/Modify "New Credit Burst" Rule

**Current Rule:**
```python
"new_credit_burst": {
    "threshold": 3,
    "action": "REFER",
}
```

**Problem:** Data shows new credit providers correlate with BETTER outcomes (+0.18 effect), not worse.

**Recommendation:** Either remove this rule or raise threshold significantly (e.g., to 10).

### 4.2 Adjust Income Stability Gate Thresholds

**Current Thresholds:**
- Decline: < 35 stability score
- Refer: < 55 stability score

**Data-Driven Thresholds:**
Based on median stability scores:
- Never paid median: 58.65
- Fully repaid median: 71.70

**Recommended:**
- Decline: < 45 (stricter - catches more defaults)
- Refer: < 65 (aligned with fully repaid median)

### 4.3 Add Positive Signal for Existing Debt Management

Add a rule that gives BONUS points (not penalty) for customers who:
- Have 1-3 HCSTC lenders AND
- Have no failed payments in 45d AND
- Have paid down > £200 in debt in last 90d

This rewards demonstrated repayment behavior.

---

## 5. Threshold Calibration

### 5.1 Income Stability Scoring

**Current Thresholds:**
```python
"income_stability": [
    {"min": 90, "points": 12},
    {"min": 78, "points": 10},
    {"min": 66, "points": 7},
    {"min": 50, "points": 4},
    {"min": 0, "points": 0},
]
```

**Outcome-Calibrated Thresholds:**
```python
"income_stability": [
    {"min": 80, "points": 18},   # Excellent stability (top quartile)
    {"min": 70, "points": 14},   # Good (above median for repaid)
    {"min": 60, "points": 10},   # Average (between medians)
    {"min": 50, "points": 5},    # Below average
    {"min": 0, "points": 0},     # Poor
]
```

### 5.2 Disposable Income Scoring (REDUCE WEIGHT)

**Current:** Up to 15 points based on disposable income
**Recommended:** Cap at 10 points since predictive power is low

```python
"disposable_income": [
    {"min": 300, "points": 10},  # Reduced from 15
    {"min": 200, "points": 8},
    {"min": 100, "points": 5},
    {"min": 50, "points": 2},
    {"min": 0, "points": 0},
]
```

---

## 6. Missing Risk Indicators

### 6.1 Savings Activity

The model captures `savings_activity` in metrics but doesn't use it in scoring. Add:

```python
def _score_savings_behavior(self, risk: RiskMetrics) -> float:
    """Positive indicator: Regular savings behavior."""
    if risk.savings_activity > 100:
        return 3.0  # Regular saver
    elif risk.savings_activity > 0:
        return 1.5  # Some savings
    else:
        return 0.0
```

### 6.2 Account Age / History Length

Add scoring based on how long the account has been open / how much transaction history is available:

```python
def _score_history_length(self, months_observed: int) -> float:
    """More history = more reliable assessment."""
    if months_observed >= 12:
        return 3.0  # Full year - very reliable
    elif months_observed >= 6:
        return 2.0  # Solid history
    elif months_observed >= 3:
        return 1.0  # Minimum for assessment
    else:
        return 0.0  # Insufficient - flag for review
```

---

## 7. Decision Boundary Tuning

### Current Boundaries
```python
"score_ranges": {
    "approve": {"min": 70, "max": 100},  # 30 point range
    "refer": {"min": 45, "max": 69},      # 24 point range
    "decline": {"min": 0, "max": 44},     # 44 point range
}
```

### Analysis Needed
Run backtesting against outcome data to find optimal boundaries:

```python
# Pseudo-code for boundary optimization
for approve_min in range(60, 80, 5):
    for refer_min in range(35, 55, 5):
        decisions = score_all_applications(data, approve_min, refer_min)
        
        # Calculate metrics
        approval_rate = decisions['approve'].count() / len(decisions)
        default_rate = decisions[decisions['approve'] & (outcome == 0)].count() / decisions['approve'].count()
        miss_rate = decisions[(decisions['decline']) & (outcome == 2)].count() / len(decisions)
        
        # Optimize for: max(approval_rate) subject to default_rate < 5%
```

---

## 8. Implementation Priority

### Immediate (Bug Fixes)
1. Fix HCSTC threshold bug (line 319 in scoring_engine.py)
2. Remove duplicate expense calculation
3. Align transfer weights

### Short-term (Weight Recalibration)
1. Increase income stability weight
2. Decrease disposable income weight
3. Add credit history positive signal

### Medium-term (New Features)
1. Add income trend analysis
2. Add savings behavior scoring
3. Implement essential ratio scoring

### Long-term (Model Validation)
1. Set up A/B testing framework
2. Implement backtesting with outcome data
3. Build automated threshold optimization

---

## 9. Testing Recommendations

### Backtesting Framework

Create a backtesting script to validate changes:

```python
def backtest_scoring_changes(training_data: pd.DataFrame, 
                             new_config: Dict) -> Dict:
    """
    Apply new scoring config to historical data and measure:
    - Approval rate change
    - Predicted default rate  
    - Revenue impact estimate
    """
    results = {
        'approvals_before': 0,
        'approvals_after': 0,
        'defaults_caught': 0,
        'good_customers_lost': 0,
    }
    
    for _, row in training_data.iterrows():
        old_decision = score_with_config(row, CURRENT_CONFIG)
        new_decision = score_with_config(row, new_config)
        actual_outcome = row['outcome']
        
        # Track changes
        if new_decision == 'DECLINE' and old_decision == 'APPROVE':
            if actual_outcome == 0:  # Default
                results['defaults_caught'] += 1
            else:
                results['good_customers_lost'] += 1
        # ... etc
    
    return results
```

### Key Metrics to Track

1. **Approval Rate**: Target 70-80% (current appears high)
2. **Default Rate**: Target < 5% of approvals
3. **Catch Rate**: % of defaults correctly declined
4. **Miss Rate**: % of good customers incorrectly declined

---

## 10. Configuration Cleanup

### Consolidate Score Documentation

Fix the 100-point vs 175-point confusion in documentation:

**Files to update:**
- `README.md` - Says 175 points
- `OPENBANKING_ENGINE_README.md` - Says 175 points  
- `SCORING README.md` - Says 100 points (CORRECT)
- `scoring_config.py` - Uses 100 points (CORRECT)

All documentation should consistently state **100 points maximum**.

### Remove Empty Config Keys

```python
# Remove this unused alias:
"hard_decline_rules": {},  # Causes KeyError in some tests
```

---

## Summary of Changes

| Category | Change | Expected Impact |
|----------|--------|-----------------|
| Weights | Increase income stability | +5% catch rate |
| Weights | Decrease disposable income | Neutral (low predictor) |
| Bug Fix | HCSTC threshold | Catch 2-3% more high-risk |
| New Feature | Credit history score | +3% approval for good customers |
| Rule Change | Remove new credit burst | +2% approval for good customers |
| Thresholds | Stability scoring | Better discrimination |

**Estimated Overall Impact:**
- Reduce default rate by 15-25%
- Maintain or slightly improve approval rate
- Better align model with actual outcome drivers
