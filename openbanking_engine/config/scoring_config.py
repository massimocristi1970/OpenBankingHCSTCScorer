"""
Scoring configuration for HCSTC Loan Scoring.
Contains scoring weights, thresholds, and decision rules.
"""

# Scoring Configuration
# Maximum possible score is 100
SCORING_CONFIG = {
    # Score ranges and decisions
    "score_ranges": {
    "approve": {"min": 70, "max": 100, "decision": "APPROVE"},
    "refer": {"min": 45, "max": 69, "decision": "REFER"},
    "decline": {"min": 0, "max": 44, "decision": "DECLINE"},
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
            {"max": 30, "points": 18},
            {"max": 40, "points": 15},
            {"max": 50, "points": 12},
            {"max": 60, "points": 8},
            {"max": 70, "points": 4},
            {"max": 100, "points": 0},
        ],

        "disposable_income": [
            {"min": 200, "points": 15},  
            {"min": 150, "points": 13},  
            {"min": 100, "points": 10},  # Previously 10
            {"min": 50, "points": 6},  # Previously 6
            {"min": 25, "points": 3},  # Previously 3
            {"min": 0, "points": 0},
        ],
        "income_stability": [
            {"min": 90, "points": 12},
            {"min": 78, "points": 10},
            {"min": 66, "points": 7},
            {"min": 50, "points": 4},
            {"min": 0, "points": 0},
        ],

        "gambling_percentage": [
            {"max": 0, "points": 5},  # Previously 5
            {"max": 2, "points": 3},  # Previously 3
            {"max": 5, "points": 0},
            {"max": 10, "points": -3},  # Previously -3
            {"max": 100, "points": -5},  # Previously -5
        ],
    },
    
    # Rule configurations - easily toggle between DECLINE and REFER
    "rules": {
        "min_monthly_income": {
            "threshold": 1500,
            "action": "REFER",  # Change to "REFER" to make it a soft rule
            "description": "Minimum monthly income required"
        },
        "no_verifiable_income": {
            "threshold": 300,
            "action": "REFER",
            "description": "No verifiable income source and income below threshold"
        },
        "max_active_hcstc_lenders": {
            "threshold": 6,  # 7+ triggers action
            "action": "DECLINE",  # Change to "REFER" for manual review instead
            "lookback_days": 90,
            "description": "Maximum active HCSTC lenders in lookback period"
        },
        "max_gambling_percentage": {
            "threshold": 15,
            "action": "REFER",  # Change to "DECLINE" to make it harder
            "description": "Maximum percentage of income spent on gambling"
        },
        "min_post_loan_disposable": {
            "threshold": 50,
            "action": "REFER",  # Change to "REFER" for manual affordability review
            "description": "Minimum disposable income after loan payment"
        },
        "max_failed_payments": {
            "threshold": 2,  # 3+ in 45 days triggers
            "action": "REFER",
            "lookback_days": 45,
            "description": "Maximum failed payments in lookback period"
        },
        "max_dca_count": {
            "threshold":  4,  # 4+ triggers action
            "action": "REFER",  # Change to "REFER" for case-by-case review
            "description": "Maximum distinct debt collection agencies"
        },
        "max_dti_with_new_loan": {
            "threshold":  85,
            "action": "REFER",  # Change to "REFER" if you want manual DTI reviews
            "description": "Maximum debt-to-income ratio including new loan"
        },
    },

    # Backwards-compatibility alias (some code expects this key)
    "hard_decline_rules": {},

    
    # Loan amount determination by score (thresholds scaled by 1.75x)
    "score_based_limits": [
        {"min_score": 75, "max_amount": 1500, "max_term": 6},
        {"min_score": 65, "max_amount": 1200, "max_term": 6},
        {"min_score": 55, "max_amount": 800,  "max_term": 5},
        {"min_score": 45, "max_amount": 500,  "max_term": 4},
        {"min_score": 35, "max_amount": 300,  "max_term": 3},
        {"min_score": 0,  "max_amount": 0,    "max_term": 0},
    ],

    
    # Mandatory referral rules (not automatic declines)
    "mandatory_referral_rules": {
        "bank_charges_lookback_days": 90,  # Check for bank charges in last 3 months
        "bank_charges_threshold": 2,  # 3+ bank charges triggers referral
        "new_credit_lookback_days": 90,  # Check for new credit providers in last 3 months
        "new_credit_threshold": 5,  # 5+ new credit providers triggers referral
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
    "max_repayment_to_disposable": 1.0,  # Not included in scoring, just a product rule
    "expense_shock_buffer": 1.1,  # 10% buffer on expenses for resilience assessment
}
