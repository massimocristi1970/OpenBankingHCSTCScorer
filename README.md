# OpenBankingHCSTCScorer

Open Banking HCSTC (High-Cost Short-Term Credit) Loan Scoring System - A Streamlit-based batch processing application for scoring consumer loan applications using Open Banking (PLAID format) transaction data.

## Overview

This application is designed for UK High-Cost Short-Term Credit (HCSTC) lenders operating under FCA regulation. It processes Open Banking transaction data to assess loan affordability and risk.

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

## Usage

### Uploading Files

The application accepts:
- Individual JSON files in PLAID format
- ZIP archives containing multiple JSON files

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

## Scoring System

### Score Ranges

| Score Range | Decision |
|-------------|----------|
| 70-100 | APPROVE |
| 50-69 | APPROVE WITH CONDITIONS |
| 30-49 | REFER (manual review) |
| 0-29 | DECLINE |

### Scoring Components (100 points total)

1. **Affordability (45 points)**
   - Debt-to-Income Ratio: 18 points
   - Disposable Income: 15 points
   - Post-Loan Affordability: 12 points

2. **Income Quality (25 points)**
   - Income Stability: 12 points
   - Income Regularity: 8 points
   - Income Verification: 5 points

3. **Account Conduct (20 points)**
   - Failed Payments: 8 points
   - Overdraft Usage: 7 points
   - Balance Management: 5 points

4. **Risk Indicators (10 points)**
   - Gambling Activity: 5 points
   - HCSTC History: 5 points

### Hard Decline Rules

Applications are automatically declined if:

- Monthly income < £500
- No identifiable income source
- Active HCSTC with 3+ lenders
- Gambling > 15% of income
- Post-loan disposable < £30
- 5+ failed payments in period
- Active debt collection (3+ DCAs)
- DTI would exceed 60% with new loan

## Transaction Categories

### Income Categories

- **Salary & Wages**: Regular employment income
- **Benefits & Government**: Universal Credit, DWP, HMRC payments
- **Pension**: State and private pension income
- **Gig Economy** (weighted at 70%): Uber, Deliveroo, freelance platforms

### Debt Categories

- **HCSTC/Payday**: High-cost short-term credit lenders
- **Other Loans**: Personal loans, car finance
- **Credit Cards**: Card payments and minimum payments
- **BNPL**: Buy Now Pay Later (Klarna, Clearpay, etc.)
- **Catalogue Credit**: Catalogue shopping credit

### Essential Living Costs

- Housing (Rent or Mortgage)
- Council Tax
- Utilities
- Transport
- Groceries
- Communications
- Insurance
- Childcare

### Risk Indicators

- **Gambling**: Betting, casino, lottery
- **Failed Payments**: Bounced, returned, declined payments
- **Debt Collection**: DCA activity

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
    └── categorization_patterns.py  # Pattern definitions
```

## Dependencies

- streamlit>=1.28.0
- pandas>=2.0.0
- numpy>=1.24.0
- plotly>=5.15.0
- rapidfuzz>=3.0.0
- openpyxl>=3.1.0

## License

This project is for educational and demonstration purposes.

## Disclaimer

This software is provided for demonstration purposes only. It should not be used as the sole basis for lending decisions. Always ensure compliance with FCA regulations and conduct appropriate due diligence