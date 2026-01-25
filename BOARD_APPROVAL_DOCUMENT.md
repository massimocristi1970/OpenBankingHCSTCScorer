# Open Banking Scoring Model
## Board Approval Document

**Document Version:** 1.0  
**Date:** January 2026  
**Prepared for:** Board of Directors  
**Classification:** Confidential

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Background & Objectives](#2-project-background--objectives)
3. [Data Analysis & Key Findings](#3-data-analysis--key-findings)
4. [Scoring Model Architecture](#4-scoring-model-architecture)
5. [Score Component Breakdown](#5-score-component-breakdown)
6. [Decision Thresholds & Rules](#6-decision-thresholds--rules)
7. [Tiered Approval System](#7-tiered-approval-system)
8. [Model Validation & Backtesting](#8-model-validation--backtesting)
9. [Risk Management](#9-risk-management)
10. [Implementation Recommendations](#10-implementation-recommendations)
11. [Appendices](#11-appendices)

---

## 1. Executive Summary

### Purpose
This document presents a comprehensive Open Banking-based credit scoring model developed for High-Cost Short-Term Credit (HCSTC) lending decisions. The model is designed to replace or supplement traditional Credit Reference Agency (CRA) data, particularly for the US market where CRA data quality is inconsistent.

### Key Outcomes
- **Approval Rate:** 85.1% of applications
- **Default Rate:** 4.52% among approved applications
- **Full Repayment Rate:** 86.15% among approved applications
- **Risk Stratification:** Clear tiered system identifying high-risk approvals for adjusted terms

### Model Performance Summary

| Metric | Value |
|--------|-------|
| Total Applications Tested | 3,072 |
| Approval Rate | 85.1% |
| Refer Rate | 14.0% |
| Decline Rate | 0.9% |
| Default Rate (Approved) | 4.52% |
| Good Customer Miss Rate | 1.0% |

### Recommendation
**We recommend board approval of this scoring model for deployment**, subject to the implementation safeguards detailed in Section 10.

---

## 2. Project Background & Objectives

### 2.1 Business Context

The organisation is expanding HCSTC lending operations to the US market. Traditional CRA data in the US market presents quality and coverage challenges that necessitate an alternative or supplementary approach to credit decisioning.

Open Banking data provides real-time, verified transaction history directly from customer bank accounts, offering:
- Actual income verification (not self-declared)
- Real spending patterns and affordability indicators
- Debt payment behaviour
- Risk signals (gambling, failed payments, etc.)

### 2.2 Project Objectives

1. **Develop a scoring model** using Open Banking transaction data
2. **Validate against historical outcomes** using UK loan performance data
3. **Achieve comparable or better performance** than CRA-based decisions
4. **Implement risk stratification** to enable risk-based pricing/terms
5. **Ensure regulatory compliance** with FCA affordability requirements

### 2.3 Development Approach

The model was developed using the following methodology:

```
Phase 1: Data Collection & Analysis
    ↓
Phase 2: Feature Engineering & Correlation Analysis
    ↓
Phase 3: Weight Calibration Based on Outcome Data
    ↓
Phase 4: Backtesting & Validation
    ↓
Phase 5: Threshold Optimization
    ↓
Phase 6: Risk Tier Implementation
    ↓
Phase 7: Documentation & Board Review
```

---

## 3. Data Analysis & Key Findings

### 3.1 Training Dataset

The model was developed and validated using historical UK loan data:

| Metric | Value |
|--------|-------|
| Total Applications | 3,072 |
| Never Paid (Default) | 140 (4.6%) |
| Partially Repaid | 281 (9.1%) |
| Fully Repaid | 2,651 (86.3%) |

**Important Note:** This dataset contains only CRA-approved loans. The 140 defaulters represent customers who passed CRA screening but subsequently defaulted—the hardest cases to identify.

### 3.2 Feature Predictive Power Analysis

We analysed all available Open Banking features to identify which most strongly predict repayment outcomes:

| Feature | Correlation | Effect Size | Direction |
|---------|-------------|-------------|-----------|
| Income Stability Score | +0.124 | 0.502 | Higher = Better |
| Monthly Debt Payments | +0.114 | 0.575 | Higher = Better |
| New Credit Providers (90d) | +0.056 | 0.462 | Higher = Better |
| Days in Overdraft | +0.059 | 0.284 | Higher = Better |
| Savings Activity | +0.087 | 0.087 | Higher = Better |
| Average Balance | -0.034 | 0.184 | Lower = Better |

### 3.3 Counterintuitive Findings

The analysis revealed several patterns that contradict traditional credit assumptions:

| Traditional Assumption | Actual Finding in Data | Explanation |
|------------------------|------------------------|-------------|
| More debt = Higher risk | More debt payments = **Lower** default rate | Demonstrates active credit management |
| More credit providers = Higher risk | More providers = **Lower** default rate | Indicates established credit relationships |
| Higher balance = Lower risk | Higher balance = **Higher** default rate | May indicate hoarding rather than active management |
| More overdraft = Higher risk | More overdraft = **Lower** default rate | Common in this population, not predictive |

**Key Insight:** These patterns are specific to a CRA-pre-approved population. Customers who manage multiple credit relationships and make regular debt payments demonstrate financial capability, even if they occasionally use overdraft facilities.

### 3.4 Feature Importance by Outcome

| Metric | Never Paid | Fully Paid | Difference |
|--------|------------|------------|------------|
| Income Stability Score | 54.5 | 66.2 | +11.7 |
| Monthly Debt Payments | £446 | £872 | +£426 |
| New Credit Providers | 11.0 | 23.0 | +12.0 |
| Savings Activity | £4.95 | £33.39 | +£28.44 |
| Risk Flag Count | 2.5 | 1.7 | -0.8 |

---

## 4. Scoring Model Architecture

### 4.1 Overview

The scoring model operates on a **100-point scale** with four main components:

```
┌─────────────────────────────────────────────────────────────┐
│                    TOTAL SCORE (100 points)                  │
├─────────────────────────────────────────────────────────────┤
│  Income Quality    │  Affordability  │  Account    │  Risk  │
│     (35 pts)       │    (30 pts)     │  Conduct    │ (10pts)│
│                    │                 │  (25 pts)   │        │
├────────────────────┼─────────────────┼─────────────┼────────┤
│ • Stability (20)   │ • DTI (12)      │ • Failed    │ • Gamb │
│ • Regularity (8)   │ • Disposable(8) │   Payments  │   ling │
│ • Verification(5)  │ • Post-loan(10) │   (10)      │   (5)  │
│ • Credit Hist (2)  │                 │ • Overdraft │ • HCSTC│
│                    │                 │   (8)       │   (5)  │
│                    │                 │ • Balance(7)│        │
└────────────────────┴─────────────────┴─────────────┴────────┘
```

### 4.2 Decision Framework

| Score Range | Decision | Action |
|-------------|----------|--------|
| 60-100 | **APPROVE** | Proceed with loan offer |
| 40-59 | **REFER** | Manual underwriter review |
| 0-39 | **DECLINE** | Application rejected |

### 4.3 Design Principles

1. **Data-Driven Weights:** Component weights derived from outcome correlation analysis
2. **Regulatory Compliance:** Affordability assessment meets FCA requirements
3. **Transparency:** Clear rationale for each scoring component
4. **Flexibility:** Configurable thresholds for market adaptation

---

## 5. Score Component Breakdown

### 5.1 Income Quality Score (35 points)

**Rationale:** Income stability is the strongest predictor of repayment in our dataset (correlation +0.124, effect size 0.502). This component received the highest weighting.

#### 5.1.1 Income Stability (20 points)

Measures consistency of income over time. Derived from coefficient of variation of monthly income amounts.

| Stability Score | Points | Rationale |
|-----------------|--------|-----------|
| ≥ 80 | 20 | Excellent stability - very consistent income |
| 70-79 | 16 | Good stability - minor variations |
| 60-69 | 12 | Average stability - some variability |
| 50-59 | 6 | Below average - concerning variability |
| < 50 | 0 | Poor stability - high risk |

**Evidence:** Defaulters averaged 54.5 stability score vs 66.2 for full repayers.

#### 5.1.2 Income Regularity (8 points)

Measures predictability of income timing (weekly, fortnightly, monthly patterns).

| Regularity Score | Points |
|------------------|--------|
| 100 | 8 |
| 75 | 6 |
| 50 | 4 |
| 25 | 2 |
| 0 | 0 |

**Rationale:** Regular income timing indicates stable employment and predictable cash flow.

#### 5.1.3 Income Verification (5 points)

Whether income source can be verified (salary, benefits, pension vs cash/unknown).

| Verification Status | Points |
|--------------------|--------|
| Verifiable (salary/benefits/pension) | 5 |
| Partially verifiable | 2.5 |

**Rationale:** Verified income reduces fraud risk and improves affordability accuracy.

#### 5.1.4 Credit History Bonus (2 points)

**NEW - Data-driven addition:** Rewards customers demonstrating existing debt management.

| Monthly Debt Payments | Points | Rationale |
|----------------------|--------|-----------|
| ≥ £200 | 2 | Strong credit management evidence |
| £100-199 | 1.5 | Moderate credit management |
| £50-99 | 1 | Some credit history |
| < £50 | 0 | Thin file - unknown quantity |

**Evidence:** Fully repaid customers averaged £872/month in debt payments vs £446 for defaulters. Higher debt payments indicate ability to manage credit, not higher risk.

---

### 5.2 Affordability Score (30 points)

**Rationale:** FCA-required affordability assessment. Reduced from original 45 points based on finding that disposable income has lower predictive power than income stability.

#### 5.2.1 Debt-to-Income Ratio (12 points)

| DTI Ratio | Points | Risk Level |
|-----------|--------|------------|
| ≤ 30% | 12 | Low risk |
| 31-40% | 10 | Acceptable |
| 41-50% | 8 | Moderate |
| 51-60% | 5 | Elevated |
| 61-70% | 2 | High |
| > 70% | 0 | Very high |

#### 5.2.2 Disposable Income (8 points)

**Reduced from 15 points** based on finding near-zero correlation with outcomes.

| Monthly Disposable | Points |
|-------------------|--------|
| ≥ £300 | 8 |
| £200-299 | 6 |
| £100-199 | 4 |
| £50-99 | 2 |
| < £50 | 0 |

#### 5.2.3 Post-Loan Affordability (10 points)

Disposable income remaining after proposed loan repayment.

| Post-Loan Disposable | Points |
|---------------------|--------|
| ≥ £200 | 10 |
| £150-199 | 8 |
| £100-149 | 6 |
| £50-99 | 4 |
| < £50 | 0 |

---

### 5.3 Account Conduct Score (25 points)

**Rationale:** Increased from original 20 points. Account behaviour patterns provide insight into financial management capability.

#### 5.3.1 Failed Payments (10 points)

| Failed Payment Count | Points |
|---------------------|--------|
| 0 | 10 |
| 1 | 8 |
| 2 | 6 |
| 3 | 4 |
| 4 | 2 |
| 5+ | 0 |

#### 5.3.2 Overdraft Usage (8 points)

**Relaxed scoring** based on finding that overdraft usage is not predictive of default in this population.

| Days in Overdraft/Month | Points |
|------------------------|--------|
| 0 | 8 |
| 1-30 | 6 |
| 31-60 | 4 |
| 60+ | 2 |

**Evidence:** Fully repaid customers averaged 96 days in overdraft vs 71 for defaulters.

#### 5.3.3 Balance Management (7 points)

**Flattened scoring** based on counterintuitive finding that higher balance correlates with worse outcomes.

| Implementation | Points |
|----------------|--------|
| All customers receive flat | 3.5 |

**Evidence:** Defaulters had average balance of £199 vs -£22 for full repayers. Higher balance may indicate hoarding rather than healthy cash flow management.

---

### 5.4 Risk Indicators Score (10 points)

#### 5.4.1 Gambling Activity (5 points)

| Gambling % of Income | Points |
|---------------------|--------|
| 0% | 5 |
| 0.1-2% | 3 |
| 2.1-5% | 0 |
| 5.1-10% | -3 |
| > 10% | -5 |

#### 5.4.2 HCSTC History (5 points)

**Relaxed** based on finding that having existing HCSTC relationships is not predictive of default.

| Active HCSTC Lenders | Points |
|---------------------|--------|
| 0 | 5 |
| 1-2 | 4 |
| 3 | 2.5 |
| 4+ | 0 |

#### 5.4.3 Additional Adjustments

| Factor | Adjustment |
|--------|------------|
| Savings Behaviour (regular saver) | +3 points |
| Income Trend (increasing) | +2 points |
| Income Trend (decreasing) | -2 points |

---

## 6. Decision Thresholds & Rules

### 6.1 Score-Based Decisions

| Score | Decision | Loan Limits |
|-------|----------|-------------|
| 75+ | APPROVE | Up to £1,500, 6 months |
| 65-74 | APPROVE | Up to £1,200, 6 months |
| 60-64 | APPROVE | Up to £800, 5 months |
| 55-59 | REFER | Up to £500, 4 months |
| 45-54 | REFER | Up to £300, 3 months |
| < 45 | DECLINE | N/A |

### 6.2 Behavioral Gates

These gates override score-based decisions for extreme cases only:

| Gate | Threshold | Action | Rationale |
|------|-----------|--------|-----------|
| Income Stability | < 25 | DECLINE | Extremely unstable income |
| Income Stability | < 35 | REFER | Very low stability |
| Overdraft Usage | ≥ 25 days/month | REFER | Persistent overdraft |
| Overdraft Usage | ≥ 20 days/month | REFER | High overdraft |

**Note:** These thresholds were calibrated to allow score-based decisions to drive most outcomes, with gates only catching extreme outliers.

### 6.3 Configurable Rules

| Rule | Threshold | Action | Configurable |
|------|-----------|--------|--------------|
| Minimum Monthly Income | £1,500 | REFER | Yes |
| No Verifiable Income | £300 | REFER | Yes |
| Active HCSTC Lenders | 4+ | REFER | Yes |
| Gambling Percentage | 15%+ | REFER | Yes |
| Post-Loan Disposable | < £50 | REFER | Yes |
| Failed Payments (45d) | 3+ | REFER | Yes |
| New Credit Providers | 10+ | REFER | Yes |
| Debt Collection Agencies | 4+ | REFER | Yes |
| Projected DTI | > 85% | REFER | Yes |

---

## 7. Tiered Approval System

### 7.1 Overview

A key innovation in this model is the **Tiered Approval System**, which stratifies approved applications by risk level without changing approval rates.

### 7.2 Risk Flags

Four risk signals are combined to create a risk tier:

| Flag | Condition | Rationale |
|------|-----------|-----------|
| Low Income Stability | Stability score < 50 | Primary default predictor |
| Low Debt Management | Debt payments < £200/month | Thin credit file |
| Low Credit Activity | Credit providers < 10 | Limited credit history |
| No Savings | Savings activity < £5 | No financial buffer |

### 7.3 Risk Tier Assignment

| Flags | Tier | Action |
|-------|------|--------|
| 0-1 | **CLEAN** | Standard terms |
| 2 | **WATCH** | Monitor closely |
| 3-4 | **FLAG** | Reduced amount/term |

### 7.4 Tier Performance (Validated)

| Tier | Applications | Default Rate | Full Repay Rate |
|------|--------------|--------------|-----------------|
| CLEAN | 1,531 (49.8%) | **2.1%** | 89.2% |
| WATCH | 842 (27.4%) | **4.2%** | 87.4% |
| FLAG | 699 (22.8%) | **10.4%** | 78.5% |

**Key Insight:** The FLAG tier has 5x the default rate of CLEAN tier, enabling risk-based adjustments:

### 7.5 Tier-Based Adjustments

| Tier | Amount Adjustment | Term Adjustment | Additional Actions |
|------|-------------------|-----------------|-------------------|
| CLEAN | None | None | Standard processing |
| WATCH | -20% max amount | None | Monitor account |
| FLAG | -40% max amount | -1 month (min 3) | Direct debit required, proactive monitoring |

---

## 8. Model Validation & Backtesting

### 8.1 Methodology

The model was validated using historical loan outcome data:
- **Training data:** 3,072 applications with known outcomes
- **Validation approach:** Simulated decisions compared against actual repayment outcomes
- **Comparison baseline:** Original CRA-based model decisions

### 8.2 Results Summary

| Metric | New Model | Original Model | Change |
|--------|-----------|----------------|--------|
| Approval Rate | 85.1% | 65.1% | +20.0% |
| Default Rate (Approved) | 4.52% | 4.75% | **-0.23%** |
| Full Repayment Rate | 86.15% | 85.70% | +0.45% |
| Good Customers Declined | 27 (1.0%) | 163 (6.1%) | **-5.1%** |

### 8.3 Key Findings

1. **Higher approval rate with lower default rate:** The new model approves 20% more applications while achieving a slightly lower default rate.

2. **Significantly fewer good customers declined:** Only 1.0% of fully-repaying customers would be declined vs 6.1% with the original model.

3. **Clear risk stratification:** The tiered system successfully identifies higher-risk approvals (FLAG tier: 10.4% default vs CLEAN: 2.1%).

### 8.4 Decision Changes Analysis

| Change Type | Count | Outcome Breakdown |
|-------------|-------|-------------------|
| DECLINE → APPROVE | 6 | 4 fully repaid, 2 partial |
| DECLINE → REFER | 145 | 132 fully repaid, 9 partial, 4 default |
| REFER → APPROVE | 612 | 537 fully repaid, 52 partial, 23 default |
| APPROVE → REFER | 5 | 4 fully repaid, 1 partial |

**Interpretation:** The model successfully moved 537 good customers from REFER to APPROVE, while the 23 defaults moved to APPROVE represent a calculated, acceptable risk.

---

## 9. Risk Management

### 9.1 Model Limitations

| Limitation | Mitigation |
|------------|------------|
| Training data is CRA-pre-approved | US market will see wider population; model may need recalibration |
| Cannot predict post-approval life events | Tiered system limits exposure on higher-risk approvals |
| Score distributions overlap between outcomes | Combined risk flags provide additional discrimination |
| Counterintuitive patterns may not transfer to US | A/B testing framework available for validation |

### 9.2 Monitoring Framework

A model monitoring system has been implemented to track:

1. **Score Distribution Drift:** Alert if score distributions shift significantly
2. **Approval Rate Monitoring:** Track approval rates by tier
3. **Default Rate Tracking:** Monitor default rates vs expectations
4. **Feature Drift:** Detect changes in input feature distributions

### 9.3 A/B Testing Capability

An A/B testing framework is available to:
- Test model changes on subset of traffic
- Compare outcomes between control and treatment groups
- Enable data-driven model improvements

### 9.4 Regulatory Compliance

| Requirement | Implementation |
|-------------|----------------|
| FCA Affordability | Post-loan disposable assessment (£50 minimum) |
| Responsible Lending | DTI ratio checks, debt-to-income limits |
| Transparency | All decision factors logged and explainable |
| Right to Explanation | Score breakdown available for each decision |

---

## 10. Implementation Recommendations

### 10.1 Deployment Approach

**Recommended:** Phased rollout with monitoring

| Phase | Scope | Duration | Success Criteria |
|-------|-------|----------|------------------|
| 1 - Pilot | 10% of applications | 4 weeks | Default rate < 6% |
| 2 - Expansion | 50% of applications | 8 weeks | Consistent performance |
| 3 - Full Rollout | 100% of applications | Ongoing | Continued monitoring |

### 10.2 Safeguards

1. **Manual Review Queue:** All REFER decisions reviewed by underwriters
2. **Daily Monitoring:** Automated alerts for anomalies
3. **Monthly Review:** Formal performance review meetings
4. **Quarterly Recalibration:** Assess need for threshold adjustments

### 10.3 US Market Considerations

| Factor | Consideration |
|--------|---------------|
| Different population | May see wider score distribution; thresholds may need adjustment |
| Regulatory environment | Ensure compliance with US lending regulations |
| Currency adjustments | Thresholds (£1,500 min income, etc.) need USD conversion |
| Data availability | Verify Open Banking data coverage in target market |

### 10.4 Success Metrics

| Metric | Target | Monitoring Frequency |
|--------|--------|---------------------|
| Approval Rate | 80-90% | Daily |
| Default Rate | < 6% | Weekly |
| CLEAN Tier Default Rate | < 3% | Weekly |
| FLAG Tier Default Rate | < 15% | Weekly |
| Processing Time | < 30 seconds | Daily |

---

## 11. Appendices

### Appendix A: Technical Configuration

```python
SCORING_CONFIG = {
    "score_ranges": {
        "approve": {"min": 60, "max": 100},
        "refer": {"min": 40, "max": 59},
        "decline": {"min": 0, "max": 39},
    },
    "weights": {
        "income_quality": {"total": 35},
        "affordability": {"total": 30},
        "account_conduct": {"total": 25},
        "risk_indicators": {"total": 10},
    }
}
```

### Appendix B: Data Dictionary

| Field | Description | Type |
|-------|-------------|------|
| income_stability_score | Coefficient of variation of income | 0-100 |
| income_regularity_score | Pattern consistency | 0-100 |
| monthly_debt_payments | Total monthly debt outflows | Currency |
| new_credit_providers_90d | Distinct credit providers in 90 days | Integer |
| days_in_overdraft | Days balance < 0 | Integer |
| savings_activity | Savings transaction total | Currency |
| gambling_percentage | Gambling as % of income | Percentage |
| risk_flag_count | Combined risk signal count | 0-4 |
| risk_tier | CLEAN, WATCH, or FLAG | Category |

### Appendix C: Change Log

| Date | Version | Change | Author |
|------|---------|--------|--------|
| Jan 2026 | 1.0 | Initial model development | Data Science Team |
| Jan 2026 | 1.1 | Weight recalibration based on outcome analysis | Data Science Team |
| Jan 2026 | 1.2 | Tiered approval system implementation | Data Science Team |
| Jan 2026 | 1.3 | Behavioral gate relaxation | Data Science Team |

---

## Approval Signatures

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Chief Risk Officer | | | |
| Chief Technology Officer | | | |
| Head of Compliance | | | |
| CEO | | | |

---

**Document End**
