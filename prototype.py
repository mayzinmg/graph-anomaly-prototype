from pathlib import Path

import pandas as pd


DATA_FILE = Path("data/transactions.csv")

REQUIRED_COLUMNS = {
    "transaction_id",
    "customer_id",
    "device_id",
    "card_id",
    "product_id",
    "cashier_id",
    "transaction_type",
    "amount",
    "event_time",
}


def load_transactions() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Cannot find the dataset: {DATA_FILE.resolve()}"
        )

    transactions = pd.read_csv(DATA_FILE)

    missing_columns = REQUIRED_COLUMNS.difference(transactions.columns)

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    transactions["event_time"] = pd.to_datetime(
        transactions["event_time"],
        errors="raise",
    )

    transactions["amount"] = pd.to_numeric(
        transactions["amount"],
        errors="raise",
    )

    transactions["transaction_type"] = (
        transactions["transaction_type"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    return transactions


def add_graph_features(transactions: pd.DataFrame) -> pd.DataFrame:
    featured = transactions.copy()

    customers_per_device = (
        featured.groupby("device_id")["customer_id"]
        .nunique()
    )

    customers_per_card = (
        featured.groupby("card_id")["customer_id"]
        .nunique()
    )

    refunds_per_cashier = (
        featured[featured["transaction_type"] == "refund"]
        .groupby("cashier_id")["transaction_id"]
        .count()
    )

    featured["customers_per_device"] = (
        featured["device_id"]
        .map(customers_per_device)
        .fillna(0)
        .astype(int)
    )

    featured["customers_per_card"] = (
        featured["card_id"]
        .map(customers_per_card)
        .fillna(0)
        .astype(int)
    )

    featured["refunds_per_cashier"] = (
        featured["cashier_id"]
        .map(refunds_per_cashier)
        .fillna(0)
        .astype(int)
    )

    return featured

def get_severity(score: int) -> str:
    if score >= 90:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"

def score_anomalies(featured: pd.DataFrame)-> pd.DataFrame:
    scored= featured.copy()

    anomaly_scores=[]
    explanations=[]

    for row in scored.itertuples(index=False):
        score=0
        reasons=[]

        if row.customers_per_device>=3:
            score +=30
            reasons.append(
                   f"{row.customers_per_device} customers shared device {row.device_id}"
            )
        if row.customers_per_card>=3:
            score +=35
            reasons.append(
                 f"{row.customers_per_card} customers shared card {row.card_id}"
            )
        if row.transaction_type == "refund" and row.refunds_per_cashier>=3:
            score +=20
            reasons.append(
                 f"Cashier {row.cashier_id} processed {row.refunds_per_cashier} refunds"
            )
        anomaly_scores.append(score)

        if reasons:
            explanations.append("; ".join(reasons))
        else:
            explanations.append("No suspicious patttern detected")
    
    scored["anomaly_score"]=anomaly_scores
    scored["severity"]=scored["anomaly_score"].apply(get_severity)
    scored["explanation"]=explanations

    return scored

        

def main() -> None:
    transactions = load_transactions()
    featured = add_graph_features(transactions)
    scored = score_anomalies(featured)

    print("Anomaly scoring completed.")
    print(
        scored[
            [
                "transaction_id",
                "customer_id",
                "device_id",
                "card_id",
                "cashier_id",
                "transaction_type",
                "customers_per_device",
                "customers_per_card",
                "refunds_per_cashier",
                "anomaly_score",
                "severity",
                "explanation",
            ]
        ]
    )


if __name__ == "__main__":
    main()