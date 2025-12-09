"""
Transaction categorization patterns for HCSTC Loan Scoring.
Patterns for UK consumer lending based on PLAID format transaction data.
"""

# Income Categories (Credits - negative amounts)
INCOME_PATTERNS = {
    "salary": {
        "keywords": [
            "SALARY", "WAGES", "PAYROLL", "NET PAY", "BACS", "PAY", 
            "EMPLOYERS", "EMPLOYER", "WAGE", "PAYSLIP",
            "FP-", "FASTER PAYMENT", "BGC", "CREDIT", "LTD", "PLC",
            "LIMITED", "DIRECT CREDIT", "BANK CREDIT", "CR"
        ],
        "regex_patterns": [
            r"(?i)salary|wages|payroll|net\s*pay",
            r"(?i)\b(employer|company)\s*(payment|pay)\b",
            r"(?i)bacs\s*credit",
            r"(?i)monthly\s*pay",
            r"(?i)^FP-.*",
            r"(?i)faster\s*payment",
            r"(?i)\bbgc\b",
            r"(?i)direct\s*credit",
            r"(?i)bank\s*credit",
            r"(?i)\b(ltd|plc|limited)\b",
        ],
        "weight": 1.0,
        "is_stable": True,
        "description": "Salary & Wages"
    },
    "benefits": {
        "keywords": [
            "UNIVERSAL CREDIT", "UC", "DWP", "HMRC", "CHILD BENEFIT", 
            "PIP", "DLA", "ESA", "JSA", "PENSION CREDIT", "HOUSING BENEFIT",
            "TAX CREDIT", "WORKING TAX", "CHILD TAX", "CARERS ALLOWANCE",
            "ATTENDANCE ALLOWANCE", "BEREAVEMENT", "MATERNITY ALLOWANCE"
        ],
        "regex_patterns": [
            r"(?i)universal\s*credit",
            r"(?i)\buc\b",
            r"(?i)\bdwp\b",
            r"(?i)\bhmrc\b",
            r"(?i)child\s*benefit",
            r"(?i)\bpip\b",
            r"(?i)\bdla\b",
            r"(?i)\besa\b",
            r"(?i)\bjsa\b",
            r"(?i)pension\s*credit",
            r"(?i)housing\s*benefit",
            r"(?i)tax\s*credit",
            r"(?i)carers?\s*allowance",
        ],
        "weight": 1.0,
        "is_stable": True,
        "description": "Benefits & Government Payments"
    },
    "pension": {
        "keywords": [
            "PENSION", "ANNUITY", "STATE PENSION", "NEST", "AVIVA",
            "LEGAL AND GENERAL", "SCOTTISH WIDOWS", "STANDARD LIFE",
            "PRUDENTIAL", "ROYAL LONDON", "AEGON", "RETIREMENT"
        ],
        "regex_patterns": [
            r"(?i)\bpension\b",
            r"(?i)annuity",
            r"(?i)state\s*pension",
            r"(?i)retirement\s*(income|payment)",
        ],
        "weight": 1.0,
        "is_stable": True,
        "description": "Pension Income"
    },
    "gig_economy": {
        "keywords": [
            "UBER", "DELIVEROO", "JUST EAT", "BOLT", "LYFT", 
            "FIVERR", "UPWORK", "EBAY", "VINTED", "DEPOP",
            "TASKRABBIT", "FREELANCER", "ETSY", "AMAZON FLEX"
        ],
        "regex_patterns": [
            r"(?i)\buber\b",
            r"(?i)deliveroo",
            r"(?i)just\s*eat",
            r"(?i)\bbolt\b",
            r"(?i)\blyft\b",
            r"(?i)fiverr",
            r"(?i)upwork",
            r"(?i)\bebay\b",
            r"(?i)vinted",
            r"(?i)depop",
        ],
        "weight": 0.7,  # Multiplier for effective income calculation (70% of actual value)
        "is_stable": False,
        "description": "Gig Economy Income"
    },
}

# Transfer patterns (NOT counted as income)
TRANSFER_PATTERNS = {
    "keywords": [
        "OWN ACCOUNT", "INTERNAL TRANSFER", "FROM SAVINGS", "FROM CURRENT", 
        "SELF TRANSFER", "MOVED FROM", "MOVED TO", "BETWEEN ACCOUNTS",
        "INTERNAL TFR"
    ],
    "regex_patterns": [
        r"(?i)own\s*account",
        r"(?i)internal\s*(transfer|tfr)",
        r"(?i)from\s*(savings|current)",
        r"(?i)between\s*accounts",
        r"(?i)self\s*transfer",
        r"(?i)(moved|move)\s*(from|to)\s*(savings|current)",
    ]
}

# Existing Debt Categories (CRITICAL for HCSTC)
# Updated late 2025 with verified active lenders only
DEBT_PATTERNS = {
    "hcstc_payday": {
        # Active & Trading HCSTC / Payday / Short-Term lenders as of late 2025
        "keywords": [
            "LENDING STREAM", "DRAFTY", "MR LENDER", "MONEYBOAT",
            "CREDITSPRING", "CASHFLOAT", "QUIDMARKET", "LOANS 2 GO",
            "CASHASAP", "POLAR CREDIT", "118 118 MONEY", "THE MONEY PLATFORM",
            "FAST LOAN UK", "CONDUIT", "SALAD MONEY", "FAIR FINANCE"
        ],
        "regex_patterns": [
            r"(?i)lending\s*stream",
            r"(?i)drafty",
            r"(?i)mr\s*lender",
            r"(?i)moneyboat",
            r"(?i)creditspring",
            r"(?i)cashfloat",
            r"(?i)quidmarket",
            r"(?i)loans\s*2\s*go",
            r"(?i)cashasap",
            r"(?i)polar\s*credit",
            r"(?i)118\s*118\s*money",
            r"(?i)the\s*money\s*platform",
            r"(?i)fast\s*loan\s*uk",
            r"(?i)conduit",
            r"(?i)salad\s*money",
            r"(?i)fair\s*finance",
        ],
        "risk_level": "very_high",
        "description": "HCSTC/Payday Lenders"
    },
    "other_loans": {
        # Personal, Guarantor & Sub-Prime loans (active lenders)
        "keywords": [
            "LOAN", "FINANCE", "HP", "CAR FINANCE", "ZOPA", "NOVUNA",
            "FINIO LOANS", "EVLO", "EVERYDAY LOANS", "BAMBOO", "LIVELEND",
            "FLA", "PERSONAL LOAN", "AUTO FINANCE", "VEHICLE FINANCE"
        ],
        "regex_patterns": [
            r"(?i)\bloan\s*(repayment|payment)?\b",
            r"(?i)finance\s*(payment|agreement)?",
            r"(?i)\bhp\s*(payment|repayment)?\b",
            r"(?i)car\s*finance",
            r"(?i)\bzopa\b",
            r"(?i)novuna",
            r"(?i)finio\s*loans?",
            r"(?i)\bevlo\b",
            r"(?i)everyday\s*loans?",
            r"(?i)bamboo",
            r"(?i)livelend",
        ],
        "risk_level": "medium",
        "description": "Other Loans"
    },
    "credit_cards": {
        # Credit Builder & Bad Credit cards (active providers)
        "keywords": [
            "VANQUIS", "AQUA", "CAPITAL ONE", "MARBLES", "ZABLE",
            "TYMIT", "118 118 MONEY CARD", "FLUID CARD", "CHROME CARD",
            "BARCLAYCARD", "AMEX", "MBNA", "NEWDAY", "VIRGIN MONEY",
            "SAINSBURYS BANK", "TESCO BANK", "M&S BANK", "HALIFAX",
            "LLOYDS", "HSBC", "NATIONWIDE", "NATWEST", "MONZO", "STARLING"
        ],
        "regex_patterns": [
            r"(?i)vanquis",
            r"(?i)\baqua\b",
            r"(?i)capital\s*one",
            r"(?i)marbles",
            r"(?i)zable",
            r"(?i)tymit",
            r"(?i)118\s*118\s*money\s*card",
            r"(?i)fluid\s*(card|credit|payment)",
            r"(?i)chrome\s*(card|credit|payment)",
            r"(?i)barclaycard",
            r"(?i)\bamex\b",
            r"(?i)american\s*express",
            r"(?i)\bmbna\b",
            r"(?i)newday",
            r"(?i)credit\s*card\s*(payment|minimum|balance)",
        ],
        "risk_level": "low",
        "description": "Credit Cards"
    },
    "bnpl": {
        # Buy Now Pay Later (active UK providers)
        "keywords": [
            "KLARNA", "CLEARPAY", "ZILCH", "MONZO FLEX",
            "PAYPAL PAY IN 3", "RIVERTY", "PAYL8R"
        ],
        "regex_patterns": [
            r"(?i)klarna",
            r"(?i)clearpay",
            r"(?i)zilch",
            r"(?i)monzo\s*flex",
            r"(?i)paypal\s*pay\s*in\s*3",
            r"(?i)riverty",
            r"(?i)payl8r",
        ],
        "risk_level": "medium",
        "description": "Buy Now Pay Later"
    },
    "catalogue": {
        "keywords": [
            "VERY", "LITTLEWOODS", "STUDIO", "JD WILLIAMS", "FREEMANS",
            "GRATTAN", "SIMPLY BE", "JACAMO", "AMBROSE WILSON", "FASHION WORLD"
        ],
        "regex_patterns": [
            r"(?i)\bvery\s*(catalogue|account|payment)?\b",
            r"(?i)littlewoods",
            r"(?i)\bstudio\s*(catalogue|account|payment)?\b",
            r"(?i)jd\s*williams",
            r"(?i)freemans",
            r"(?i)grattan",
        ],
        "risk_level": "medium",
        "description": "Catalogue Credit"
    },
}

# Essential Living Costs
ESSENTIAL_PATTERNS = {
    "rent": {
        "keywords": [
            "RENT", "LANDLORD", "LETTING", "TENANCY", "HOUSING ASSOCIATION",
            "COUNCIL RENT", "HA RENT", "PROPERTY RENT"
        ],
        "regex_patterns": [
            r"(?i)\brent\b",
            r"(?i)landlord",
            r"(?i)letting\s*(agent|agency)?",
            r"(?i)tenancy",
            r"(?i)housing\s*association",
        ],
        "is_housing": True,
        "description": "Rent"
    },
    "mortgage": {
        "keywords": [
            "MORTGAGE", "HOME LOAN", "NATIONWIDE", "HALIFAX", "SANTANDER",
            "BARCLAYS", "HSBC", "LLOYDS", "NATWEST", "TSB", "VIRGIN MONEY",
            "SKIPTON", "LEEDS", "YORKSHIRE", "COVENTRY"
        ],
        "regex_patterns": [
            r"(?i)mortgage",
            r"(?i)home\s*loan",
            r"(?i)building\s*society\s*(mortgage)?",
        ],
        "is_housing": True,
        "description": "Mortgage"
    },
    "council_tax": {
        "keywords": [
            "COUNCIL TAX", "LOCAL AUTHORITY", "BOROUGH COUNCIL", 
            "CITY COUNCIL", "DISTRICT COUNCIL", "COUNTY COUNCIL"
        ],
        "regex_patterns": [
            r"(?i)council\s*tax",
            r"(?i)(borough|city|district|county)\s*council",
            r"(?i)local\s*authority",
        ],
        "description": "Council Tax"
    },
    "utilities": {
        "keywords": [
            "BRITISH GAS", "EDF", "EON", "SSE", "OCTOPUS", "BULB",
            "SCOTTISH POWER", "THAMES WATER", "SEVERN TRENT", "ANGLIAN WATER",
            "UNITED UTILITIES", "SOUTHERN WATER", "YORKSHIRE WATER",
            "ELECTRICITY", "GAS", "WATER", "ENERGY"
        ],
        "regex_patterns": [
            r"(?i)british\s*gas",
            r"(?i)\bedf\b",
            r"(?i)\beon\b",
            r"(?i)\bsse\b",
            r"(?i)octopus\s*(energy)?",
            r"(?i)\bbulb\b",
            r"(?i)scottish\s*power",
            r"(?i)thames\s*water",
            r"(?i)severn\s*trent",
            r"(?i)(electricity|gas|water)\s*(bill|payment)?",
        ],
        "description": "Utilities"
    },
    "communications": {
        "keywords": [
            "BT", "SKY", "VIRGIN MEDIA", "VODAFONE", "EE", "O2", "THREE",
            "TV LICENCE", "PLUSNET", "TALKTALK", "NOW TV", "NETFLIX",
            "DISNEY", "AMAZON PRIME", "SPOTIFY", "APPLE"
        ],
        "regex_patterns": [
            r"(?i)\bbt\s*(broadband|phone|bill)?\b",
            r"(?i)\bsky\s*(tv|broadband|bill)?\b",
            r"(?i)virgin\s*media",
            r"(?i)vodafone",
            r"(?i)\bee\b",
            r"(?i)\bo2\b",
            r"(?i)\bthree\b",
            r"(?i)tv\s*lic(e|en)(s|c)e",
            r"(?i)mobile\s*(phone|contract|bill)",
        ],
        "description": "Communications"
    },
    "insurance": {
        "keywords": [
            "INSURANCE", "AVIVA", "DIRECT LINE", "ADMIRAL", "AA", "RAC",
            "CHURCHILL", "CONFUSED", "COMPARE THE MARKET", "MEERKAT",
            "HASTINGS", "MORE THAN", "SWINTON", "ESURE"
        ],
        "regex_patterns": [
            r"(?i)insurance\s*(premium|payment)?",
            r"(?i)aviva",
            r"(?i)direct\s*line",
            r"(?i)admiral",
            r"(?i)\baa\s*(insurance|breakdown)?\b",
            r"(?i)\brac\b",
            r"(?i)churchill",
            r"(?i)car\s*insurance",
            r"(?i)home\s*insurance",
            r"(?i)life\s*insurance",
        ],
        "description": "Insurance"
    },
    "transport": {
        "keywords": [
            "SHELL", "BP", "ESSO", "TEXACO", "FUEL", "PETROL", "DIESEL",
            "TFL", "OYSTER", "NATIONAL RAIL", "TRAINLINE", "RAILCARD",
            "BUS PASS", "PARKING", "CONGESTION"
        ],
        "regex_patterns": [
            r"(?i)\bshell\b",
            r"(?i)\bbp\b",
            r"(?i)\besso\b",
            r"(?i)texaco",
            r"(?i)\bfuel\b",
            r"(?i)petrol",
            r"(?i)\btfl\b",
            r"(?i)oyster",
            r"(?i)national\s*rail",
            r"(?i)trainline",
            r"(?i)parking",
            r"(?i)congestion\s*charge",
        ],
        "description": "Transport"
    },
    "groceries": {
        "keywords": [
            "TESCO", "SAINSBURY", "ASDA", "MORRISONS", "ALDI", "LIDL",
            "WAITROSE", "M&S FOOD", "MARKS SPENCER", "CO-OP", "COOP",
            "ICELAND", "FARMFOODS", "OCADO", "AMAZON FRESH"
        ],
        "regex_patterns": [
            r"(?i)tesco",
            r"(?i)sainsbury",
            r"(?i)\basda\b",
            r"(?i)morrisons",
            r"(?i)\baldi\b",
            r"(?i)\blidl\b",
            r"(?i)waitrose",
            r"(?i)marks\s*(and|&)?\s*spencer",
            r"(?i)co-?op",
            r"(?i)iceland",
            r"(?i)ocado",
        ],
        "description": "Groceries"
    },
    "childcare": {
        "keywords": [
            "NURSERY", "CHILDCARE", "CHILDMINDER", "CRECHE", "PRESCHOOL",
            "AFTER SCHOOL", "BREAKFAST CLUB", "HOLIDAY CLUB", "NANNY"
        ],
        "regex_patterns": [
            r"(?i)nursery",
            r"(?i)childcare",
            r"(?i)childminder",
            r"(?i)creche",
            r"(?i)pre-?school",
            r"(?i)after\s*school",
        ],
        "description": "Childcare"
    },
}

# Risk Indicator Categories
RISK_PATTERNS = {
    "gambling": {
        "keywords": [
            "BET365", "BETFAIR", "WILLIAM HILL", "LADBROKES", "CORAL",
            "PADDY POWER", "BETFRED", "888", "POKERSTARS", "NATIONAL LOTTERY",
            "GROSVENOR CASINO", "TOMBOLA", "SKYBET", "UNIBET", "BWIN",
            "BETWAY", "FANDUEL", "DRAFTKINGS", "CASUMO", "CASINO",
            "BINGO", "SLOTS", "POKER", "GAMBLING", "BETTING"
        ],
        "regex_patterns": [
            r"(?i)bet365",
            r"(?i)betfair",
            r"(?i)william\s*hill",
            r"(?i)ladbrokes",
            r"(?i)\bcoral\b",
            r"(?i)paddy\s*power",
            r"(?i)betfred",
            r"(?i)\b888\b",
            r"(?i)pokerstars",
            r"(?i)national\s*lottery",
            r"(?i)lotto",
            r"(?i)grosvenor",
            r"(?i)tombola",
            r"(?i)skybet",
            r"(?i)unibet",
            r"(?i)betway",
            r"(?i)casino",
            r"(?i)\bbingo\b",
            r"(?i)gambling",
            r"(?i)betting",
        ],
        "risk_level": "critical",
        "description": "Gambling"
    },
    "bank_charges": {
        "keywords": [
            "UNPAID ITEM CHARGE", "UNPAID TRANSACTION FEE", "RETURNED ITEM FEE",
            "RETURNED DD FEE", "UNPAID DD CHARGE", "UNPAID SO CHARGE",
            "ITEM CHARGE", "TRANSACTION FEE", "BOUNCE FEE", "RETURNED PAYMENT FEE",
            "INSUFFICIENT FUNDS FEE", "NSF FEE", "OVERDRAFT FEE", "PENALTY CHARGE",
            "UNPAID CHARGE", "RETURNED FEE", "ITEM FEE", "TRANSACTION CHARGE"
        ],
        "regex_patterns": [
            r"(?i)unpaid\s*(item|transaction|dd|direct\s*debit|so|standing\s*order)?\s*(charge|fee)",
            r"(?i)returned\s*(item|dd|direct\s*debit|payment)?\s*(charge|fee)",
            r"(?i)bounce\s*(charge|fee)",
            r"(?i)insufficient\s*funds\s*(charge|fee)",
            r"(?i)nsf\s*(charge|fee)",
            r"(?i)penalty\s*charge",
            r"(?i)overdraft\s*(charge|fee)",
            r"(?i)(item|transaction)\s*(charge|fee)",
        ],
        "risk_level": "high",
        "description": "Bank Charges for Unpaid Items"
    },
    "failed_payments": {
        "keywords": [
            "UNPAID", "RETURNED", "BOUNCED", "INSUFFICIENT", "NSF",
            "DECLINED", "FAILED", "REJECTED", "DISHONOURED", "DD RETURN",
            "DIRECT DEBIT RETURN", "PAYMENT FAILED", "INSUFFICIENT FUNDS"
        ],
        "regex_patterns": [
            r"(?i)unpaid",
            r"(?i)returned\s*(payment|dd|direct\s*debit)?",
            r"(?i)bounced",
            r"(?i)insufficient\s*(funds)?",
            r"(?i)\bnsf\b",
            r"(?i)declined",
            r"(?i)failed\s*(payment|dd|direct\s*debit)?",
            r"(?i)rejected",
            r"(?i)dishon(ou)?red",
            r"(?i)dd\s*return",
            r"(?i)direct\s*debit\s*return",
        ],
        "risk_level": "critical",
        "description": "Failed Payments"
    },
    "debt_collection": {
        "keywords": [
            "DEBT COLLECTION", "DCA", "LOWELL", "CABOT", "INTRUM",
            "HOIST", "PAST DUE CREDIT", "ARROW GLOBAL", "LINK FINANCIAL",
            "MOORCROFT", "CAPQUEST", "MACKENZIE HALL", "BW LEGAL",
            "CREDIT SOLUTIONS", "DEBT RECOVERY", "COLLECTIONS"
        ],
        "regex_patterns": [
            r"(?i)debt\s*collect(ion|or)?",
            r"(?i)\bdca\b",
            r"(?i)lowell",
            r"(?i)\bcabot\b",
            r"(?i)intrum",
            r"(?i)\bhoist\b",
            r"(?i)past\s*due\s*credit",
            r"(?i)arrow\s*global",
            r"(?i)link\s*financial",
            r"(?i)moorcroft",
            r"(?i)capquest",
            r"(?i)debt\s*recovery",
            r"(?i)collections?\s*(agency|agent)?",
        ],
        "risk_level": "severe",
        "description": "Debt Collection"
    },
}

# Positive Indicators
POSITIVE_PATTERNS = {
    "savings": {
        "keywords": [
            "SAVINGS", "ISA", "INVESTMENT", "MONEYBOX", "PLUM", "CHIP",
            "NUTMEG", "VANGUARD", "FIDELITY", "HARGREAVES", "AJ BELL",
            "PREMIUM BONDS", "NS&I"
        ],
        "regex_patterns": [
            r"(?i)\bsavings\b",
            r"(?i)\bisa\b",
            r"(?i)investment",
            r"(?i)moneybox",
            r"(?i)\bplum\b",
            r"(?i)\bchip\b",
            r"(?i)nutmeg",
            r"(?i)vanguard",
            r"(?i)premium\s*bonds?",
            r"(?i)ns&?i",
        ],
        "description": "Savings Activity"
    },
}

# Scoring Configuration
SCORING_CONFIG = {
    # Score ranges and decisions
    "score_ranges": {
        "approve": {"min": 70, "max": 100, "decision": "APPROVE"},
        "conditional": {"min": 50, "max": 69, "decision": "APPROVE WITH CONDITIONS"},
        "refer": {"min": 30, "max": 49, "decision": "REFER"},
        "decline": {"min": 0, "max": 29, "decision": "DECLINE"},
    },
    
    # Scoring weights (total = 100)
    "weights": {
        "affordability": {
            "total": 45,
            "dti_ratio": 18,
            "disposable_income": 15,
            "post_loan_affordability": 12,
        },
        "income_quality": {
            "total": 25,
            "income_stability": 12,
            "income_regularity": 8,
            "income_verification": 5,
        },
        "account_conduct": {
            "total": 20,
            "failed_payments": 8,
            "overdraft_usage": 7,
            "balance_management": 5,
        },
        "risk_indicators": {
            "total": 10,
            "gambling_activity": 5,
            "hcstc_history": 5,
        },
    },
    
    # Thresholds for scoring
    "thresholds": {
        "dti_ratio": [
            {"max": 15, "points": 18},
            {"max": 25, "points": 15},
            {"max": 35, "points": 12},
            {"max": 45, "points": 8},
            {"max": 55, "points": 4},
            {"max": 100, "points": 0},
        ],
        "disposable_income": [
            {"min": 400, "points": 15},
            {"min": 300, "points": 13},
            {"min": 200, "points": 10},
            {"min": 100, "points": 6},
            {"min": 50, "points": 3},
            {"min": 0, "points": 0},
        ],
        "income_stability": [
            {"min": 90, "points": 12},
            {"min": 75, "points": 10},
            {"min": 60, "points": 7},
            {"min": 40, "points": 4},
            {"min": 0, "points": 0},
        ],
        "gambling_percentage": [
            {"max": 0, "points": 5},
            {"max": 2, "points": 3},
            {"max": 5, "points": 0},
            {"max": 10, "points": -3},
            {"max": 100, "points": -5},
        ],
    },
    
    # Hard decline rules
    "hard_decline_rules": {
        "min_monthly_income": 1500,
        "max_active_hcstc_lenders": 2,  # 3+ triggers decline (in last 90 days)
        "max_gambling_percentage": 15,
        "min_post_loan_disposable": 0,  # Changed from £30 - allows tighter affordability with expense buffer
        "max_failed_payments": 2,  # 3+ triggers decline (in last 45 days)
        "max_dca_count": 2,  # 3+ triggers decline
        "max_dti_with_new_loan": 60,
        "hcstc_lookback_days": 90,  # Days to look back for HCSTC lenders
        "failed_payment_lookback_days": 45,  # Days to look back for failed payments
    },
    
    # Loan amount determination by score
    "score_based_limits": [
        {"min_score": 85, "max_amount": 1500, "max_term": 6},
        {"min_score": 70, "max_amount": 1200, "max_term": 6},
        {"min_score": 60, "max_amount": 800, "max_term": 5},
        {"min_score": 50, "max_amount": 500, "max_term": 4},
        {"min_score": 40, "max_amount": 300, "max_term": 3},
        {"min_score": 0, "max_amount": 0, "max_term": 0},
    ],
    
    # Mandatory referral rules (not automatic declines)
    "mandatory_referral_rules": {
        "bank_charges_lookback_days": 90,  # Check for bank charges in last 3 months
        "new_credit_lookback_days": 90,  # Check for new credit providers in last 3 months
        "new_credit_threshold": 3,  # 3+ new credit providers triggers referral
    },
}

# Product Parameters
PRODUCT_CONFIG = {
    "min_loan_amount": 200,
    "max_loan_amount": 1500,
    "available_terms": [3, 4, 5, 6],  # months
    "daily_interest_rate": 0.008,  # 0.8% per day (FCA cap)
    "total_cost_cap": 1.0,  # 100% total cost cap
    "min_disposable_buffer": 50,  # Minimum £50 post-loan disposable
    "max_repayment_to_disposable": 0.70,  # Max 70% of disposable
    "expense_shock_buffer": 1.1,  # 10% buffer on expenses for resilience assessment
}
