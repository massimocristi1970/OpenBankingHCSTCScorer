# Transaction Categorization Review Dashboard

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
- **Search Functionality**: Search transactions by description
- **Low Confidence Alerts**: Automatically highlights transactions needing review

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
- **Search**: Find specific transactions by description text
- **Category Cards**: Click on category/subcategory cards to view only those transactions

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
    "amount": -2500.00,
    "date": "2024-01-25",
    "merchant_name": "ACME CORP LTD",
    "personal_finance_category": {
      "primary": "INCOME",
      "detailed": "INCOME_WAGES"
    }
  },
  {
    "name": "TESCO STORES",
    "amount": 45.50,
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
      "amount": -2500.00,
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
    "amount": -2800.00,
    "date": "2024-01-25"
  },
  {
    "name": "BANK GIRO CREDIT ACME CORP",
    "amount": -2800.00,
    "date": "2024-02-25"
  },
  {
    "name": "BANK GIRO CREDIT ACME CORP",
    "amount": -2800.00,
    "date": "2024-03-25"
  }
]
```

**sample_mixed.json:**
```json
[
  {
    "name": "SALARY FROM EMPLOYER",
    "amount": -2500.00,
    "date": "2024-01-15"
  },
  {
    "name": "TESCO STORES",
    "amount": 85.30,
    "date": "2024-01-16"
  },
  {
    "name": "LENDING STREAM LOAN REPAY",
    "amount": 150.00,
    "date": "2024-01-17"
  },
  {
    "name": "UNIVERSAL CREDIT DWP",
    "amount": -450.00,
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

### Match Methods

The `match_method` field explains how the transaction was categorized:

- **`keyword`**: Matched against keyword patterns in categorization rules
- **`regex`**: Matched using regular expressions
- **`fuzzy`**: Fuzzy string matching (similarity score)
- **`plaid`**: Categorized based on PLAID's personal_finance_category
- **`behavioral_*`**: Detected through behavioral analysis (recurring patterns, keywords)
  - `behavioral_recurring_income`: Recurring pattern detected
  - `behavioral_salary_keywords`: Payroll keywords found
  - `behavioral_benefit_keywords`: Benefits keywords found
  - `behavioral_plaid_income_category`: PLAID marked as income

### Categories

The dashboard categorizes transactions into these main categories:

**Income Categories:**
- `income/salary`: Employment income, wages, salaries
- `income/benefits`: Government benefits (Universal Credit, DWP, etc.)
- `income/pension`: Pension and retirement income
- `income/gig_economy`: Gig economy platforms (Uber, Deliveroo, etc.) - 70% weight
- `income/investment`: Investment returns, dividends
- `income/other`: Other income sources

**Expense Categories:**
- `debt/hcstc`: High-cost short-term credit lenders
- `debt/credit_card`: Credit card payments
- `debt/other_loans`: Other loan payments
- `essential/housing`: Rent, mortgage, housing costs
- `essential/utilities`: Utilities, phone, internet
- `essential/groceries`: Grocery shopping
- `essential/transport`: Transportation costs
- `risk/gambling`: Gambling transactions (critical risk)
- `risk/crypto`: Cryptocurrency transactions (critical risk)
- Other categories...

### Risk Levels

Some transactions are flagged with risk levels:
- **Critical**: Gambling, cryptocurrency (high concern)
- **High**: HCSTC lenders, payday loans
- **Medium**: Other loans, credit utilization

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

## Support

For issues or questions:
1. Check this documentation
2. Review the JSON file format requirements
3. Check browser console for error messages
4. Verify all dependencies are installed

## Technical Details

- **Framework**: Flask 2.3.0+
- **Port**: 5001 (configurable)
- **Dependencies**: Uses existing project dependencies
- **Categorizer**: TransactionCategorizer (read-only)
- **Performance**: Optimized batch processing for large datasets

---

**Remember**: This is a diagnostic and review tool. It does not affect how the main application categorizes transactions. Use it to identify issues and understand categorization behavior before modifying core rules.
