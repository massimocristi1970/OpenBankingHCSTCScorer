import pandas as pd

OUTCOME_LABELS = {0: "Never paid", 1: "Partially repaid", 2: "Fully repaid"}

KEY_FEATURES = [
    "monthly_income",
    "effective_monthly_income",
    "income_stability_score",
    "income_regularity_score",
    "income_sources_count",
    "average_balance",
    "minimum_balance",
    "days_in_overdraft",
    "overdraft_frequency",
    "end_of_month_average",
    "failed_payments_count",
    "failed_payments_count_45d",
    "bank_charges_count",
    "bank_charges_count_90d",
    "new_credit_providers_90d",
    "gambling_percentage",
    "monthly_disposable",
    "disposable_ratio",
    "post_loan_disposable",
    "repayment_to_disposable_ratio",
    "debt_to_income_ratio",
    "monthly_essential_total",
    "monthly_debt_payments",
]


def main(path: str):
    df = pd.read_csv(path)

    # Filter rows that errored during build
    if "error" in df.columns:
        bad = df["error"].notna().sum()
        if bad:
            print(f"WARNING: {bad} rows contain errors. Filtering them out for analysis.")
        df = df[df["error"].isna()].copy()

    df["outcome_label"] = df["outcome"].map(OUTCOME_LABELS)

    print("\nOutcome counts:")
    print(df["outcome_label"].value_counts(dropna=False).to_string())

    print("\nMedians by outcome (commonality scan):")
    med = df.groupby("outcome_label")[KEY_FEATURES].median(numeric_only=True)
    print(med.round(2).to_string())

    # Simple “separation” score: (median_full - median_never) / pooled std
    print("\nSeparation hints (Never paid vs Fully repaid):")
    never = df[df["outcome"] == 0]
    full = df[df["outcome"] == 2]

    for col in KEY_FEATURES:
        if col not in df.columns:
            continue
        a = never[col].dropna()
        b = full[col].dropna()
        if len(a) < 30 or len(b) < 30:
            continue

        pooled_std = pd.concat([a, b]).std()
        if pooled_std == 0 or pd.isna(pooled_std):
            continue
        effect = (b.median() - a.median()) / pooled_std
        print(f"  {col:32s} effect≈ {effect: .2f}  (full {b.median():.2f} vs never {a.median():.2f})")

    print("\nBreakpoint suggestions (Never paid vs Fully repaid quartiles):")
    for col in KEY_FEATURES:
        if col not in df.columns:
            continue
        a = never[col].dropna()
        b = full[col].dropna()
        if len(a) < 50 or len(b) < 50:
            continue
        a_q = a.quantile([0.25, 0.5, 0.75])
        b_q = b.quantile([0.25, 0.5, 0.75])
        print(f"\n{col}")
        print(f"  Never paid   Q25/Q50/Q75: {a_q.iloc[0]:.2f} / {a_q.iloc[1]:.2f} / {a_q.iloc[2]:.2f}")
        print(f"  Fully repaid Q25/Q50/Q75: {b_q.iloc[0]:.2f} / {b_q.iloc[1]:.2f} / {b_q.iloc[2]:.2f}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python analyse_outcomes.py training_dataset.csv")
    main(sys.argv[1])
