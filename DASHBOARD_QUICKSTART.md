# Transaction Categorization Dashboard - Quick Start Guide

## 🚀 Quick Start (30 seconds)

```bash
# 1. Install dependencies (if not already installed)
pip install flask

# 2. Start the dashboard
python dashboard.py

# 3. Open browser
# Navigate to: http://localhost:5001

# 4. Upload JSON files
# - Drag and drop JSON files with transaction data
# - Click "Analyze Transactions"
# - Review results, filter by confidence, export to CSV/JSON
```

## 📋 JSON File Format

Your JSON files should contain transaction data with these fields:

**Required:**
- `name` - Transaction description (string)
- `amount` - Transaction amount (number, negative = income, positive = expense)
- `date` - Date in YYYY-MM-DD format (string)

**Optional:**
- `merchant_name` - Merchant name (string)
- `personal_finance_category` - PLAID categories (object)

**Example:**
```json
[
  {
    "name": "BANK GIRO CREDIT SALARY",
    "amount": -2500.00,
    "date": "2024-01-25"
  },
  {
    "name": "TESCO STORES",
    "amount": 85.30,
    "date": "2024-01-26"
  }
]
```

## 🎯 What You'll See

- **Summary Cards**: Total transactions, income/expense counts, confidence levels
- **Category Breakdown**: Visual breakdown by category and subcategory
- **Transaction Table**: Detailed view with filters and search
- **Export Options**: Download results as CSV or JSON

## 🔍 Key Features

| Feature | What It Does |
|---------|-------------|
| **Confidence Filtering** | Focus on low/medium/high confidence transactions |
| **Category Drilling** | Click a category to see all transactions in it |
| **Search** | Find specific transactions by description |
| **Export** | Download filtered results for offline analysis |

## ⚠️ Important Notes

- **Read-Only**: Dashboard doesn't modify any core code
- **Negative Amounts**: Negative = Income (credits), Positive = Expenses (debits)
- **Gig Economy**: UBER/DELIVEROO with negative amounts = driver income
- **Debug Mode**: Only use `FLASK_DEBUG=1` in development, never in production

## 📊 Common Use Cases

### 1. Find Low Confidence Transactions
```
Filter by Confidence: Low (< 60%)
→ Review and identify patterns needing new rules
```

### 2. Validate Salary Detection
```
Filter by Category: income
→ Check if salaries are correctly identified
→ Look for match_method: behavioral_*
```

### 3. Identify Miscategorizations
```
Look at Low Confidence summary card
→ Click to see details
→ Export for team review
```

### 4. Check Risk Flags
```
Scroll through transaction table
→ Look for risk badges (critical/high/medium)
→ Verify gambling and crypto transactions are flagged
```

## 🆘 Troubleshooting

**Port already in use?**
Edit `dashboard.py` line 324: change `port=5001` to another port

**File won't upload?**
- Max size: 16MB
- Must be valid JSON
- Check field names match required format

**No transactions displayed?**
- Check browser console (F12 → Console)
- Verify amounts are numbers, not strings
- Ensure dates are in YYYY-MM-DD format

## 📚 More Information

For complete documentation, see: [DASHBOARD_README.md](DASHBOARD_README.md)

## ✅ Quick Validation Test

```bash
# Test the dashboard processes sample data correctly
python test_dashboard_functionality.py

# Expected output: "✓ All Dashboard Tests Passed!"
```

---

**Need Help?** Check [DASHBOARD_README.md](DASHBOARD_README.md) for detailed documentation.
