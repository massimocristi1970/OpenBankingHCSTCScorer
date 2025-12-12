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
            "FP-", "FASTER PAYMENT", "BGC"
        ],
        "regex_patterns": [
            r"(?i)salary|wages|payroll|net\s*pay",
            r"(?i)\b(employer|company)\s*(payment|pay)\b",
            r"(?i)bacs\s*credit",
            r"(?i)monthly\s*pay",
            r"(?i)^FP-.*",
            r"(?i)faster\s*payment",
            r"(?i)\bbgc\b",
            r"(?i)\b(ltd|plc|limited)\s*(credit|payment)",
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
    "loans": {
        "keywords": [
            "LOAN PAYMENT", "LOAN REPAYMENT", "LOAN DISBURSEMENT",
            "PERSONAL LOAN", "UNSECURED LOAN", "GUARANTOR LOAN",
             "LENDABLE", "ZOPA", "TOTALSA", "AQUA",
            "VISA DIRECT PAYMENT", "LOAN REVERSAL", "LOAN REFUND"
        ],
        "regex_patterns": [
            r"(?i)loan\s*(payment|repayment|disbursement)",
            r"(?i)personal\s*loan",
            r"(?i)unsecured\s*loan",
            r"(?i)guarantor\s*loan",
            r"(?i)mr\s*lender",
            r"(?i)lendable",
            r"(?i)\bzopa\b",
            r"(?i)totalsa",
            r"(?i)\baqua\b",
            r"(?i)visa\s*direct\s*payment",
            r"(?i)(loan|loans)\s*(reversal|refund)",
            r"(?i)reversal\s*of.*\bloan",
        ],
        "weight": 0.0,  # Not counted as income
        "is_stable": False,
        "description": "Loan Payments/Disbursements"
    },
    "refund": {
        "keywords": [
            "REFUND", "REFUNDED", "REIMBURSEMENT",
            "CASHBACK", "CREDIT ADJUSTMENT"
        ],
        "regex_patterns": [
            r"(?i)\brefund(ed)?\b",
            
            r"(?i)reimbursement",
            r"(?i)cash\s*back",
        ],
        "weight": 1.0,
        "is_stable": False,
        "description": "Refunds & Returns"
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
            "GRATTAN", "SIMPLY BE", "JACAMO", "AMBROSE WILSON", "FASHION WORLD",
            "CATALOGUE PAYMENT", "CATALOG PAYMENT"
        ],
        "regex_patterns": [
            r"(?i)\bvery\s*(catalogue|account|payment)?\b",
            r"(?i)littlewoods",
            r"(?i)\bstudio\s*(catalogue|account|payment)?\b",
            r"(?i)jd\s*williams",
            r"(?i)freemans",
            r"(?i)grattan",
            r"(?i)(marks\s*(&|and)?\s*spencer|m&s)\s*(catalogue|catalog)",
            r"(?i)catalogue\s*(payment|account|credit)",
            r"(?i)catalog\s*(payment|account|credit)",
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
    "BOUNCE FEE", "RETURNED PAYMENT FEE",
    "INSUFFICIENT FUNDS FEE", "NSF FEE", "OVERDRAFT FEE", "PENALTY CHARGE",
    "UNPAID CHARGE", "RETURNED FEE", "ITEM FEE",
    "CREDIT REVERSAL"   # (optional)
  ],
  "regex_patterns": [
    r"(?i)\b(unpaid|returned|bounced|failed|dishono(u)?red)\b.*\b(charge|fee)\b",
    r"(?i)\b(charge|fee)\b.*\b(unpaid|returned|bounced|failed|nsf|insufficient|dishono(u)?red)\b",
    r"(?i)\boverdraft\b.*\b(charge|fee)\b",
    r"(?i)\bnsf\b.*\b(charge|fee)\b",
    r"(?i)\binsufficient\s*funds\b.*\b(charge|fee)\b",
    r"(?i)\b(item|transaction)\b.*\b(charge|fee)\b",
    r"(?i)\bcredit\s*(reversal|adjustment)\b",
  ],
  "risk_level": "high",
  "description": "Bank charges for unpaid/returned items"
},

    "failed_payments": {
  "keywords": [
    "UNPAID DIRECT DEBIT", "UNPAID DD", "DD UNPAID",
    "RETURNED DIRECT DEBIT", "RETURNED DD", "DD RETURNED",
    "BOUNCED PAYMENT", "BOUNCED DD", "BOUNCED DIRECT DEBIT",
    "PAYMENT RETURNED", "PAYMENT BOUNCED", "PAYMENT FAILED",
    "FAILED DIRECT DEBIT", "FAILED DD", "DD FAILED",
    "DISHONOURED DD", "DISHONOURED DIRECT DEBIT", "DISHONOURED PAYMENT",
    "INSUFFICIENT FUNDS DD",
    "DD RETURN", "DIRECT DEBIT RETURN", "RETURNED PAYMENT"
  ],
  "regex_patterns": [
    r"(?i)\b(unpaid|returned|bounced|failed|dishono(u)?red)\b\s+(direct\s*debit|dd|payment)\b",
    r"(?i)\b(direct\s*debit|dd|payment)\b\s+\b(unpaid|returned|bounced|failed|dishono(u)?red)\b",
    r"(?i)\binsufficient\s*funds?\b\s+(direct\s*debit|dd)\b",
    r"(?i)\bdd\b\s+\b(return(ed)?|unpaid|bounced|failed)\b",
  ],
  "risk_level": "critical",
  "description": "Failed payment events (DD/payment returned/failed)"
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
