# Transaction Categorization Review Dashboard

## Quick Start (30 seconds)

```bash
# 1. Install dependencies (if not already installed)
pip install flask

# 2. Start the dashboard
python dashboard.py

# 3. Open browser to http://localhost:5001

# 4. Upload JSON files, click "Analyze Transactions", review results
```

---

## Overview

The Transaction Categorization Review Dashboard is a non-intrusive, read-only Flask-based web application designed to help analyze and review how transactions are being categorized by the OpenBanking HCSTC Scorer system. This tool is ideal for:

- Identifying miscategorizations in transaction data
- Understanding how the categorization engine processes different transactions
- Analyzing confidence scores and match methods
- Finding patterns that need rule adjustments
- Generating reports for manual review

**Important:** This dashboard does NOT modify any core categorization logic. It's a pure analysis tool that reads from the existing `TransactionCategorizer` and related modules.

## Features

### 📁 Batch Upload

- Upload multiple JSON files containing transaction data
- Supports both array format `[{...}, {...}]` and object format `{"transactions": [{...}]}`
- Processes files independently and aggregates results

### 📊 Detailed Analysis

For each transaction, the dashboard displays:

- **Transaction Details**: Description, amount, date, merchant name
- **Categorization Results**: Category, subcategory, confidence score
- **Match Information**: How the transaction was categorized (keyword, regex, fuzzy, plaid, behavioral)
- **PLAID Categories**: Both primary and detailed PLAID categories if available
- **Risk Indicators**: Risk level for high-risk categories (gambling, crypto, etc.)
- **Stability Flags**: Whether income is considered stable, housing expenses, etc.

### 🔍 Review Features

- **Summary Statistics**: Overview of total transactions, income/expense counts, confidence levels
- **Category Breakdown**: Visual breakdown by category and subcategory
- **Confidence Filtering**: Filter transactions by high/medium/low confidence
- **Category Filtering**: View transactions by specific category
- **Amount Range Filtering**: Filter by minimum and maximum transaction amounts
- **Search Functionality**: Search transactions by description
- **Low Confidence Alerts**: Automatically highlights transactions needing review with visual highlighting

### 📥 Export Capabilities

- **CSV Export**: Download filtered results in CSV format for spreadsheet analysis
- **JSON Export**: Export data in JSON format for further processing
- Exports include all categorization details and metadata

## Installation

### Prerequisites

- Python 3.8 or higher
- All dependencies from the main project

### Setup

1. Ensure you have the required dependencies installed:

```bash
pip install -r requirements.txt
```

This will install Flask (version 2.3.0 or higher) along with other dependencies.

2. No additional configuration needed - the dashboard uses the existing categorization modules.

## Usage

### Starting the Dashboard

Run the dashboard from the project root directory:

```bash
python dashboard.py
```

The dashboard will start on `http://localhost:5001` (port 5001 to avoid conflicts with the main Streamlit app).

**For development with auto-reload:**

```bash
FLASK_DEBUG=1 python dashboard.py
```

⚠️ **Note**: Debug mode should NOT be used in production as it poses security risks.

You should see output like:

```
================================================================================
Transaction Categorization Review Dashboard
================================================================================

Starting dashboard on http://localhost:5001
This is a READ-ONLY tool that does not modify core categorization logic.

Press Ctrl+C to stop the server.
================================================================================
```

### Accessing the Dashboard

Open your web browser and navigate to:

```
http://localhost:5001
```

### Uploading Transaction Data

1. **Prepare JSON Files**: Ensure your transaction files are in JSON format (see format requirements below)
2. **Upload**: Either drag-and-drop files onto the upload area or click to browse
3. **Analyze**: Click the "Analyze Transactions" button
4. **Review**: Explore the results, use filters, and identify potential issues

### Using Filters

- **Category Filter**: Narrow down to specific categories (income, debt, essential, etc.)
- **Confidence Filter**: Focus on high, medium, or low confidence transactions
- **Amount Range Filter**: Filter transactions by minimum and maximum amount (£)
  - Supports negative values for income (e.g., Min: -3000, Max: -1000 shows income between £1000-£3000)
  - Supports positive values for expenses (e.g., Min: 100, Max: 500 shows expenses between £100-£500)
  - Mix positive and negative to filter across transaction types
- **Search**: Find specific transactions by description text
- **Category Cards**: Click on category/subcategory cards to view only those transactions

Transactions with low confidence (< 60%) are automatically highlighted with a red background for easy identification.

### Exporting Results

1. Apply any filters you want
2. Click "Export CSV" or "Export JSON"
3. The file will download with a timestamp in the filename

## JSON File Format

The dashboard accepts transaction data in JSON format. Two structures are supported:

### Array Format (Preferred)

```json
[
  {
    "name": "ACME CORP LTD SALARY",
    "amount": -2500.0,
    "date": "2024-01-25",
    "merchant_name": "ACME CORP LTD",
    "personal_finance_category": {
      "primary": "INCOME",
      "detailed": "INCOME_WAGES"
    }
  },
  {
    "name": "TESCO STORES",
    "amount": 45.5,
    "date": "2024-01-26",
    "merchant_name": "TESCO",
    "personal_finance_category": {
      "primary": "GENERAL_MERCHANDISE",
      "detailed": "GENERAL_MERCHANDISE_SUPERSTORES"
    }
  }
]
```

### Object Format

```json
{
  "transactions": [
    {
      "name": "ACME CORP LTD SALARY",
      "amount": -2500.0,
      "date": "2024-01-25"
    }
  ]
}
```

### Field Descriptions

**Required Fields:**

- `name` (string): Transaction description/name
- `amount` (number): Transaction amount
  - **Negative values** = Credits (money IN to account, e.g., income)
  - **Positive values** = Debits (money OUT of account, e.g., expenses)
- `date` (string): Transaction date in YYYY-MM-DD format

**Optional Fields:**

- `merchant_name` (string): Merchant or company name
- `personal_finance_category` (object): PLAID categorization
  - `primary` (string): Primary category
  - `detailed` (string): Detailed subcategory
- `personal_finance_category.primary` (string): Flat format for primary category
- `personal_finance_category.detailed` (string): Flat format for detailed category

### Example Files

You can create sample files for testing:

**sample_salary.json:**

```json
[
  {
    "name": "BANK GIRO CREDIT ACME CORP",
    "amount": -2800.0,
    "date": "2024-01-25"
  },
  {
    "name": "BANK GIRO CREDIT ACME CORP",
    "amount": -2800.0,
    "date": "2024-02-25"
  },
  {
    "name": "BANK GIRO CREDIT ACME CORP",
    "amount": -2800.0,
    "date": "2024-03-25"
  }
]
```

**sample_mixed.json:**

```json
[
  {
    "name": "SALARY FROM EMPLOYER",
    "amount": -2500.0,
    "date": "2024-01-15"
  },
  {
    "name": "TESCO STORES",
    "amount": 85.3,
    "date": "2024-01-16"
  },
  {
    "name": "LENDING STREAM LOAN REPAY",
    "amount": 150.0,
    "date": "2024-01-17"
  },
  {
    "name": "UNIVERSAL CREDIT DWP",
    "amount": -450.0,
    "date": "2024-01-20"
  }
]
```

## Understanding the Results

### Confidence Scores

Confidence scores indicate how certain the categorization engine is about its classification:

- **High (≥ 0.80 / 80%)**: Strong match, likely correct
- **Medium (0.60-0.79 / 60-79%)**: Reasonable match, but worth reviewing
- **Low (< 0.60 / < 60%)**: Weak match, may be miscategorized

**Focus on low confidence transactions** - these are the most likely to need rule adjustments.

## Transaction Categorization Engine

### How Categorization Works

The categorization engine uses a **multi-step pipeline** to accurately classify banking transactions. Each transaction is processed through several stages to determine its category, subcategory, and confidence level:

**Pipeline Steps:**

1. **Text Normalization** - Transaction descriptions are normalized (uppercase, trimmed)
2. **HCSTC Lender Canonicalization** - Known lender variations are mapped to canonical names
3. **Strict PLAID Category Checks** - High-confidence PLAID categories processed first (TRANSFER_IN/OUT, loan disbursements)
4. **Known Expense Service Filtering** - Payment processors and BNPL services excluded from income
5. **PLAID Income Category Validation** - INCOME_WAGES checked first for employment income
6. **Pattern-Based Matching** - Sequential matching: keyword → regex → fuzzy
7. **Transfer Detection** - Multi-signal transfer detection with confidence scoring
8. **Fallback Categorization** - Default categories for unmatched transactions

### Match Methods Explained

The `match_method` field indicates how a transaction was categorized:

- **`keyword`** - Exact keyword match in transaction description
- **`regex`** - Regular expression pattern match for flexible matching
- **`fuzzy`** - Fuzzy string matching using rapidfuzz (similarity threshold: 80%)
- **`plaid`** - Categorized based on PLAID's personal_finance_category mapping
- **`plaid_strict`** - High-confidence PLAID categories (TRANSFER_IN/OUT, loans)
- **`plaid_income_wages`** - PLAID INCOME_WAGES detection (employment income)
- **`behavioral_*`** - (Deprecated) Recurring pattern detection methods
- **`known_service_exclusion`** - Known expense services excluded from income (e.g., PayPal, Klarna)

### Category Hierarchy & Details

#### 📥 Income Categories (Negative Amounts - Credits)

**`salary`** - Employment Income

- Weight: 1.0 (100% counted)
- Stable: Yes
- Examples: "SALARY FROM ACME LTD", "PAYROLL BACS", "MONTHLY WAGES", "NET PAY"
- Keywords: SALARY, WAGES, PAYROLL, PAYSLIP, NET PAY, PAYE
- Risk: None

**`benefits`** - Government Benefits

- Weight: 1.0 (100% counted)
- Stable: Yes
- Examples: "UNIVERSAL CREDIT DWP", "CHILD BENEFIT", "PIP PAYMENT", "JSA"
- Keywords: UNIVERSAL CREDIT, DWP, CHILD BENEFIT, PIP, DLA, ESA, JSA, PENSION CREDIT
- Risk: None

**`pension`** - Retirement Income

- Weight: 1.0 (100% counted)
- Stable: Yes
- Examples: "STATE PENSION", "ANNUITY PAYMENT", "PENSION DRAWDOWN"
- Keywords: STATE PENSION, ANNUITY, PENSION PAYMENT, OCCUPATIONAL PENSION
- Risk: None

**`gig_economy`** - Gig Economy Income

- Weight: 1.0 (100% counted for affordability)
- Stable: No (irregular income)
- Examples: "UBER PAYOUT", "DELIVEROO EARNINGS", "AMAZON FLEX", "ETSY SETTLEMENT"
- Keywords: UBER, DELIVEROO, JUST EAT, BOLT, FIVERR, UPWORK, AMAZON FLEX, ETSY, EBAY
- Risk: Income instability

**`loans`** - Loan Disbursements

- Weight: 0.0 (NOT counted as income)
- Stable: No
- Examples: "ZOPA LOAN DISBURSEMENT", "PERSONAL LOAN PAYOUT", "LENDABLE TRANSFER"
- Keywords: LOAN DISBURSEMENT, LOAN PAYOUT, ZOPA, LENDABLE
- PLAID: TRANSFER_IN_CASH_ADVANCES_AND_LOANS
- Risk: Debt increase

**`other`** - Other Income Sources

- Weight: 0.5-1.0 (depending on verification)
- Stable: No
- Examples: Unverified transfers, miscellaneous credits
- Risk: Unverified income

#### 💳 Debt Categories (Positive Amounts - Debits)

**`hcstc_payday`** - HCSTC/Payday Lenders

- Risk Level: Very High / Critical
- Examples: "LENDING STREAM", "DRAFTY", "MONEYBOAT", "CASHFLOAT", "QUIDMARKET"
- Keywords: 30+ known HCSTC lenders (Lending Stream, Drafty, Mr Lender, etc.)
- Impact: High debt indicator, triggers hard decline at 7+ lenders

**`credit_cards`** - Credit Card Payments

- Risk Level: Low-Medium
- Examples: "VANQUIS PAYMENT", "BARCLAYCARD", "CAPITAL ONE", "AMEX"
- Keywords: VANQUIS, AQUA, CAPITAL ONE, BARCLAYCARD, AMEX, MBNA
- Impact: Managed credit, factored into DTI ratio

**`bnpl`** - Buy Now Pay Later

- Risk Level: High
- Examples: "KLARNA", "CLEARPAY", "ZILCH", "MONZO FLEX", "PAYPAL PAY IN 3"
- Keywords: KLARNA, CLEARPAY, ZILCH, PAYPAL PAY IN 3/4, LAYBUY
- Impact: Credit utilization indicator

**`catalogue`** - Catalogue Credit

- Risk Level: Medium
- Examples: "VERY.COM", "LITTLEWOODS", "JD WILLIAMS", "FREEMANS"
- Keywords: VERY, LITTLEWOODS, JD WILLIAMS, SIMPLY BE, JACAMO
- Impact: Sub-prime credit indicator

**`other_loans`** - Other Loan Payments

- Risk Level: Medium
- Examples: "ZOPA REPAYMENT", "CAR FINANCE", "PERSONAL LOAN PAYMENT"
- Keywords: ZOPA, NOVUNA, CAR FINANCE, LOAN REPAYMENT
- Impact: Debt servicing costs, DTI ratio

#### 🏠 Essential Expense Categories

**`rent`** - Rental Payments

- Housing: Yes
- Examples: "RENT TO LANDLORD", "LETTING AGENT", "HOUSING ASSOCIATION"
- Keywords: LANDLORD, LETTING AGENT, TENANCY, COUNCIL RENT
- Impact: Essential expense, housing cost

**`mortgage`** - Mortgage Payments

- Housing: Yes
- Examples: "MORTGAGE PAYMENT", "HOME LOAN", "NATIONWIDE MORTGAGE"
- Keywords: MORTGAGE, HOME LOAN, MTG
- Impact: Essential expense, housing cost

**`council_tax`** - Council Tax

- Examples: "COUNCIL TAX", "CITY COUNCIL TAX"
- Keywords: COUNCIL TAX, CTAX
- Impact: Essential expense

**`utilities`** - Gas, Electric, Water

- Examples: "BRITISH GAS", "EDF ENERGY", "THAMES WATER", "OCTOPUS ENERGY"
- Keywords: Energy suppliers, water companies, utility bills
- Impact: Essential expense

**`communications`** - Phone, Internet, TV

- Examples: "VIRGIN MEDIA", "VODAFONE", "BT BROADBAND", "SKY TV", "TV LICENCE"
- Keywords: Telecoms providers, broadband, mobile networks
- Impact: Essential expense

**`transport`** - Car, Fuel, Public Transport

- Examples: "SHELL FUEL", "TFL OYSTER", "TRAINLINE", "CONGESTION CHARGE"
- Keywords: SHELL, ESSO, TFL, NATIONAL RAIL, parking
- Impact: Essential expense

**`groceries`** - Food Shopping

- Examples: "TESCO STORES", "SAINSBURY'S", "ASDA", "MORRISONS", "ALDI", "LIDL"
- Keywords: Major supermarkets (excluding their banking services)
- Impact: Essential expense

**`insurance`** - Insurance Premiums

- Examples: "AVIVA", "DIRECT LINE", "CAR INSURANCE", "HOME INSURANCE"
- Keywords: Insurance providers, premium payments
- Impact: Essential expense

**`childcare`** - Childcare Costs

- Examples: "CHILDCARE PAYMENT", "CHILDMINDER", "NURSERY FEES", "AFTER SCHOOL CLUB"
- Keywords: CHILDCARE, CHILDMINDER, NURSERY, PRESCHOOL
- Impact: Essential expense

#### ⚠️ Risk Categories

**`gambling`** - Gambling Transactions

- Risk Level: Critical
- Examples: "BET365", "WILLIAM HILL", "LADBROKES", "BETFAIR", "SKYBET"
- Keywords: 20+ gambling operators and betting brands
- Impact: Hard decline at >15% of income, critical risk flag

**`bank_charges`** - Overdraft/Unpaid Fees

- Risk Level: High
- Examples: "UNPAID ITEM CHARGE", "OVERDRAFT FEE", "RETURNED DD FEE"
- Keywords: Unpaid charges, NSF fees, overdraft charges
- Impact: Account conduct penalty, mandatory referral at 3+

**`failed_payments`** - Failed Direct Debits

- Risk Level: Critical
- Examples: "UNPAID DIRECT DEBIT", "RETURNED DD", "BOUNCED PAYMENT"
- Keywords: Unpaid DD, returned payments, failed debits
- Impact: Hard decline at 6+ in 45 days

**`debt_collection`** - Debt Collection Agencies

- Risk Level: Severe/Critical
- Examples: "LOWELL", "CABOT", "INTRUM", "ARROW GLOBAL", "LINK FINANCIAL"
- Keywords: DCAs, debt collectors, recovery agencies
- Impact: Hard decline at 4+ distinct DCAs

#### ✅ Positive Categories

**`savings`** - Savings Activity

- Examples: "SAVINGS TRANSFER", "ISA", "MONEYBOX", "PLUM", "PREMIUM BONDS"
- Keywords: SAVINGS, ISA, INVESTMENT, savings apps
- Impact: Positive indicator (+5 bonus points)

#### 🔄 Transfer Categories

**`internal`** - Internal Transfers

- Weight: 0.0 (excluded from income/expense calculations)
- Examples: "OWN ACCOUNT TRANSFER", "BETWEEN ACCOUNTS", "FROM SAVINGS TO CURRENT"
- Keywords: OWN ACCOUNT, INTERNAL TRANSFER, SELF TRANSFER
- PLAID: TRANSFER_IN_ACCOUNT_TRANSFER, TRANSFER_OUT_ACCOUNT_TRANSFER
- Impact: Excluded (not counted)

### Confidence Scoring

Confidence scores indicate certainty of categorization:

- **High (≥ 0.80 / 80%)**: Strong match, likely correct (PLAID strict, exact keyword match)
- **Medium (0.60-0.79 / 60-79%)**: Reasonable match (regex, fuzzy match above threshold)
- **Low (< 0.60 / < 60%)**: Weak match, may be miscategorized (fuzzy below threshold, fallback)

**Focus on low confidence transactions** - these are most likely to need rule adjustments.

### PLAID Category Integration

The system prioritizes PLAID categories in this order:

1. **Strict PLAID Categories** (checked first):

   - `TRANSFER_IN_ACCOUNT_TRANSFER` → income/internal (weight: 0.0)
   - `TRANSFER_OUT_ACCOUNT_TRANSFER` → expense/internal (weight: 0.0)
   - `TRANSFER_IN_CASH_ADVANCES_AND_LOANS` → income/loans (weight: 0.0)

2. **High-Confidence PLAID Categories**:

   - `INCOME_WAGES` → income/salary (weight: 1.0, stable)
   - `LOAN_PAYMENTS` → income/loans (weight: 0.0)

3. **Pattern Matching Fallback**:
   - If PLAID categories don't match strict rules, keyword/regex/fuzzy matching is used
   - PLAID provides additional context but doesn't override strict rules

### Income Detection Methodology

The system uses a **PLAID-first approach** for income detection:

1. **Check PLAID INCOME_WAGES first** - Most reliable indicator of employment income
2. **Known expense service filtering** - Excludes PayPal, Klarna, BNPL services
3. **Strict PLAID category preservation** - Loans and transfers handled before keywords
4. **Keyword-based detection** - Salary keywords (SALARY, PAYROLL, WAGES, etc.)
5. **Regex pattern matching** - Flexible patterns for payroll variations
6. **Fuzzy matching** - Similarity scoring for close matches
7. **Default categorization** - Fallback to "other" with lower weight

### Risk Levels

Transactions are flagged with risk levels for underwriting:

- **Critical**: Gambling, failed payments, debt collection (immediate concern)
- **Very High**: HCSTC lenders at high counts
- **High**: Bank charges, BNPL usage
- **Medium**: Other loans, catalogue credit
- **Low**: Credit cards (managed credit)

## Troubleshooting

### Port Already in Use

If port 5001 is already in use, you can modify the port in `dashboard.py`:

```python
app.run(debug=True, port=5002, host='0.0.0.0')  # Change 5001 to 5002
```

### File Upload Fails

- **Check file size**: Max 16MB per request
- **Verify JSON format**: Use a JSON validator to ensure files are valid
- **Check field names**: Ensure required fields (`name`, `amount`, `date`) are present

### No Transactions Displayed

- Check browser console for errors (F12 → Console tab)
- Verify the JSON structure matches the expected format
- Ensure transactions have valid amounts (numbers, not strings)

### Low Performance with Large Files

The dashboard uses batch categorization which is optimized for large transaction sets. However:

- Very large files (10,000+ transactions) may take a few seconds to process
- Consider splitting extremely large datasets into multiple files

## Architecture

### Non-Intrusive Design

The dashboard follows a strict read-only architecture:

```
dashboard.py (Flask App)
    ↓ (reads only)
transaction_categorizer.py (Core Logic)
    ↓ (reads only)
income_detector.py (Behavioral Detection)
    ↓ (reads only)
config/categorization_patterns.py (Rules & Patterns)
```

**Key Principles:**

1. **No Modifications**: Dashboard never modifies core categorization code
2. **Read-Only Usage**: Only calls existing public methods
3. **Isolated Logic**: All dashboard-specific code is in `dashboard.py` and `templates/`
4. **No Side Effects**: Cannot change how the main application categorizes transactions

### Files Created

This dashboard adds only these files to the project:

- `dashboard.py` - Flask application
- `templates/dashboard.html` - Web interface
- `DASHBOARD_README.md` - This documentation
- Updates to `requirements.txt` - Added Flask dependency

No existing files are modified.

## Use Cases

### 1. Identifying Salary Miscategorization

**Scenario**: Some salary payments are being categorized as transfers instead of income.

**Steps:**

1. Upload transaction files
2. Filter by category: "income" and "transfer"
3. Look for low confidence scores
4. Check match methods - if PLAID categorization is wrong, you'll see it
5. Export results for further analysis

### 2. Finding Low Confidence Transactions

**Scenario**: Need to find transactions where the engine is uncertain.

**Steps:**

1. Upload files
2. Use the "Low Confidence" summary card to see the count
3. Filter by confidence: "Low (< 0.60)"
4. Review each transaction's description and categorization
5. Identify patterns that need new rules

### 3. Validating New Rules

**Scenario**: Added new categorization patterns, want to verify they work.

**Steps:**

1. Upload test data containing transactions that should match new rules
2. Check if transactions are categorized correctly
3. Review match methods to ensure new patterns are being used
4. Check confidence scores

### 4. Generating Review Reports

**Scenario**: Need a report for manual review by the team.

**Steps:**

1. Upload all transaction files
2. Apply relevant filters (e.g., low confidence only)
3. Export to CSV
4. Share with team for review

## Best Practices

1. **Start with Small Files**: Test with a small sample file first
2. **Use Meaningful Names**: Name JSON files descriptively (e.g., `january_transactions.json`)
3. **Review Low Confidence First**: Focus on transactions with confidence < 0.60
4. **Check Behavioral Detection**: Look for `behavioral_*` match methods - these indicate pattern-based detection
5. **Compare Categories**: Check if PLAID categories match your expectations
6. **Export for Analysis**: Use CSV export for deeper analysis in spreadsheets
7. **Regular Reviews**: Periodically review categorization to catch new patterns

## Limitations

- **File Size**: Maximum 16MB per upload (configurable in `dashboard.py`)
- **Real-Time Updates**: Dashboard shows a snapshot, not live data
- **No Database**: Results are not persisted; refresh loses data
- **Single User**: Not designed for concurrent multi-user access
- **Read-Only**: Cannot modify categorization rules from the dashboard

## Future Enhancements

Possible improvements for future versions:

- Save analysis sessions to database
- Compare categorization across different time periods
- Add more advanced filtering options
- Export confidence score trends
- Rule suggestion engine based on miscategorizations
- Integration with main Streamlit app

## Technical Details

- **Framework**: Flask 2.3.0+
- **Port**: 5001 (configurable)
- **Dependencies**: Uses existing project dependencies
- **Categorizer**: TransactionCategorizer (read-only)
- **Performance**: Optimized batch processing for large datasets

---

**Remember**: This is a diagnostic and review tool. It does not affect how the main application categorizes transactions. Use it to identify issues and understand categorization behavior before modifying core rules.
