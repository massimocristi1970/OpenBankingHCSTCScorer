#!/usr/bin/env python3
"""
Backtesting script for HCSTC Scoring Model

This script validates scoring model changes against historical outcome data.
It compares the new recalibrated model against what decisions would have been
made and how they correlate with actual loan outcomes.

Usage:
    python backtest_scoring.py training_dataset.csv

Outputs:
    - Approval/Refer/Decline rates
    - Default rate among approved applications
    - Accuracy metrics by outcome
    - Score distribution analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import sys

# Outcome labels
OUTCOME_LABELS = {0: "Never paid", 1: "Partially repaid", 2: "Fully repaid"}


def calculate_risk_flags(row: pd.Series) -> Tuple[int, str, Dict]:
    """
    Calculate combined risk flags for tiered approval system.
    
    Returns:
        Tuple of (flag_count, risk_tier, flags_dict)
    """
    flags = {}
    
    # Flag 1: Low income stability
    stability = row.get('income_stability_score', 50) or 50
    flags['low_income_stability'] = stability < 50
    
    # Flag 2: Low debt management
    debt_payments = row.get('monthly_debt_payments', 200) or 200
    flags['low_debt_management'] = debt_payments < 200
    
    # Flag 3: Low credit activity
    credit_providers = row.get('new_credit_providers_90d', 10) or 10
    flags['low_credit_activity'] = credit_providers < 10
    
    # Flag 4: No savings
    savings = row.get('savings_activity', 5) or 5
    flags['no_savings'] = savings < 5
    
    # Count flags
    flag_count = sum(flags.values())
    
    # Determine tier
    if flag_count >= 3:
        risk_tier = "FLAG"
    elif flag_count == 2:
        risk_tier = "WATCH"
    else:
        risk_tier = "CLEAN"
    
    return flag_count, risk_tier, flags


def calculate_score_from_metrics(row: pd.Series) -> Tuple[float, str, Dict]:
    """
    Calculate score using the NEW recalibrated weights.
    
    Returns:
        Tuple of (score, decision, breakdown)
    """
    breakdown = {}
    
    # Calculate risk flags first
    flag_count, risk_tier, flags = calculate_risk_flags(row)
    breakdown['risk_flags'] = {
        'flag_count': flag_count,
        'risk_tier': risk_tier,
        'flags': flags
    }
    
    # 1. Income Quality Score (35 points max)
    # Income Stability (20 points max) - using recalibrated thresholds
    stability = row.get('income_stability_score', 0) or 0
    if stability >= 80:
        stability_points = 20
    elif stability >= 70:
        stability_points = 16
    elif stability >= 60:
        stability_points = 12
    elif stability >= 50:
        stability_points = 6
    else:
        stability_points = 0
    
    # Income Regularity (8 points max)
    regularity = row.get('income_regularity_score', 0) or 0
    regularity_points = min(8, regularity / 100 * 8)
    
    # Income Verification (5 points)
    has_verifiable = row.get('has_verifiable_income', 0) == 1
    verification_points = 5 if has_verifiable else 2.5
    
    # Credit History Bonus (2 points max) - NEW
    debt_payments = row.get('monthly_debt_payments', 0) or 0
    if debt_payments >= 200:
        credit_history_points = 2
    elif debt_payments >= 100:
        credit_history_points = 1.5
    elif debt_payments >= 50:
        credit_history_points = 1
    else:
        credit_history_points = 0
    
    income_score = min(35, stability_points + regularity_points + verification_points + credit_history_points)
    breakdown['income_quality'] = {
        'stability': stability_points,
        'regularity': round(regularity_points, 1),
        'verification': verification_points,
        'credit_history': credit_history_points,
        'total': round(income_score, 1)
    }
    
    # 2. Affordability Score (30 points max) - REDUCED from 45
    # DTI Ratio (12 points max)
    # Note: training data doesn't have DTI directly, estimate from debt/income
    monthly_income = row.get('effective_monthly_income', 0) or row.get('monthly_income', 0) or 1
    monthly_debt = row.get('monthly_debt_payments', 0) or 0
    dti = (monthly_debt / monthly_income * 100) if monthly_income > 0 else 100
    
    if dti <= 30:
        dti_points = 12
    elif dti <= 40:
        dti_points = 10
    elif dti <= 50:
        dti_points = 8
    elif dti <= 60:
        dti_points = 5
    elif dti <= 70:
        dti_points = 2
    else:
        dti_points = 0
    
    # Disposable Income (8 points max) - REDUCED from 15
    disposable = row.get('monthly_disposable', 0) or 0
    if disposable >= 300:
        disp_points = 8
    elif disposable >= 200:
        disp_points = 6
    elif disposable >= 100:
        disp_points = 4
    elif disposable >= 50:
        disp_points = 2
    else:
        disp_points = 0
    
    # Post-loan Affordability (10 points max) - REDUCED from 12
    post_loan = row.get('post_loan_disposable', 0) or 0
    post_loan_points = min(10, max(0, post_loan / 50 * 10))
    
    affordability_score = min(30, dti_points + disp_points + post_loan_points)
    breakdown['affordability'] = {
        'dti': dti_points,
        'disposable': disp_points,
        'post_loan': round(post_loan_points, 1),
        'total': round(affordability_score, 1)
    }
    
    # 3. Account Conduct Score (25 points max) - INCREASED from 20
    # Failed Payments (10 points max)
    failed = row.get('failed_payments_count', 0) or 0
    failed_points = max(0, 10 - failed * 2)
    
    # Overdraft Usage (8 points max)
    # NOTE: Reduced penalty - overdraft not predictive in CRA-approved populations
    overdraft_days = row.get('days_in_overdraft', 0) or 0
    if overdraft_days == 0:
        overdraft_points = 8
    elif overdraft_days <= 30:
        overdraft_points = 6  # Gentle decline
    elif overdraft_days <= 60:
        overdraft_points = 4
    else:
        overdraft_points = 2  # Only penalize extreme overdraft
    
    # Balance Management (7 points max)
    # NOTE: Flat points - balance not predictive in CRA-approved populations
    avg_balance = row.get('average_balance', 0)
    if avg_balance is not None:
        balance_points = 3.5  # Flat points - balance not predictive
    else:
        balance_points = 2.45
    
    conduct_score = min(25, failed_points + overdraft_points + balance_points)
    breakdown['account_conduct'] = {
        'failed_payments': failed_points,
        'overdraft': round(overdraft_points, 1),
        'balance': round(balance_points, 1),
        'total': round(conduct_score, 1)
    }
    
    # 4. Risk Indicators Score (10 points max)
    # Gambling (5 points)
    gambling_pct = row.get('gambling_percentage', 0) or 0
    if gambling_pct == 0:
        gambling_points = 5
    elif gambling_pct <= 2:
        gambling_points = 3
    elif gambling_pct <= 5:
        gambling_points = 0
    elif gambling_pct <= 10:
        gambling_points = -3
    else:
        gambling_points = -5
    
    # HCSTC History (5 points)
    # Use active_hcstc_count_90d if available, otherwise proxy from new_credit_providers
    hcstc_count = row.get('active_hcstc_count_90d') or row.get('new_credit_providers_90d', 0) or 0
    if hcstc_count == 0:
        hcstc_points = 5
    elif hcstc_count <= 2:
        hcstc_points = 4  # 1-2 is normal
    elif hcstc_count == 3:
        hcstc_points = 2.5  # 3 - some concern
    else:
        hcstc_points = 0  # 4+ - significant concern
    
    # NEW: Savings Behavior Bonus (up to 3 points)
    savings_score = row.get('savings_behavior_score', 0) or 0
    savings_bonus = min(3, savings_score)  # Already calculated in metrics
    
    # NEW: Income Trend Adjustment
    income_trend = row.get('income_trend', 'stable')
    if income_trend == 'increasing':
        trend_bonus = 2.0
    elif income_trend == 'decreasing':
        trend_bonus = -2.0
    else:
        trend_bonus = 0.0
    
    risk_score = gambling_points + hcstc_points + savings_bonus + trend_bonus
    breakdown['risk_indicators'] = {
        'gambling': gambling_points,
        'hcstc': hcstc_points,
        'savings_bonus': savings_bonus,
        'income_trend': trend_bonus,
        'total': risk_score
    }
    
    # Total Score
    total_score = max(0, min(100, income_score + affordability_score + conduct_score + risk_score))
    
    # Determine decision (using recalibrated thresholds)
    if total_score >= 60:  # LOWERED from 70 based on backtest analysis
        decision = "APPROVE"
    elif total_score >= 40:  # LOWERED from 45
        decision = "REFER"
    else:
        decision = "DECLINE"
    
    return total_score, decision, breakdown


def calculate_old_score_from_metrics(row: pd.Series) -> Tuple[float, str]:
    """
    Calculate score using the OLD weights for comparison.
    
    Returns:
        Tuple of (score, decision)
    """
    # 1. Income Quality Score (25 points max) - OLD
    stability = row.get('income_stability_score', 0) or 0
    if stability >= 90:
        stability_points = 12
    elif stability >= 78:
        stability_points = 10
    elif stability >= 66:
        stability_points = 7
    elif stability >= 50:
        stability_points = 4
    else:
        stability_points = 0
    
    regularity = row.get('income_regularity_score', 0) or 0
    regularity_points = min(8, regularity / 100 * 8)
    
    has_verifiable = row.get('has_verifiable_income', 0) == 1
    verification_points = 5 if has_verifiable else 2.5
    
    income_score = min(25, stability_points + regularity_points + verification_points)
    
    # 2. Affordability Score (45 points max) - OLD
    monthly_income = row.get('effective_monthly_income', 0) or row.get('monthly_income', 0) or 1
    monthly_debt = row.get('monthly_debt_payments', 0) or 0
    dti = (monthly_debt / monthly_income * 100) if monthly_income > 0 else 100
    
    if dti <= 30:
        dti_points = 18
    elif dti <= 40:
        dti_points = 15
    elif dti <= 50:
        dti_points = 12
    elif dti <= 60:
        dti_points = 8
    elif dti <= 70:
        dti_points = 4
    else:
        dti_points = 0
    
    disposable = row.get('monthly_disposable', 0) or 0
    if disposable >= 200:
        disp_points = 15
    elif disposable >= 150:
        disp_points = 13
    elif disposable >= 100:
        disp_points = 10
    elif disposable >= 50:
        disp_points = 6
    elif disposable >= 25:
        disp_points = 3
    else:
        disp_points = 0
    
    post_loan = row.get('post_loan_disposable', 0) or 0
    post_loan_points = min(12, max(0, post_loan / 50 * 12))
    
    affordability_score = min(45, dti_points + disp_points + post_loan_points)
    
    # 3. Account Conduct Score (20 points max) - OLD
    failed = row.get('failed_payments_count', 0) or 0
    failed_points = max(0, 8 - failed * 1.5)
    
    overdraft_days = row.get('days_in_overdraft', 0) or 0
    if overdraft_days == 0:
        overdraft_points = 7
    elif overdraft_days <= 5:
        overdraft_points = 5
    elif overdraft_days <= 15:
        overdraft_points = 5 - (overdraft_days - 5) * 0.5
    else:
        overdraft_points = 0
    overdraft_points = max(0, overdraft_points)
    
    avg_balance = row.get('average_balance', 0) or 0
    if avg_balance >= 500:
        balance_points = 5
    elif avg_balance >= 200:
        balance_points = 3.5
    elif avg_balance >= 0:
        balance_points = 1.75
    else:
        balance_points = 0
    
    conduct_score = min(20, failed_points + overdraft_points + balance_points)
    
    # 4. Risk Indicators Score (10 points max) - OLD
    gambling_pct = row.get('gambling_percentage', 0) or 0
    if gambling_pct == 0:
        gambling_points = 5
    elif gambling_pct <= 2:
        gambling_points = 3
    elif gambling_pct <= 5:
        gambling_points = 0
    elif gambling_pct <= 10:
        gambling_points = -3
    else:
        gambling_points = -5
    
    new_credit = row.get('new_credit_providers_90d', 0) or 0
    if new_credit <= 2:
        hcstc_points = 5
    elif new_credit <= 5:
        hcstc_points = 3.5
    else:
        hcstc_points = 0
    
    risk_score = gambling_points + hcstc_points
    
    total_score = max(0, min(100, income_score + affordability_score + conduct_score + risk_score))
    
    if total_score >= 70:
        decision = "APPROVE"
    elif total_score >= 45:
        decision = "REFER"
    else:
        decision = "DECLINE"
    
    return total_score, decision


def run_backtest(df: pd.DataFrame) -> Dict:
    """
    Run backtesting on the dataset.
    
    Returns:
        Dictionary with comparison metrics
    """
    results = {
        'new_model': {'scores': [], 'decisions': [], 'risk_tiers': [], 'flag_counts': []},
        'old_model': {'scores': [], 'decisions': []},
        'outcomes': []
    }
    
    print("Running backtest on {} applications...".format(len(df)))
    
    for idx, row in df.iterrows():
        new_score, new_decision, breakdown = calculate_score_from_metrics(row)
        old_score, old_decision = calculate_old_score_from_metrics(row)
        outcome = row.get('outcome', 2)
        
        # Extract risk tier info from breakdown
        risk_info = breakdown.get('risk_flags', {})
        risk_tier = risk_info.get('risk_tier', 'CLEAN')
        flag_count = risk_info.get('flag_count', 0)
        
        results['new_model']['scores'].append(new_score)
        results['new_model']['decisions'].append(new_decision)
        results['new_model']['risk_tiers'].append(risk_tier)
        results['new_model']['flag_counts'].append(flag_count)
        results['old_model']['scores'].append(old_score)
        results['old_model']['decisions'].append(old_decision)
        results['outcomes'].append(outcome)
    
    return results


def analyze_results(results: Dict) -> None:
    """Print detailed analysis of backtest results."""
    
    df = pd.DataFrame({
        'new_score': results['new_model']['scores'],
        'new_decision': results['new_model']['decisions'],
        'risk_tier': results['new_model']['risk_tiers'],
        'flag_count': results['new_model']['flag_counts'],
        'old_score': results['old_model']['scores'],
        'old_decision': results['old_model']['decisions'],
        'outcome': results['outcomes'],
        'outcome_label': [OUTCOME_LABELS.get(o, 'Unknown') for o in results['outcomes']]
    })
    
    print("\n" + "="*70)
    print("BACKTESTING RESULTS - RECALIBRATED vs ORIGINAL MODEL")
    print("="*70)
    
    # 1. Decision Distribution
    print("\n1. DECISION DISTRIBUTION")
    print("-"*40)
    print("\nNEW MODEL (Recalibrated):")
    new_dist = df['new_decision'].value_counts()
    for dec in ['APPROVE', 'REFER', 'DECLINE']:
        count = new_dist.get(dec, 0)
        pct = count / len(df) * 100
        print(f"  {dec:10s}: {count:5d} ({pct:5.1f}%)")
    
    print("\nOLD MODEL (Original):")
    old_dist = df['old_decision'].value_counts()
    for dec in ['APPROVE', 'REFER', 'DECLINE']:
        count = old_dist.get(dec, 0)
        pct = count / len(df) * 100
        print(f"  {dec:10s}: {count:5d} ({pct:5.1f}%)")
    
    # 2. Score Statistics
    print("\n2. SCORE STATISTICS")
    print("-"*40)
    print(f"\nNEW MODEL:  Mean={df['new_score'].mean():.1f}, Median={df['new_score'].median():.1f}, Std={df['new_score'].std():.1f}")
    print(f"OLD MODEL:  Mean={df['old_score'].mean():.1f}, Median={df['old_score'].median():.1f}, Std={df['old_score'].std():.1f}")
    
    # 3. Outcome Analysis for Approved Applications
    print("\n3. OUTCOME ANALYSIS FOR APPROVED APPLICATIONS")
    print("-"*40)
    
    for model_name, decision_col in [('NEW MODEL', 'new_decision'), ('OLD MODEL', 'old_decision')]:
        approved = df[df[decision_col] == 'APPROVE']
        if len(approved) > 0:
            never_paid = len(approved[approved['outcome'] == 0])
            partial = len(approved[approved['outcome'] == 1])
            full = len(approved[approved['outcome'] == 2])
            
            default_rate = never_paid / len(approved) * 100
            full_repay_rate = full / len(approved) * 100
            
            print(f"\n{model_name}:")
            print(f"  Approved: {len(approved)}")
            print(f"  Default rate (never paid): {default_rate:.2f}%")
            print(f"  Full repayment rate: {full_repay_rate:.2f}%")
            print(f"  Breakdown: {never_paid} never paid, {partial} partial, {full} full")
    
    # 4. Catch Rate (Defaults correctly declined)
    print("\n4. DEFAULT CATCH RATE")
    print("-"*40)
    
    defaults = df[df['outcome'] == 0]
    if len(defaults) > 0:
        new_caught = len(defaults[defaults['new_decision'] == 'DECLINE'])
        old_caught = len(defaults[defaults['old_decision'] == 'DECLINE'])
        
        print(f"\nDefaults in data: {len(defaults)}")
        print(f"NEW MODEL caught (declined): {new_caught} ({new_caught/len(defaults)*100:.1f}%)")
        print(f"OLD MODEL caught (declined): {old_caught} ({old_caught/len(defaults)*100:.1f}%)")
    
    # 5. Good Customer Miss Rate (Full repayers incorrectly declined)
    print("\n5. GOOD CUSTOMER MISS RATE")
    print("-"*40)
    
    good_customers = df[df['outcome'] == 2]
    if len(good_customers) > 0:
        new_missed = len(good_customers[good_customers['new_decision'] == 'DECLINE'])
        old_missed = len(good_customers[good_customers['old_decision'] == 'DECLINE'])
        
        print(f"\nGood customers (fully repaid): {len(good_customers)}")
        print(f"NEW MODEL missed (declined): {new_missed} ({new_missed/len(good_customers)*100:.1f}%)")
        print(f"OLD MODEL missed (declined): {old_missed} ({old_missed/len(good_customers)*100:.1f}%)")
    
    # 6. Decision Changes
    print("\n6. DECISION CHANGES (NEW vs OLD)")
    print("-"*40)
    
    changed = df[df['new_decision'] != df['old_decision']]
    print(f"\nTotal decisions changed: {len(changed)} ({len(changed)/len(df)*100:.1f}%)")
    
    if len(changed) > 0:
        print("\nChanges breakdown:")
        changes = changed.groupby(['old_decision', 'new_decision']).size().reset_index(name='count')
        for _, row in changes.iterrows():
            print(f"  {row['old_decision']} -> {row['new_decision']}: {row['count']}")
        
        # Analyze outcome of changed decisions
        print("\nOutcomes of changed decisions:")
        for outcome_val, outcome_label in OUTCOME_LABELS.items():
            outcome_changes = changed[changed['outcome'] == outcome_val]
            if len(outcome_changes) > 0:
                print(f"\n  {outcome_label} ({len(outcome_changes)} applications):")
                for _, row in outcome_changes.groupby(['old_decision', 'new_decision']).size().reset_index(name='count').iterrows():
                    print(f"    {row['old_decision']} -> {row['new_decision']}: {row['count']}")
    
    # 7. Score by Outcome
    print("\n7. SCORE DISTRIBUTION BY OUTCOME")
    print("-"*40)
    
    for outcome_val, outcome_label in OUTCOME_LABELS.items():
        subset = df[df['outcome'] == outcome_val]
        if len(subset) > 0:
            print(f"\n{outcome_label} (n={len(subset)}):")
            print(f"  NEW: Mean={subset['new_score'].mean():.1f}, Median={subset['new_score'].median():.1f}")
            print(f"  OLD: Mean={subset['old_score'].mean():.1f}, Median={subset['old_score'].median():.1f}")
    
    # 8. TIERED APPROVAL ANALYSIS (NEW)
    print("\n" + "="*70)
    print("8. TIERED APPROVAL ANALYSIS")
    print("="*70)
    
    print("\nRisk Tier Distribution:")
    print(f"{'Tier':<10} {'Total':>8} {'Defaults':>10} {'Default%':>10} {'FullRepay%':>12}")
    print("-"*55)
    
    for tier in ['CLEAN', 'WATCH', 'FLAG']:
        tier_df = df[df['risk_tier'] == tier]
        if len(tier_df) > 0:
            defaults = len(tier_df[tier_df['outcome'] == 0])
            full_repay = len(tier_df[tier_df['outcome'] == 2])
            default_rate = defaults / len(tier_df) * 100
            full_rate = full_repay / len(tier_df) * 100
            print(f"{tier:<10} {len(tier_df):>8} {defaults:>10} {default_rate:>9.1f}% {full_rate:>11.1f}%")
    
    # Tier effectiveness for approved applications
    print("\nTier Analysis for APPROVED Applications:")
    approved = df[df['new_decision'] == 'APPROVE']
    if len(approved) > 0:
        print(f"{'Tier':<10} {'Approved':>10} {'Defaults':>10} {'Default%':>10} {'Action':>20}")
        print("-"*65)
        
        for tier in ['CLEAN', 'WATCH', 'FLAG']:
            tier_approved = approved[approved['risk_tier'] == tier]
            if len(tier_approved) > 0:
                defaults = len(tier_approved[tier_approved['outcome'] == 0])
                default_rate = defaults / len(tier_approved) * 100
                action = {
                    'CLEAN': 'Standard terms',
                    'WATCH': 'Monitor closely',
                    'FLAG': 'Reduced amount/term'
                }.get(tier, '')
                print(f"{tier:<10} {len(tier_approved):>10} {defaults:>10} {default_rate:>9.1f}% {action:>20}")
    
    # 9. Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    # Calculate key metrics
    new_approved = df[df['new_decision'] == 'APPROVE']
    old_approved = df[df['old_decision'] == 'APPROVE']
    
    new_default_rate = len(new_approved[new_approved['outcome'] == 0]) / len(new_approved) * 100 if len(new_approved) > 0 else 0
    old_default_rate = len(old_approved[old_approved['outcome'] == 0]) / len(old_approved) * 100 if len(old_approved) > 0 else 0
    
    new_approval_rate = len(new_approved) / len(df) * 100
    old_approval_rate = len(old_approved) / len(df) * 100
    
    # Calculate tier breakdown
    flag_approved = len(approved[approved['risk_tier'] == 'FLAG']) if len(approved) > 0 else 0
    watch_approved = len(approved[approved['risk_tier'] == 'WATCH']) if len(approved) > 0 else 0
    clean_approved = len(approved[approved['risk_tier'] == 'CLEAN']) if len(approved) > 0 else 0
    
    print(f"""
    Metric                    NEW MODEL    OLD MODEL    CHANGE
    ----------------------------------------------------------------
    Approval Rate             {new_approval_rate:6.1f}%      {old_approval_rate:6.1f}%      {new_approval_rate - old_approval_rate:+5.1f}%
    Default Rate (Approved)   {new_default_rate:6.2f}%      {old_default_rate:6.2f}%      {new_default_rate - old_default_rate:+5.2f}%
    
    TIERED APPROVAL BREAKDOWN (NEW MODEL):
    ----------------------------------------------------------------
    CLEAN tier approvals:     {clean_approved:6d} ({clean_approved/len(approved)*100 if len(approved) > 0 else 0:5.1f}%)  - Standard terms
    WATCH tier approvals:     {watch_approved:6d} ({watch_approved/len(approved)*100 if len(approved) > 0 else 0:5.1f}%)  - Monitor closely  
    FLAG tier approvals:      {flag_approved:6d} ({flag_approved/len(approved)*100 if len(approved) > 0 else 0:5.1f}%)  - Reduced amount/term
    """)
    
    if new_default_rate < old_default_rate:
        print("    IMPROVEMENT: New model has LOWER default rate among approved applications")
    elif new_default_rate > old_default_rate:
        print("    WARNING: New model has HIGHER default rate among approved applications")
    else:
        print("    No change in default rate")


def main(path: str):
    """Main entry point."""
    print(f"Loading data from {path}...")
    df = pd.read_csv(path)
    
    # Filter rows with errors
    if 'error' in df.columns:
        bad = df['error'].notna().sum()
        if bad:
            print(f"WARNING: {bad} rows contain errors. Filtering them out.")
        df = df[df['error'].isna()].copy()
    
    print(f"Loaded {len(df)} valid applications")
    
    # Run backtest
    results = run_backtest(df)
    
    # Analyze results
    analyze_results(results)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python backtest_scoring.py training_dataset.csv")
        sys.exit(1)
    
    main(sys.argv[1])
