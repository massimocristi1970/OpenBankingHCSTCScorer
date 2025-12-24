# OpenBankingHCSTCScorer

Open Banking HCSTC (High-Cost Short-Term Credit) Loan Scoring System - A Streamlit-based batch processing application for scoring consumer loan applications using Open Banking (PLAID format) transaction data.

## Application Purpose

The OpenBankingHCSTCScorer is a sophisticated credit decisioning engine designed specifically for UK High-Cost Short-Term Credit (HCSTC) lenders operating under FCA regulation. It automates the assessment of loan applications by analyzing Open Banking transaction data to evaluate:

- **Affordability**: Can the applicant afford the loan repayments?
- **Income Quality**: Is the income stable, regular, and verifiable?
- **Account Conduct**: Does the applicant manage their finances responsibly?
- **Risk Indicators**: Are there red flags that indicate elevated risk?

The system processes transaction data in PLAID format, categorizes transactions intelligently, calculates financial metrics, and produces a comprehensive credit score that drives automated lending decisions.

## Overview

This application provides batch processing capabilities for HCSTC lenders, enabling:

- Automated analysis of bank transaction data (90 days minimum recommended)
- Intelligent categorization of income, expenses, and debt obligations
- Comprehensive risk assessment including gambling, debt collection, and payment failures
- Score-based loan amount and term recommendations
- Hard decline rules for immediate rejection of unsuitable applications
- Detailed scoring breakdowns for transparency and compliance

### Product Parameters

- **Loan Range**: £200 - £1,500
- **Term Range**: 3, 4, 5, or 6 months
- **Interest**: Fixed Rate (FCA Price Cap Compliant - 0.8% per day, total cost cap 100%)
- **Repayment**: Equal monthly instalments

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/OpenBankingHCSTCScorer.git
cd OpenBankingHCSTCScorer
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the application:

```bash
streamlit run app.py
```

### Windows Users

Double-click `run_hcstc_scorer.bat` to start the application.

## Usage Instructions

### How to Run the Scoring Engine

1. **Start the Application**:

   ```bash
   streamlit run app.py
   ```

   Or on Windows: Double-click `run_hcstc_scorer.bat`

2. **Access the Web Interface**: Browser opens automatically to `http://localhost:8501`

3. **Upload Transaction Data**:

   - Upload individual JSON files in PLAID format
   - Upload ZIP archives containing multiple JSON files for batch processing
   - Supports cumulative mode to process files across multiple uploads

4. **Configure Processing Options**:

   - Set requested loan amount (£200-£1,500)
   - Set requested loan term (3-6 months)
   - Enable/disable cumulative processing mode

5. **Review Results**:
   - View summary statistics (approval, refer, decline counts)
   - Review individual scoring breakdowns
   - Download results as Excel file
   - Analyze score distributions with interactive charts

### Batch Processing

The system supports batch processing of multiple applications:

- Upload a ZIP file containing multiple JSON files (one per applicant)
- Each file is processed independently
- Results are aggregated and displayed in a summary table
- Export all results to Excel for further analysis

### Uploading Files

The application accepts:

- **Individual JSON files** in PLAID format (one applicant)
- **ZIP archives** containing multiple JSON files (batch processing)

### JSON Data Format

Files must follow the PLAID Open Banking format:

```json
{
  "accounts": [
    {
      "account_id": "xxx",
      "name": "Current Account",
      "type": "depository",
      "subtype": "checking",
      "balances": {
        "available": 1234.56,
        "current": 1234.56,
        "iso_currency_code": "GBP"
      }
    }
  ],
  "transactions": [
    {
      "account_id": "xxx",
      "transaction_id": "xxx",
      "amount": 123.45,
      "date": "2024-01-15",
      "name": "TRANSACTION DESCRIPTION",
      "merchant_name": "Merchant Name",
      "personal_finance_category.detailed": "category_name"
    }
  ]
}
```

**Amount Convention**:

- Negative amounts = Credits (money in)
- Positive amounts = Debits (money out)

## Scoring System Overview

The scoring system operates on a **0-175 point scale** (rescaled from the original 0-100 to maintain stricter standards). The passing threshold is set at 70 points, ensuring only creditworthy applicants are approved automatically.

### Decision Thresholds

| Score Range | Decision    | Description                                                       |
| ----------- | ----------- | ----------------------------------------------------------------- |
| **≥70**     | **APPROVE** | Automatically approved for loan offer based on score-based limits |
| **45-69**   | **REFER**   | Manual review required - borderline case                          |
| **<45**     | **DECLINE** | Automatically declined - does not meet minimum standards          |

### Scoring Components (175 points total)

The scoring system evaluates four key areas, with each contributing to the total score:

#### 1. Affordability Score (78.75 points)

Measures the applicant's ability to afford loan repayments:

- **Debt-to-Income Ratio** (31.5 points): Lower DTI = higher score
  - ≤15%: 31.5 points
  - 15-25%: 26.25 points
  - 25-35%: 21 points
  - 35-45%: 14 points
  - 45-55%: 7 points
  - > 55%: 0 points
- **Disposable Income** (26.25 points): Monthly income minus essential expenses and debt
  - ≥£400: 26.25 points
  - £300-399: 22.75 points
  - £200-299: 17.5 points
  - £100-199: 10.5 points
  - £50-99: 5.25 points
  - <£50: 0 points
- **Post-Loan Affordability** (21 points): Disposable income remaining after loan repayment
  - Calculated as: min(21, disposable_after_loan / 50 \* 21)

#### 2. Income Quality Score (43.75 points)

Assesses the stability and reliability of income:

- **Income Stability** (21 points): Percentage of income from stable sources (salary, benefits, pension)
  - ≥90%: 21 points
  - 75-89%: 17.5 points
  - 60-74%: 12.25 points
  - 40-59%: 7 points
  - <40%: 0 points
- **Income Regularity** (14 points): Consistency of income payments
  - Calculated as: regularity_score / 100 \* 14
- **Income Verification** (8.75 points): Presence of identifiable income sources
  - Verifiable income: 8.75 points
  - Unverifiable: 3.5 points

#### 3. Account Conduct Score (35 points)

Evaluates how responsibly the applicant manages their finances:

- **Failed Payments** (14 points): Deducted 3.5 points per failed payment
  - 0 failed payments: 14 points
  - 1 failed payment: 10.5 points
  - 2 failed payments: 7 points
  - 3+ failed payments: 0-3.5 points
- **Overdraft Usage** (12.25 points): Days spent in overdraft
  - 0 days: 12.25 points
  - 1-5 days: 8.75 points
  - 6-15 days: 5.25 points
  - > 15 days: 0 points
- **Balance Management** (8.75 points): Average account balance
  - ≥£500: 8.75 points
  - £200-499: 5.25 points
  - £0-199: 1.75 points
  - Negative: 0 points

#### 4. Risk Indicators Score (17.5 points)

Identifies negative risk factors:

- **Gambling Activity** (8.75 points): Percentage of income spent on gambling
  - 0%: 8.75 points
  - <2%: 5.25 points
  - 2-5%: 0 points
  - 5-10%: -5.25 points (penalty)
  - > 10%: -8.75 points (penalty)
- **HCSTC History** (8.75 points): Active HCSTC lenders
  - 0 lenders: 8.75 points
  - 1 lender: 3.5 points
  - 2+ lenders: 0 points + -17.5 penalty

### Hard Decline Rules (Automatic Rejection)

Applications are **immediately declined** without scoring if any of the following criteria are met:

1. **Insufficient Income**: Monthly income < £1,000
2. **No Verifiable Income**: No identifiable income source and income < £300
3. **Excessive HCSTC Exposure**: Active borrowing from 7+ HCSTC lenders in last 90 days (max: 6)
4. **Problem Gambling**: Gambling expenditure > 15% of monthly income
5. **Negative Post-Loan Affordability**: Post-loan disposable income < £0
6. **Excessive Payment Failures**: 6+ failed payments in last 45 days (max: 5)
7. **Multiple Debt Collection Agencies**: Active debt collection from 4+ agencies (max: 3)
8. **Unsustainable DTI**: Projected DTI with new loan would exceed 75%

These rules are designed to prevent lending to applicants who clearly cannot afford additional credit or have severe financial management issues.

### Score-Based Loan Limits

Once an application passes the hard decline checks and achieves a score ≥70, the approved loan amount and term are determined by the score:

| Minimum Score | Maximum Amount | Maximum Term | Risk Profile      |
| ------------- | -------------- | ------------ | ----------------- |
| **149+**      | £1,500         | 6 months     | Excellent         |
| **123-148**   | £1,200         | 6 months     | Very Good         |
| **105-122**   | £800           | 5 months     | Good              |
| **88-104**    | £500           | 4 months     | Fair              |
| **70-87**     | £300           | 3 months     | Acceptable        |
| **<70**       | £0             | 0 months     | Declined/Referred |

The final approved amount is the **minimum** of:

- Requested amount
- Score-based limit
- Affordability-based maximum (ensures repayment < 70% of disposable income)
- Product maximum (£1,500)

### Current System Performance

Based on recent application data, the scoring system produces the following distribution:

| Decision    | Count | Percentage | Notes                                                   |
| ----------- | ----- | ---------- | ------------------------------------------------------- |
| **APPROVE** | 17    | 5.5%       | Automatically approved with loan offers                 |
| **REFER**   | 252   | 81.8%      | Require manual underwriting review                      |
| **DECLINE** | 39    | 12.7%      | Automatically declined (failed hard rules or score <45) |
| **Total**   | 308   | 100%       |                                                         |

**Key Insights:**

- The high referral rate (81.8%) reflects the conservative scoring approach and the challenging financial profiles typical of HCSTC applicants
- Only 5.5% of applications achieve the ≥70 score threshold for automatic approval
- 12.7% are immediately declined due to hard decline rules or very low scores (<45)
- The 70-point threshold ensures only the most creditworthy applicants are approved automatically, reducing risk

## Transaction Categories

The system intelligently categorizes transactions to calculate accurate financial metrics. Categories are identified using keyword patterns, regex matching, and Plaid personal_finance_category fields.

### Expense Categories

Expenses include essential living costs and **account transfers out**:

| Category                 | Weight | Examples                              | Description                                  |
| ------------------------ | ------ | ------------------------------------- | -------------------------------------------- |
| **Account Transfer Out** | 100%   | TRANSFER_OUT_ACCOUNT_TRANSFER (PLAID) | Bank account transfers (counted as expenses) |
| **Discretionary**        | 100%   | Shopping, entertainment, dining       | Non-essential spending                       |
| **Food & Dining**        | 100%   | Restaurants, takeaways                | Food outside groceries                       |
| **Unpaid/Failed**        | 100%   | Bounced payments, failed DDs          | Payment failures                             |
| **Gambling**             | 100%   | Betting, casinos, online gambling     | High-risk spending                           |
| **Other**                | 100%   | Miscellaneous expenses                | Uncategorized outgoings                      |

### Income Categories

Income is categorized and weighted based on stability and verifiability:

| Category                  | Weight | Examples                                        | Description                                    |
| ------------------------- | ------ | ----------------------------------------------- | ---------------------------------------------- |
| **Salary & Wages**        | 100%   | BACS, Payroll, FP-, BGC, NET PAY                | Regular employment income - highest stability  |
| **Benefits & Government** | 100%   | Universal Credit, DWP, HMRC, Child Benefit, PIP | State benefits - reliable and regular          |
| **Pension**               | 100%   | State Pension, NEST, Aviva, Standard Life       | Pension income - highly stable                 |
| **Gig Economy**           | 70%    | Uber, Deliveroo, Just Eat, Fiverr, Upwork       | Variable income - discounted for instability   |
| **Account Transfer In**   | 100%   | TRANSFER_IN_ACCOUNT_TRANSFER (PLAID)            | Bank account transfers (now counted as income) |
| **Other Verified**        | 100%   | Any other identifiable credit (non-transfer)    | Miscellaneous income sources                   |

**Transfer Handling**:

- **Account transfers** (`TRANSFER_IN_ACCOUNT_TRANSFER`) are **included** as income at 100% weight
- **Keyword-based transfers** (e.g., "OWN ACCOUNT", "INTERNAL TRANSFER") remain excluded

### Debt Categories (Updated Late 2025)

The following debt categories contain verified active UK lenders only. Defunct lenders (Wonga, QuickQuid, Sunny, etc.) have been removed.

#### 1. HCSTC / Payday / Short-Term (Active & Trading)

| Lender             | Type                                            |
| ------------------ | ----------------------------------------------- |
| Lending Stream     | Loans 6–12 months                               |
| Drafty             | Line of Credit                                  |
| Mr Lender          | Installment loans                               |
| Moneyboat          | Installment loans                               |
| CreditSpring       | Subscription finance (monthly fee for 0% loans) |
| Cashfloat          | Short-term loans                                |
| QuidMarket         | Short-term installment loans                    |
| Loans 2 Go         | Unsecured personal loans                        |
| CashASAP           | Short-term payday style                         |
| Polar Credit       | Line of Credit                                  |
| 118 118 Money      | Personal loans & Credit cards                   |
| The Money Platform | Peer-to-Peer short-term lending                 |
| Fast Loan UK       | Short-term loans                                |
| Conduit            | CDFI – Non-profit alternative                   |
| Salad Money        | Open Banking lender (NHS/Public sector)         |
| Fair Finance       | Ethical/Non-profit lender                       |

#### 2. Other Loans (Personal & Sub-Prime)

| Lender      | Type                                          |
| ----------- | --------------------------------------------- |
| Finio Loans | Formerly Likely Loans – Bad credit specialist |
| Evlo        | Formerly Everyday Loans – Branch-based        |
| Bamboo      | Unsecured loans                               |
| Novuna      | Prime/Good credit (formerly Hitachi)          |
| Zopa        | Prime/Good credit                             |
| Livelend    | Reward loan – rate drops if paid on time      |

#### 3. Credit Cards (Credit Builder & Bad Credit)

- Vanquis
- Aqua
- Capital One
- Marbles
- Zable (App-based, formerly Lendable/Level)
- Tymit (Installment-based credit card)
- 118 118 Money Card
- Fluid
- Chrome (Administered by Vanquis)

#### 4. Buy Now Pay Later (BNPL)

- Klarna
- Clearpay
- Zilch
- Monzo Flex
- PayPal Pay in 3
- Riverty (Formerly AfterPay in EU)
- Payl8r

### Essential Living Costs

Essential expenses are used to calculate disposable income (Income - Essentials - Debt):

| Category           | Examples                              | Impact on Score                           |
| ------------------ | ------------------------------------- | ----------------------------------------- |
| **Housing**        | Rent, Mortgage, Housing Association   | Major expense - reduces disposable income |
| **Council Tax**    | Local Authority, Borough/City Council | Fixed regular cost                        |
| **Utilities**      | British Gas, EDF, Water companies     | Essential services                        |
| **Transport**      | Fuel, TfL, Rail, Parking              | Necessary for employment                  |
| **Groceries**      | Tesco, Sainsbury's, Asda, Morrisons   | Basic living costs                        |
| **Communications** | BT, Sky, Mobile contracts             | Modern essentials                         |
| **Insurance**      | Car, Home, Life insurance             | Required coverage                         |
| **Childcare**      | Nursery, Childminder, After school    | Critical for working parents              |

### Risk Indicators

Risk indicators are negative signals that reduce credit score or trigger declines:

#### Gambling Activity

- **Lenders**: Bet365, Betfair, William Hill, Ladbrokes, Coral, Paddy Power, etc.
- **Impact**:
  - 0% of income: +8.75 points
  - <2%: +5.25 points
  - 2-5%: 0 points
  - 5-10%: -5.25 points (penalty)
  - > 10%: -8.75 points (penalty)
  - > 15%: **Hard decline**
- **Lookback**: Last 90 days

#### Failed Payments

- **Indicators**: "UNPAID DD", "RETURNED PAYMENT", "BOUNCED DD", "PAYMENT FAILED"
- **Impact**: -3.5 points per failed payment (max 14 points)
- **Hard Decline**: 6+ failed payments in last 45 days
- **Lookback**: Last 45 days for hard decline, full period for scoring

#### Bank Charges

- **Types**: "UNPAID ITEM CHARGE", "RETURNED DD FEE", "INSUFFICIENT FUNDS FEE"
- **Impact**: Indicates financial stress and poor money management
- **Threshold**: 3+ charges in 90 days triggers concerns

#### Debt Collection

- **Agencies**: Lowell, Cabot, Intrum, Hoist, Arrow Global, Moorcroft, etc.
- **Impact**: Strong negative signal of past credit problems
- **Hard Decline**: 4+ distinct debt collection agencies
- **Scoring**: Presence reduces risk score

#### HCSTC History

- **Impact**: Active HCSTC loans indicate existing credit stress
  - 0 lenders: +8.75 points
  - 1 lender: +3.5 points
  - 2+ lenders: 0 points + -17.5 penalty
- **Hard Decline**: 7+ active HCSTC lenders in last 90 days

## Configuration Parameters

All scoring parameters are configurable in `config/categorization_patterns.py`. Key adjustable thresholds include:

### Hard Decline Thresholds

```python
"hard_decline_rules": {
    "min_monthly_income": 1000,              # Minimum monthly income (£)
    "max_active_hcstc_lenders": 6,           # Maximum HCSTC lenders in 90 days
    "max_gambling_percentage": 15,           # Maximum gambling as % of income
    "min_post_loan_disposable": 0,           # Minimum disposable income after loan (£)
    "max_failed_payments": 5,                # Maximum failed payments in 45 days
    "max_dca_count": 3,                      # Maximum debt collection agencies
    "max_dti_with_new_loan": 75,             # Maximum DTI % with new loan
    "hcstc_lookback_days": 90,               # Lookback period for HCSTC activity
    "failed_payment_lookback_days": 45,      # Lookback period for payment failures
}
```

### Product Limits

```python
PRODUCT_CONFIG = {
    "min_loan_amount": 200,                  # Minimum loan amount (£)
    "max_loan_amount": 1500,                 # Maximum loan amount (£)
    "available_terms": [3, 4, 5, 6],         # Available terms (months)
    "daily_interest_rate": 0.008,            # 0.8% per day (FCA cap)
    "total_cost_cap": 1.0,                   # 100% total cost cap
    "min_disposable_buffer": 50,             # Minimum post-loan disposable (£)
    "max_repayment_to_disposable": 0.70,     # Max 70% of disposable for repayment
    "expense_shock_buffer": 1.1,             # 10% buffer on essential expenses (affordability stress-test only, NOT used for displayed disposable income)
}
```

### Expense Buffer Clarification

**Important:** The 10% expense shock buffer is used **only for affordability decisions**, not for calculating monthly disposable income shown to customers.

- **Monthly Disposable Income** (displayed): `Income - Actual Expenses - Debt`
- **Affordability Decision** (internal): Uses `Income - (Essential × 1.1) - Discretionary - Debt` to stress-test

This ensures customers can afford the loan even if essential expenses (rent, utilities, groceries) increase by 10%.

### Decision Thresholds

```python
"score_ranges": {
    "approve": {"min": 70, "max": 175},      # Auto-approve threshold
    "refer": {"min": 45, "max": 69},         # Manual review range
    "decline": {"min": 0, "max": 44},        # Auto-decline threshold
}
```

### Income Weighting

Different income types are weighted based on reliability:

- **Salary, Benefits, Pension**: 100% (fully counted)
- **Gig Economy**: 70% (discounted for variability)
- **Other Verified Income**: 100%

### Categorization Patterns

The system uses keyword and regex patterns to categorize transactions. Key pattern groups include:

- **Income patterns**: Salary, benefits, pension, gig economy
- **Debt patterns**: HCSTC lenders, credit cards, loans, BNPL, catalogues
- **Essential expense patterns**: Rent, mortgage, utilities, groceries, transport
- **Risk patterns**: Gambling, bank charges, failed payments, debt collection
- **Transfer patterns**: To exclude internal transfers from income

All patterns are defined in `config/categorization_patterns.py` and can be customized for specific markets or lender requirements.

## Project Structure

```
OpenBankingHCSTCScorer/
├── app.py                          # Main Streamlit application
├── hcstc_batch_processor.py        # Batch processing class
├── transaction_categorizer.py       # Transaction categorisation logic
├── scoring_engine.py               # HCSTC scoring calculations
├── metrics_calculator.py           # Financial metrics calculations
├── requirements.txt                # Dependencies
├── run_hcstc_scorer.bat           # Windows launcher
├── README.md                       # Documentation
└── config/
    └── categorization_patterns.py  # Pattern definitions & scoring config
```

### Key Modules

- **app.py**: Streamlit web interface for batch processing CSV/JSON files
- **hcstc_batch_processor.py**: Orchestrates batch processing of multiple applications
- **transaction_categorizer.py**: Categorizes transactions using pattern matching and Plaid categories
- **scoring_engine.py**: Implements the 175-point scoring system and decision logic
- **metrics_calculator.py**: Calculates financial metrics (income, expenses, affordability, risk)
- **config/categorization_patterns.py**: All patterns, thresholds, and configuration parameters

## Dependencies

- streamlit>=1.28.0
- pandas>=2.0.0
- numpy>=1.24.0
- plotly>=5.15.0
- rapidfuzz>=3.0.0
- openpyxl>=3.1.0

## Documentation Index

This repository contains multiple documentation files for different use cases:

| Document                                                                     | Purpose                               | Audience             |
| ---------------------------------------------------------------------------- | ------------------------------------- | -------------------- |
| [README.md](README.md)                                                       | Getting started, usage guide          | All users            |
| [OPENBANKING_ENGINE_README.md](OPENBANKING_ENGINE_README.md)                 | Technical architecture, API reference | Developers           |
| [SCORING README.md](SCORING%20README.md)                                     | Scoring logic deep-dive               | Credit analysts      |
| [ENHANCED_CATEGORIZATION.md](ENHANCED_CATEGORIZATION.md)                     | Categorization features               | Developers, analysts |
| [INCOME_CLASSIFICATION_FIX_SUMMARY.md](INCOME_CLASSIFICATION_FIX_SUMMARY.md) | Income detection fix changelog        | Developers, QA       |
| [CHANGELOG.md](CHANGELOG.md)                                                 | Version history and breaking changes  | All users            |

**Quick Links:**

- Need to understand scoring? → [SCORING README.md](SCORING%20README.md)
- Want to customize categories? → [ENHANCED_CATEGORIZATION.md](ENHANCED_CATEGORIZATION.md)
- Building an integration? → [OPENBANKING_ENGINE_README.md](OPENBANKING_ENGINE_README.md)

## License

This project is for educational and demonstration purposes.

## Disclaimer

This software is provided for demonstration purposes only. It should not be used as the sole basis for lending decisions. Always ensure compliance with FCA regulations and conduct appropriate due diligence
