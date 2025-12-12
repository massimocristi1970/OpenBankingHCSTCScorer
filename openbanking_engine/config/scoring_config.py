"""
Scoring configuration for HCSTC Loan Scoring.
Contains scoring weights, thresholds, and decision rules.
"""

# Scoring Configuration
# NOTE: All point values have been rescaled by 1.75x (70/40) to shift passing threshold from ≥40 to ≥70
# Maximum possible score is now 175 (previously 100)
SCORING_CONFIG = {
    # Score ranges and decisions
    "score_ranges": {
        "approve": {"min": 70, "max": 175, "decision": "APPROVE"},
        "refer": {"min": 45, "max": 69, "decision": "REFER"},
        "decline": {"min": 0, "max": 44, "decision": "DECLINE"},
    },
    
    # Scoring weights (total = 175, previously 100)
    "weights": {
        "affordability": {
            "total": 78.75,  # Previously 45
            "dti_ratio": 31.5,  # Previously 18
            "disposable_income": 26.25,  # Previously 15
            "post_loan_affordability": 21,  # Previously 12
        },
        "income_quality": {
            "total": 43.75,  # Previously 25
            "income_stability": 21,  # Previously 12
            "income_regularity": 14,  # Previously 8
            "income_verification": 8.75,  # Previously 5
        },
        "account_conduct": {
            "total": 35,  # Previously 20
            "failed_payments": 14,  # Previously 8
            "overdraft_usage": 12.25,  # Previously 7
            "balance_management": 8.75,  # Previously 5
        },
        "risk_indicators": {
            "total": 17.5,  # Previously 10
            "gambling_activity": 8.75,  # Previously 5
            "hcstc_history": 8.75,  # Previously 5
        },
    },
    
    # Thresholds for scoring (all point values scaled by 1.75x)
    "thresholds": {
        "dti_ratio": [
            {"max": 15, "points": 31.5},  # Previously 18
            {"max": 25, "points": 26.25},  # Previously 15
            {"max": 35, "points": 21},  # Previously 12
            {"max": 45, "points": 14},  # Previously 8
            {"max": 55, "points": 7},  # Previously 4
            {"max": 100, "points": 0},
        ],
        "disposable_income": [
            {"min": 400, "points": 26.25},  # Previously 15
            {"min": 300, "points": 22.75},  # Previously 13
            {"min": 200, "points": 17.5},  # Previously 10
            {"min": 100, "points": 10.5},  # Previously 6
            {"min": 50, "points": 5.25},  # Previously 3
            {"min": 0, "points": 0},
        ],
        "income_stability": [
            {"min": 90, "points": 21},  # Previously 12
            {"min": 75, "points": 17.5},  # Previously 10
            {"min": 60, "points": 12.25},  # Previously 7
            {"min": 40, "points": 7},  # Previously 4
            {"min": 0, "points": 0},
        ],
        "gambling_percentage": [
            {"max": 0, "points": 8.75},  # Previously 5
            {"max": 2, "points": 5.25},  # Previously 3
            {"max": 5, "points": 0},
            {"max": 10, "points": -5.25},  # Previously -3
            {"max": 100, "points": -8.75},  # Previously -5
        ],
    },
    
    # Hard decline rules
    "hard_decline_rules": {
        "min_monthly_income": 1000,
        "max_active_hcstc_lenders": 6,  # 7+ triggers decline (in last 90 days) - adjusted for HCSTC market
        "max_gambling_percentage": 15,
        "min_post_loan_disposable": 0,  # Changed from £30 - allows tighter affordability with expense buffer
        "max_failed_payments": 5,  # 6+ triggers decline (in last 45 days) - adjusted for HCSTC market
        "max_dca_count": 3,  # 4+ triggers decline
        "max_dti_with_new_loan": 75,  # Adjusted from 70 - more realistic for HCSTC market
        "hcstc_lookback_days": 90,  # Days to look back for HCSTC lenders
        "failed_payment_lookback_days": 45,  # Days to look back for failed payments
    },
    
    # Loan amount determination by score (thresholds scaled by 1.75x)
    "score_based_limits": [
        {"min_score": 149, "max_amount": 1500, "max_term": 6},  # Previously 85
        {"min_score": 123, "max_amount": 1200, "max_term": 6},  # Previously 70
        {"min_score": 105, "max_amount": 800, "max_term": 5},   # Previously 60
        {"min_score": 88, "max_amount": 500, "max_term": 4},    # Previously 50
        {"min_score": 70, "max_amount": 300, "max_term": 3},    # Previously 40
        {"min_score": 0, "max_amount": 0, "max_term": 0},
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
    "max_repayment_to_disposable": 0.70,  # Max 70% of disposable
    "expense_shock_buffer": 1.1,  # 10% buffer on expenses for resilience assessment
}
