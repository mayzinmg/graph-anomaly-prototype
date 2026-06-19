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

<<<<<<< HEAD
def get_severity(score:int)-> str:
    if score>=90:
        return "Critical"
    if score>=60:
        return "High"
    if score>=30:
        return "Medium"
    return "Low"

def main()-> None:
=======

def load_transactions() -> pd.DataFrame:
>>>>>>> dd07b3bde4b41b69097f4dec8a5cdb0967cb124f
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


def main() -> None:
    transactions = load_transactions()
    featured = add_graph_features(transactions)

    print("Graph features calculated.")
    print(
        featured[
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
            ]
        ]
    )



if __name__ == "__main__":
    main()