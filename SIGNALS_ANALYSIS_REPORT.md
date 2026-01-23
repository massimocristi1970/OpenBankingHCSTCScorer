# Signals Analysis Report
## Open Banking Default Prediction Signals

**Generated from:** 3,072 UK loan applications (CRA-approved population)  
**Default rate:** 4.6% (140 never paid)

---

## Executive Summary

This analysis identifies behavioral signals from Open Banking data that correlate with loan default. The key finding is that **individual signals are weak, but combined signals are strong**.

### Key Insight for US Market

This dataset contains only CRA-approved loans. The 140 defaulters are the hardest cases - they passed CRA screening but still defaulted. For the US market without CRA pre-filtering:
- Expect **wider score distributions** (more variation)
- Expect **stronger signal separation** (clearer patterns)
- These signals should perform **better** on a general population

---

## Signal 1: Income Stability (STRONG)

| Band | Applications | Defaults | Default Rate | Risk Level |
|------|-------------|----------|--------------|------------|
| Very Low (0-30) | 205 | 22 | **10.7%** | HIGH RISK |
| Low (30-45) | 210 | 11 | 5.2% | ELEVATED |
| Medium (45-60) | 639 | 40 | 6.3% | ELEVATED |
| Good (60-75) | 784 | 38 | 4.8% | NORMAL |
| Excellent (75+) | 1,234 | 29 | **2.4%** | LOW RISK |

**Action:** Primary scoring factor. Already weighted at 20 points.

---

## Signal 2: Debt Management (COUNTERINTUITIVE)

| Band | Applications | Defaults | Default Rate | Risk Level |
|------|-------------|----------|--------------|------------|
| Minimal (<£100) | 488 | 54 | **11.1%** | HIGH RISK |
| Low (£100-300) | 449 | 27 | 6.0% | ELEVATED |
| Medium (£300-500) | 350 | 16 | 4.6% | NORMAL |
| High (£500-1000) | 808 | 22 | 2.7% | LOW RISK |
| Very High (£1000+) | 977 | 21 | **2.1%** | LOW RISK |

**Key Finding:** LOWER debt payments = HIGHER default risk

**Interpretation:** People actively managing debt demonstrate they CAN manage credit. "Thin file" customers with no debt history are actually riskier.

**Action:** Reward evidence of debt management, don't penalize it.

---

## Signal 3: Credit Activity (COUNTERINTUITIVE)

| Band | Applications | Defaults | Default Rate | Risk Level |
|------|-------------|----------|--------------|------------|
| Very Low (0-5) | 690 | 60 | **8.7%** | HIGH RISK |
| Low (6-10) | 622 | 35 | 5.6% | ELEVATED |
| Medium (11-20) | 801 | 27 | 3.4% | NORMAL |
| High (21-30) | 372 | 7 | 1.9% | LOW RISK |
| Very High (30+) | 587 | 11 | **1.9%** | LOW RISK |

**Key Finding:** FEWER credit providers = HIGHER default risk

**Interpretation:** Credit-active customers are more reliable. They have established relationships and manage multiple accounts successfully.

**Action:** Don't penalize credit activity. Consider rewarding it.

---

## Signal 4: Debt-to-Income Ratio (COUNTERINTUITIVE)

| Band | Applications | Defaults | Default Rate | Risk Level |
|------|-------------|----------|--------------|------------|
| Very Low (<10%) | 1,002 | 87 | **8.7%** | HIGH RISK |
| Low (10-20%) | 665 | 17 | 2.6% | LOW RISK |
| Medium (20-30%) | 575 | 18 | 3.1% | NORMAL |
| High (30-50%) | 591 | 12 | 2.0% | LOW RISK |
| Very High (50%+) | 239 | 6 | 2.5% | NORMAL |

**Key Finding:** Very LOW DTI = HIGHER default risk

**Interpretation:** Very low DTI often means "thin file" - no credit history. These customers are unknown quantities.

---

## Signal 5: Combined Risk Flags (STRONGEST SIGNAL)

**Risk Flags Used:**
- Low income stability (<50)
- Low debt management (<£200/month)
- Low credit activity (<10 providers)
- No savings (<£5)

| Flags | Applications | Defaults | Default Rate | Lift | Risk Level |
|-------|-------------|----------|--------------|------|------------|
| 0 | 85 | 1 | 1.2% | 0.26x | VERY LOW |
| 1 | 1,446 | 31 | 2.1% | 0.47x | LOW |
| 2 | 842 | 35 | 4.2% | 0.91x | NORMAL |
| **3** | **562** | **50** | **8.9%** | **1.95x** | **HIGH RISK** |
| **4** | **137** | **23** | **16.8%** | **3.68x** | **VERY HIGH** |

**This is the most actionable signal!** 

- 3+ flags = mandatory referral
- 4 flags = serious concern (16.8% default rate vs 4.6% baseline)

---

## Recommended Implementation

### Mandatory Referral Triggers
```
IF risk_flag_count >= 3:
    REFER for manual review
    
IF income_stability_score < 40 AND monthly_debt_payments < 100:
    REFER for manual review
```

### Score Adjustments (Negative)
| Condition | Adjustment | Rationale |
|-----------|------------|-----------|
| income_stability_score < 50 | -5 points | Strong signal |
| monthly_debt_payments < 200 | -3 points | Thin file risk |
| new_credit_providers_90d < 10 | -2 points | Limited credit history |
| savings_activity < 5 | -2 points | No savings buffer |

### Score Adjustments (Positive)
| Condition | Adjustment | Rationale |
|-----------|------------|-----------|
| monthly_debt_payments > 500 | +2 points | Demonstrates credit management |
| new_credit_providers_90d > 20 | +2 points | Established credit user |
| savings_activity > 50 | +3 points | Financial buffer |

---

## Why These Patterns Are Counterintuitive

Traditional credit models assume:
- More debt = more risk
- More credit providers = more risk
- Lower DTI = better

But in a **CRA-pre-approved population**, these assumptions invert because:

1. **Selection bias:** CRA already filtered out high-risk applicants
2. **Thin file problem:** Customers with no credit history are unknown quantities
3. **Credit management evidence:** Active credit users have demonstrated ability to manage

### Implication for US Market

Without CRA pre-filtering, you'll see a **wider population**. The traditional assumptions may hold better for clearly risky applicants, while these counterintuitive patterns may still apply to borderline cases.

**Recommendation:** Keep both sets of logic:
- Traditional rules for extreme cases (very high debt, etc.)
- These data-driven adjustments for moderate cases

---

## Limitations

1. **Training data bias:** Only CRA-approved loans (can't learn from CRA-declined)
2. **UK-specific:** Patterns may differ in US market
3. **Post-approval events:** Defaults from job loss, health issues, etc. aren't predictable
4. **Small default sample:** 140 defaults limits statistical power

---

## Next Steps

1. **Implement combined flag referral rule** (highest impact)
2. **Test on US pilot data** to validate signal transfer
3. **Consider A/B test** of counterintuitive weights
4. **Monitor and recalibrate** as US data accumulates
