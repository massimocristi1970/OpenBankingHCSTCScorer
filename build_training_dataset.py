import os
import glob
import json
import pandas as pd

from openbanking_engine.categorisation.engine import TransactionCategorizer
from openbanking_engine.scoring.feature_builder import MetricsCalculator


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_transactions(payload: dict) -> list:
    """
    Handles common shapes:
      - {"transactions":[...]}
      - {"data":{"transactions":[...]}}
      - etc.
    """
    if isinstance(payload.get("transactions"), list):
        return payload["transactions"]

    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("transactions"), list):
        return data["transactions"]

    # Last resort: scan top-level for a key named transactions
    for k, v in payload.items():
        if str(k).lower() == "transactions" and isinstance(v, list):
            return v

    return []


def extract_accounts(payload: dict) -> list:
    """
    Some metric functions expect accounts (even if empty).
    Handles common shapes:
      - {"accounts":[...]}
      - {"data":{"accounts":[...]}}
      - etc.
    """
    if isinstance(payload.get("accounts"), list):
        return payload["accounts"]

    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("accounts"), list):
        return data["accounts"]

    # Last resort: scan top-level for a key named accounts
    for k, v in payload.items():
        if str(k).lower() == "accounts" and isinstance(v, list):
            return v

    return []


def application_id_from_path(path: str) -> str:
    # "...\Record_653482.json" -> "Record_653482"
    return os.path.splitext(os.path.basename(path))[0]


def _safe_float(x):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def main(json_glob: str, outcomes_csv: str, out_csv: str, months_of_data: int = 6):
    outcomes = pd.read_csv(outcomes_csv, dtype={"application_id": str})
    if "application_id" not in outcomes.columns or "outcome" not in outcomes.columns:
        raise ValueError("outcomes.csv must have columns: application_id,outcome")

    outcomes["application_id"] = outcomes["application_id"].astype(str).str.strip()
    outcomes["outcome"] = outcomes["outcome"].astype(int)

    # Basic validation
    invalid = outcomes[~outcomes["outcome"].isin([0, 1, 2])]
    if not invalid.empty:
        raise ValueError("outcomes.csv contains invalid outcome values (must be 0, 1, or 2)")

    outcome_map = dict(zip(outcomes["application_id"], outcomes["outcome"]))

    categorizer = TransactionCategorizer()
    # Your MetricsCalculator uses lookback_months rather than months_of_data param
    calc = MetricsCalculator(lookback_months=months_of_data)

    rows = []
    files = glob.glob(json_glob, recursive=True)
    if not files:
        raise SystemExit(f"No JSON files matched: {json_glob}")

    missing_outcome = 0
    processed = 0
    empty_txns = 0

    for fp in files:
        app_id = application_id_from_path(fp)
        if app_id not in outcome_map:
            missing_outcome += 1
            continue

        try:
            payload = load_json(fp)
            txns = extract_transactions(payload)
            accounts = extract_accounts(payload)

            if not txns:
                empty_txns += 1
                continue

            # Categorise (your engine keeps Plaid fields + adds category/subcategory/weight)
            if hasattr(categorizer, "categorize_transactions_batch"):
                categorized = categorizer.categorize_transactions_batch(txns)
            else:
                categorized = categorizer.categorize_transactions(txns)

            # Category summary is required by your MetricsCalculator signature
            category_summary = categorizer.get_category_summary(categorized)

            # Compute metrics (your engine signature)
            metrics = calc.calculate_all_metrics(
                category_summary=category_summary,
                transactions=txns,
                accounts=accounts,
                categorized_transactions=categorized
            )

            # In your repo this is a dict of dataclass-like objects:
            # metrics["income"], metrics["expenses"], metrics["debt"], metrics["affordability"], metrics["balance"], metrics["risk"]
            income = metrics.get("income")
            expenses = metrics.get("expenses")
            debt = metrics.get("debt")
            affordability = metrics.get("affordability")
            balance = metrics.get("balance")
            risk = metrics.get("risk")

            row = {
                "application_id": app_id,
                "outcome": outcome_map[app_id],

                # ---- Income ----
                "monthly_income": _safe_float(getattr(income, "monthly_income", None)),
                "effective_monthly_income": _safe_float(getattr(income, "effective_monthly_income", None)),
                "income_stability_score": _safe_float(getattr(income, "income_stability_score", None)),
                "income_regularity_score": _safe_float(getattr(income, "income_regularity_score", None)),
                "has_verifiable_income": int(bool(getattr(income, "has_verifiable_income", False))),
                "income_sources_count": len(getattr(income, "income_sources", []) or []),

                # ---- Balance / overdraft behaviour ----
                "average_balance": _safe_float(getattr(balance, "average_balance", None)),
                "minimum_balance": _safe_float(getattr(balance, "minimum_balance", None)),
                "days_in_overdraft": _safe_float(getattr(balance, "days_in_overdraft", None)),
                "overdraft_frequency": _safe_float(getattr(balance, "overdraft_frequency", None)),
                "end_of_month_average": _safe_float(getattr(balance, "end_of_month_average", None)),

                # ---- Risk flags / failed payments ----
                "failed_payments_count": _safe_float(getattr(risk, "failed_payments_count", None)),
                "failed_payments_count_45d": _safe_float(getattr(risk, "failed_payments_count_45d", None)),
                "bank_charges_count": _safe_float(getattr(risk, "bank_charges_count", None)),
                "bank_charges_count_90d": _safe_float(getattr(risk, "bank_charges_count_90d", None)),
                "debt_collection_activity": _safe_float(getattr(risk, "debt_collection_activity", None)),
                "new_credit_providers_90d": _safe_float(getattr(risk, "new_credit_providers_90d", None)),
                "gambling_percentage": _safe_float(getattr(risk, "gambling_percentage", None)),

                # ---- Affordability ----
                "monthly_disposable": _safe_float(getattr(affordability, "monthly_disposable", None)),
                "disposable_ratio": _safe_float(getattr(affordability, "disposable_ratio", None)),
                "post_loan_disposable": _safe_float(getattr(affordability, "post_loan_disposable", None)),
                "repayment_to_disposable_ratio": _safe_float(getattr(affordability, "repayment_to_disposable_ratio", None)),
                "max_affordable_amount": _safe_float(getattr(affordability, "max_affordable_amount", None)),
                "debt_to_income_ratio": _safe_float(getattr(affordability, "debt_to_income_ratio", None)),

                # ---- Useful context totals ----
                "monthly_essential_total": _safe_float(getattr(expenses, "monthly_essential_total", None)),
                "monthly_debt_payments": _safe_float(getattr(debt, "monthly_debt_payments", None)),
            }

            rows.append(row)
            processed += 1

        except Exception as e:
            # Don't die on one bad file
            rows.append({
                "application_id": app_id,
                "outcome": outcome_map[app_id],
                "error": str(e)
            })

    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False, encoding="utf-8")

    print(f"Matched outcomes: {len(outcome_map):,}")
    print(f"Files matched by glob: {len(files):,}")
    print(f"Rows written: {len(df):,}")
    print(f"Skipped (no outcome): {missing_outcome:,}")
    print(f"Skipped (no transactions): {empty_txns:,}")
    print(f"Processed (successful): {processed:,}")
    print(f"Saved: {out_csv}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        raise SystemExit(
            "Usage:\n"
            "  python build_training_dataset.py <json_glob> <outcomes.csv> <out.csv> [months_of_data]\n\n"
            "Example:\n"
            "  python build_training_dataset.py \"C:\\path\\to\\json\\**\\*.json\" outcomes.csv training_dataset.csv 6\n"
        )

    json_glob = sys.argv[1]
    outcomes_csv = sys.argv[2]
    out_csv = sys.argv[3]
    months = int(sys.argv[4]) if len(sys.argv) >= 5 else 6

    main(json_glob=json_glob, outcomes_csv=outcomes_csv, out_csv=out_csv, months_of_data=months)
