import os
import glob
import json
import pandas as pd

from openbanking_engine.categorisation.engine import TransactionCategorizer
from openbanking_engine.scoring.feature_builder import MetricsCalculator

import openbanking_engine.scoring.feature_builder as fb
import openbanking_engine.categorisation.engine as ce

print("feature_builder imported from:", fb.__file__)
print("categorisation engine imported from:", ce.__file__)
print("MetricsCalculator class from:", MetricsCalculator.__module__)
print("TransactionCategorizer class from:", TransactionCategorizer.__module__)

def load_json(path: str) -> dict:
    # Some exports contain non-utf8 bytes; fall back safely
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except UnicodeDecodeError:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)



def extract_transactions(payload: dict) -> list:
    if isinstance(payload.get("transactions"), list):
        return payload["transactions"]

    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("transactions"), list):
        return data["transactions"]

    for k, v in payload.items():
        if str(k).lower() == "transactions" and isinstance(v, list):
            return v

    return []


def extract_accounts(payload: dict) -> list:
    if isinstance(payload.get("accounts"), list):
        return payload["accounts"]

    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("accounts"), list):
        return data["accounts"]

    for k, v in payload.items():
        if str(k).lower() == "accounts" and isinstance(v, list):
            return v

    return []


def application_id_from_path(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _safe_float(x):
    try:
        return None if x is None else float(x)
    except Exception:
        return None


def main(json_glob: str, outcomes_csv: str, out_csv: str, months_of_data: int = 6):
    outcomes = pd.read_csv(outcomes_csv, dtype={"application_id": str})

    if not {"application_id", "outcome"}.issubset(outcomes.columns):
        raise ValueError("outcomes.csv must have columns: application_id,outcome")

    outcomes["application_id"] = outcomes["application_id"].astype(str).str.strip()
    outcomes["outcome"] = outcomes["outcome"].astype(int)

    invalid = outcomes[~outcomes["outcome"].isin([0, 1, 2])]
    if not invalid.empty:
        raise ValueError("outcomes.csv contains invalid outcome values (must be 0, 1, or 2)")

    outcome_map = dict(zip(outcomes["application_id"], outcomes["outcome"]))

    categorizer = TransactionCategorizer()
    calc = MetricsCalculator(lookback_months=months_of_data)

    files = glob.glob(json_glob, recursive=True)
    if not files:
        raise SystemExit(f"No JSON files matched: {json_glob}")

    rows = []
    missing_outcome = 0
    processed = 0
    empty_txns = 0

    for i, fp in enumerate(files, start=1):
        app_id = application_id_from_path(fp)
        print(f"[{i}/{len(files)}] Processing {app_id}")

        if app_id not in outcome_map:
            print("  → SKIPPED (no outcome)")
            missing_outcome += 1
            continue

        try:
            payload = load_json(fp)
            txns = extract_transactions(payload)
            accounts = extract_accounts(payload)

            if not txns:
                empty_txns += 1
                continue

            categorized = categorizer.categorize_transactions(txns)

            # Resolve category summary method safely (engine version tolerant)
            if hasattr(categorizer, "build_category_summary"):
                category_summary = categorizer.build_category_summary(categorized) # type: ignore[attr-defined]
            elif hasattr(categorizer, "get_category_summary"):
                category_summary = categorizer.get_category_summary(categorized)
            else:
                raise AttributeError(
                    "TransactionCategorizer has no category summary method "
                    "(expected build_category_summary or get_category_summary)"
                )

            # Resolve metrics calculation method safely
            if not hasattr(calc, "calculate_all_metrics"):
                raise AttributeError(
                    "MetricsCalculator.calculate_all_metrics not found — "
                    "feature_builder.py is out of sync"
            )
            metrics = calc.calculate_all_metrics( # type: ignore[attr-defined]
                category_summary=category_summary,
                transactions=txns,
                accounts=accounts,
                categorized_transactions=categorized
            )


            income = metrics.get("income")
            expenses = metrics.get("expenses")
            debt = metrics.get("debt")
            affordability = metrics.get("affordability")
            balance = metrics.get("balance")
            risk = metrics.get("risk")

            rows.append({
                "application_id": app_id,
                "outcome": outcome_map[app_id],

                "monthly_income": _safe_float(getattr(income, "monthly_income", None)),
                "effective_monthly_income": _safe_float(getattr(income, "effective_monthly_income", None)),
                "income_stability_score": _safe_float(getattr(income, "income_stability_score", None)),
                "income_regularity_score": _safe_float(getattr(income, "income_regularity_score", None)),
                "has_verifiable_income": int(bool(getattr(income, "has_verifiable_income", False))),
                "income_sources_count": len(getattr(income, "income_sources", []) or []),

                "average_balance": _safe_float(getattr(balance, "average_balance", None)),
                "minimum_balance": _safe_float(getattr(balance, "minimum_balance", None)),
                "days_in_overdraft": _safe_float(getattr(balance, "days_in_overdraft", None)),
                "overdraft_frequency": _safe_float(getattr(balance, "overdraft_frequency", None)),

                "failed_payments_count": _safe_float(getattr(risk, "failed_payments_count", None)),
                "failed_payments_count_45d": _safe_float(getattr(risk, "failed_payments_count_45d", None)),
                "bank_charges_count_90d": _safe_float(getattr(risk, "bank_charges_count_90d", None)),
                "gambling_percentage": _safe_float(getattr(risk, "gambling_percentage", None)),

                "debt_collection_activity": _safe_float(getattr(risk, "debt_collection_activity", None)),
                "new_credit_providers_90d": _safe_float(getattr(risk, "new_credit_providers_90d", None)),
                "savings_activity": _safe_float(getattr(risk, "savings_activity", None)),

                "monthly_disposable": _safe_float(getattr(affordability, "monthly_disposable", None)),
                "post_loan_disposable": _safe_float(getattr(affordability, "post_loan_disposable", None)),
                "disposable_ratio": _safe_float(getattr(affordability, "disposable_ratio", None)),
                "max_affordable_amount": _safe_float(getattr(affordability, "max_affordable_amount", None)),

                "monthly_essential_total": _safe_float(getattr(expenses, "monthly_essential_total", None)),
                "monthly_debt_payments": _safe_float(getattr(debt, "monthly_debt_payments", None)),
            })

            processed += 1

        except Exception as e:
            rows.append({
                "application_id": app_id,
                "outcome": outcome_map[app_id],
                "error": str(e)
            })

    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False, encoding="utf-8")

    print("\n--- SUMMARY ---")
    print(f"Files matched: {len(files):,}")
    print(f"Processed OK: {processed:,}")
    print(f"Skipped (no outcome): {missing_outcome:,}")
    print(f"Skipped (no transactions): {empty_txns:,}")
    print(f"Rows written: {len(df):,}")
    print(f"Saved to: {out_csv}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        raise SystemExit(
            "Usage:\n"
            "  python build_training_dataset.py <json_glob> <outcomes.csv> <out.csv> [months]\n"
        )

    main(
        json_glob=sys.argv[1],
        outcomes_csv=sys.argv[2],
        out_csv=sys.argv[3],
        months_of_data=int(sys.argv[4]) if len(sys.argv) >= 5 else 6
    )
