# HCSTC Open Banking Scoring (README)

This repository contains a **scorecard-style** decision engine designed for **High Cost Short Term Credit (HCSTC)** lending using Open Banking-derived metrics.

The scoring logic is split across two files:

- **`scoring_config.py`** – configuration (weights, thresholds, rules, product parameters)
- **`scoring_engine.py`** – implementation (rule checks, scoring, decisioning, and loan offer calculation)

This README explains **how an application is scored end-to-end**, how the configuration drives outcomes, and where to adjust behaviour safely.

---

## 1. High-level flow

When an application is scored, the engine does the following:

1. **Loads metric objects** (income, expenses, debt, affordability, balance, risk) from the `metrics` dict.
2. **Applies rule checks first** (to generate **DECLINE reasons** and/or **REFER reasons**).
3. If any **DECLINE reasons** exist → decision is **DECLINE** immediately (score is set to `0.0`).
4. Otherwise it calculates a **0–100 score** using four score components:
   - Affordability (45 points)
   - Income quality (25 points)
   - Account conduct (20 points)
   - Risk indicators (10 points)
5. It assigns a decision based on score range (**APPROVE / REFER / DECLINE**).
6. If any **REFER reasons** exist (from rules), the decision is forced to **REFER** even if the score would approve.
7. If decision is **APPROVE**, the engine computes a **loan offer** (amount + term + repayment), subject to score-based and affordability-based limits.

---

## 2. Files and responsibilities

### 2.1 `scoring_config.py` (configuration)

Defines:

- **Score ranges** (approve/refer/decline cut-offs)
- **Weights** for each score component (total = 100)
- **Threshold tables** used by `_score_threshold()`
- **Rules** which can trigger **DECLINE** or **REFER**
- **Score-based limits** (max amount + max term by score band)
- **Product config** (interest rate, caps, min/max, buffers)

This is the safest place to tune approval rates without changing code structure.

### 2.2 `scoring_engine.py` (implementation)

Implements:

- Rule evaluation (`_check_rule_violations`)
- Score calculation (`_calculate_scores`)
- Decision mapping (`_determine_decision`)
- Risk flags (`_collect_risk_flags`)
- Loan offer construction (`_determine_loan_offer`)
- Monthly payment approximation (`_calculate_monthly_payment`)

---

## 3. Inputs: what metrics are required

`ScoringEngine.score_application(metrics, requested_amount, requested_term, application_ref)` expects `metrics` to be a dict containing objects compatible with the following types (imported from `feature_builder`):

- `IncomeMetrics`
- `ExpenseMetrics`
- `DebtMetrics`
- `AffordabilityMetrics`
- `BalanceMetrics`
- `RiskMetrics`

The engine reads specific fields from these objects. Key ones include:

### Income

- `effective_monthly_income`
- `income_stability_score` (0–100)
- `income_regularity_score` (0–100)
- `has_verifiable_income` (bool)

### Expenses / Debt

- `expenses.monthly_essential_total`
- `debt.monthly_debt_payments`
- `debt.active_hcstc_count`
- `debt.active_hcstc_count_90d`

### Affordability

- `monthly_disposable`
- `post_loan_disposable`
- `debt_to_income_ratio` (percentage, e.g., 45.0 for 45%)
- `max_affordable_amount` (upper bound derived from affordability logic)

### Balance

- `days_in_overdraft`
- `average_balance`

### Risk

- `gambling_percentage` (percentage of income)
- `failed_payments_count` (count across the analysed period)
- `failed_payments_count_45d` (count within the last 45 days)
- `debt_collection_distinct` (distinct DCAs in data)

> If a metric field is `None`, most scoring paths treat it as **0 points** (conservative default).

---

## 4. Rule checks (pre-scoring decision controls)

Rules are defined in `SCORING_CONFIG["rules"]` and evaluated by:

- `ScoringEngine._check_rule_violations(...)`

The function returns:

- `decline_reasons: List[str]`
- `refer_reasons: List[str]`

### Behaviour

- Any **DECLINE reasons** → immediate **DECLINE** (score forced to `0.0`).
- **REFER reasons** do not stop scoring, but later **force decision to REFER** regardless of score.

### Current rules (as configured)

The current rules include:

1. **Minimum monthly income** (soft rule → REFER)

   - Threshold: **£1500**
   - Action: **REFER**

2. **No verifiable income** (soft rule → REFER)

   - Triggers if `has_verifiable_income == False` AND income < **£300**
   - Action: **REFER**

3. **Active HCSTC lenders (last 90 days)** (hard rule → DECLINE)

   - Triggers if active HCSTC count in last 90 days > **6**
   - Action: **DECLINE**

4. **Gambling** (soft rule → REFER)

   - Triggers if gambling percentage > **15%**
   - Action: **REFER**

5. **Post-loan disposable** (soft rule → REFER)

   - Triggers if post-loan disposable < **£0**
   - Action: **REFER**

6. **Failed payments (last 45 days)** (effectively disabled)

   - Threshold: **999** (so it will not trigger in normal operation)
   - Action: **REFER**

7. **Debt collection agencies (DCA count)** (soft rule → REFER)

   - Triggers if distinct DCAs > **4** (i.e. 5+)
   - Action: **REFER**

8. **Projected DTI including the new loan** (soft rule → REFER)
   - Triggers if projected DTI > **85%**
   - Action: **REFER**

---

## 5. Score calculation (0–100)

Scoring is produced by `ScoringEngine._calculate_scores(...)` and returns a `ScoreBreakdown` containing:

- per-component score
- component sub-breakdowns
- penalties applied
- final total score (clamped to 0–100)

### 5.1 Component weights

Configured in `SCORING_CONFIG["weights"]`:

- Affordability: **45**
- Income quality: **25**
- Account conduct: **20**
- Risk indicators: **10**

### 5.2 Component 1: Affordability (max 45)

#### A) DTI ratio (max 18)

DTI is scored using threshold table `thresholds["dti_ratio"]` with **lower = better**:

| DTI <= | Points |
| -----: | -----: |
|    30% |     18 |
|    40% |     15 |
|    50% |     12 |
|    60% |      8 |
|    70% |      4 |
|   100% |      0 |

#### B) Disposable income (max 15)

Disposable income is scored with **higher = better**:

| Disposable >= | Points |
| ------------: | -----: |
|          £200 |     15 |
|          £150 |     13 |
|          £100 |     10 |
|           £50 |      6 |
|           £25 |      3 |
|            £0 |      0 |

#### C) Post-loan affordability (max 12)

This is a proportional score based on post-loan disposable:

- `post_loan_points = min(12, max(0, post_loan_disposable / 50 * 12))`

Meaning:

- £0 → 0 points
- £50 → 12 points
- £25 → 6 points
- Values above £50 are capped at 12

**Affordability total** = DTI points + Disposable points + Post-loan points (capped at 45).

### 5.3 Component 2: Income quality (max 25)

#### A) Income stability (max 12)

From `income.income_stability_score` using `thresholds["income_stability"]`:

| Stability >= | Points |
| -----------: | -----: |
|           90 |     12 |
|           75 |     10 |
|           60 |      7 |
|           40 |      4 |
|            0 |      0 |

#### B) Income regularity (max 8)

Proportional:

- `regularity_points = min(8, income_regularity_score / 100 * 8)`

#### C) Income verification (max 5)

- If `has_verifiable_income == True` → 5 points
- Else → 2.5 points

**Income quality total** = Stability + Regularity + Verification (capped at 25).

### 5.4 Component 3: Account conduct (max 20)

#### A) Failed payments (max 8)

Softened penalty:

- `failed_points = max(0, 8 - failed_payments_count * 1.5)`

So (approx):

- 0 fails → 8.0
- 1 fail → 6.5
- 2 fails → 5.0
- 3 fails → 3.5
- 4 fails → 2.0
- 5 fails → 0.5
- 6+ fails → 0.0

#### B) Overdraft usage (max 7)

Based on `balance.days_in_overdraft`:

- 0 days → 7
- 1–5 days → 5
- 6–15 days → decreases by 0.5 per day beyond day 5
- > 15 days → 0

#### C) Balance management (max 5)

Based on `balance.average_balance`:

- > = £500 → 5
- > = £200 → 3.5
- > = £0 → 1.75
- < £0 → 0

**Account conduct total** = Failed + Overdraft + Balance points (capped at 20).

### 5.5 Component 4: Risk indicators (max 10)

#### A) Gambling activity (max 5)

Uses `thresholds["gambling_percentage"]` with **lower = better**:

| Gambling <= | Points |
| ----------: | -----: |
|          0% |      5 |
|          2% |      3 |
|          5% |      0 |
|         10% |     -3 |
|        100% |     -5 |

#### B) HCSTC history (max 5)

Based on `debt.active_hcstc_count`:

- 0 → 5
- 1 → 3.5
- 2+ → 0 (and a penalty note is added)

#### Additional penalties

After base risk score is calculated, penalties may be applied:

- If gambling percentage > 5% → **-5** penalty
- If active HCSTC count >= 2 → **-10** penalty

The list of penalties applied is stored in `ScoreBreakdown.penalties_applied`.

### 5.6 Total score

Final total is clamped to 0–100:

`total_score = clamp(affordability + income_quality + conduct + risk_indicators, 0, 100)`

---

## 6. Decisioning

Decisioning is controlled by:

- `SCORING_CONFIG["score_ranges"]` in `scoring_config.py`
- `ScoringEngine._determine_decision(score)` in `scoring_engine.py`

### Score ranges (current)

- **APPROVE**: score >= **40**
- **REFER**: score 26–39
- **DECLINE**: score <= 25

### Override rule

If `refer_reasons` is non-empty, decision becomes **REFER** even if score would approve.

> Note: the engine currently appends a note _even on approve_:
> `"Score (x) suggests approval but manual review required"`.
> If you want pure auto-approve behaviour, that string logic would need adjusting.

---

## 7. Loan offer calculation (only if APPROVE)

If decision is APPROVE, the engine calculates an offer using:

1. **Score-based limits** (`SCORING_CONFIG["score_based_limits"]`)
2. **Affordability-based max** (`affordability.max_affordable_amount`)
3. **Product max loan amount** (`PRODUCT_CONFIG["max_loan_amount"]`)
4. The originally requested amount/term

### Score-based limits (current)

| Score >= | Max amount | Max term |
| -------: | ---------: | -------: |
|       75 |      £1500 |        6 |
|       65 |      £1200 |        6 |
|       55 |       £800 |        5 |
|       45 |       £500 |        4 |
|       35 |       £300 |        3 |
|        0 |         £0 |        0 |

The approved amount is:

`min(requested_amount, product_max, score_limit, affordability_max)`

If the amount is below `PRODUCT_CONFIG["min_loan_amount"]` (currently £200), it is set to 0.

### Monthly payment approximation

Monthly payment uses:

- daily interest rate (`daily_interest_rate`, default 0.008 i.e. 0.8%/day)
- days per month = 30.4
- total cost cap = 100% (interest cannot exceed principal)

The monthly payment is computed as:

1. `monthly_rate = daily_rate * 30.4`
2. `total_interest = min(amount * monthly_rate * term, amount * total_cost_cap)`
3. `monthly_payment = (amount + total_interest) / term`

> The APR shown is a simplified indicative APR, not a statutory APR calculation.

---

## 8. Outputs

`score_application(...)` returns a `ScoringResult` containing:

- `decision`: APPROVE / REFER / DECLINE
- `score`: 0–100
- `risk_level`: Low / High / Very High (mapped from decision)
- `loan_offer` (if approved)
- `score_breakdown` (component scores and notes)
- summaries: monthly income/expenses/disposable/post-loan disposable
- `risk_flags`: human-readable flags (e.g., “High DTI: 48.2%”)
- `decline_reasons` (if declined)
- `processing_notes` (refer reasons / manual review notes)

---

## 9. Known implementation note (config key)

In `scoring_engine.py.__init__`, the engine assigns:

```python
self.hard_decline_rules = self.scoring_config["hard_decline_rules"]
```

However, the current `scoring_config.py` defines rules under:

- `SCORING_CONFIG["rules"]`

If your runtime configuration does not include a `hard_decline_rules` key, engine initialisation will raise a `KeyError`.

**Suggested resolution options (choose one):**

- Add a `hard_decline_rules` alias key in `scoring_config.py`, or
- Update the engine to reference `"rules"` only

This README documents the current behaviour; fix approach depends on how the wider repo is structured.

---

## 10. Tuning guide (what to change for approval rate vs risk)

Most common tuning levers (in order of impact):

1. **Score ranges** (`score_ranges.approve.min`)
2. **DTI thresholds** (`thresholds.dti_ratio`)
3. **Disposable thresholds** (`thresholds.disposable_income`)
4. **Rule actions** (DECLINE → REFER, or refer thresholds)
5. **Score-based limits** (amount/term bands)
6. **Penalty slopes** (e.g., failed payments multiplier)

A good practice is to run historical test batches and track:

- approve / refer / decline rate
- average post-loan disposable
- distribution of DTI and missed payments among approvals
- segment-level outcomes (e.g., by income stability bucket)

---

## 11. Quick example (conceptual)

An applicant with:

- DTI 45% → 12 points (DTI)
- Disposable £75 → 6 points
- Post-loan disposable £25 → 6 points
  Affordability = 24 / 45

Income quality:

- stability 75 → 10
- regularity 80 → 6.4
- verifiable income → 5
  Income quality = 21.4 / 25

Account conduct:

- failed payments_count = 2 → 5 points
- overdraft days = 3 → 5 points
- avg balance = £150 → 1.75 points
  Conduct = 11.75 / 20

Risk:

- gambling 1% → 3 points
- active HCSTC count = 1 → 3.5 points
  Risk = 6.5 / 10

Total ≈ 24 + 21.4 + 11.75 + 6.5 = 63.65 → APPROVE (score>=40),
then offer constrained by score band and affordability max.

---
