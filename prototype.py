from pathlib import Path

import pandas as pd


DATA_FILE = Path("data/transactions.csv")
OUTPUT_DIR = Path("output")
ANOMALY_OUTPUT_FILE = OUTPUT_DIR / "anomaly_results.csv"
GRAPH_NODES_OUTPUT_FILE = OUTPUT_DIR / "graph_nodes.csv"
GRAPH_EDGES_OUTPUT_FILE = OUTPUT_DIR / "graph_edges.csv"

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

def build_graph_nodes(scored: pd.DataFrame)->pd.DataFrame:

    node_rows=[]
    entity_columns={
        "Customer": "customer_id",
        "Transaction": "transaction_id",
        "Device": "device_id",
        "Card": "card_id",
        "Product": "product_id",
        "Cashier": "cashier_id",
    }

    for node_type,column_name in entity_columns.items():
        unique_ids= scored[column_name].dropna().unique()

        for business_id in unique_ids:
            node_rows.append(
                {
                    "node_id": f"{node_type}:{business_id}",
                    "node-type":node_type,
                    "business_id": business_id
                }
            )
    return pd.DataFrame(node_rows)

def build_graph_edges(scored:pd.DataFrame)->pd.DataFrame:
    edge_rows=[]

    for row in scored.itertuples(index=False):
        customer_node=f"Customer:{row.customer_id}"
        transaction_node= f"Transaction:{row.transaction_id}"
        device_node= f"Device:{row.device_id}"
        card_node= f"Card:{row.card_id}"
        product_node=f"Product:{row.product_id}"
        cashier_node=f"Cashier:{row.cashier_id}"

        edge_rows.append(

                {   
                    "source_node_id": customer_node,
                    "target_node_id": transaction_node,
                    "relationship_type": "PLACED",
                    "transaction_id": row.transaction_id,
                    "event_time": row.event_time,
                }

            )

        edge_rows.append(
            {
                "source_node_id": transaction_node,
                "target_node_id": device_node,
                "relationship_type": "USED_DEVICE",
                "transaction_id": row.transaction_id,
                "event_time": row.event_time,
            }
        )
        edge_rows.append(
            {
                "source_node_id": transaction_node,
                "target_node_id": card_node,
                "relationship_type": "PAID_WITH",
                "transaction_id": row.transaction_id,
                "event_time": row.event_time,
            }
        )

        edge_rows.append(
            {
                "source_node_id": transaction_node,
                "target_node_id": product_node,
                "relationship_type": "INVOLVES_PRODUCT",
                "transaction_id": row.transaction_id,
                "event_time": row.event_time,
            }
        )

        edge_rows.append(
            {
                "source_node_id": transaction_node,
                "target_node_id": cashier_node,
                "relationship_type": "PROCESSED_BY",
                "transaction_id": row.transaction_id,
                "event_time": row.event_time,
            }
        )
    return pd.DataFrame(edge_rows)

def main() -> None:
    transactions = load_transactions()
    featured = add_graph_features(transactions)
    scored = score_anomalies(featured)
    graph_nodes = build_graph_nodes(scored)
    graph_edges = build_graph_edges(scored)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    scored.to_csv(
        ANOMALY_OUTPUT_FILE,
        index=False,
    )
    graph_nodes.to_csv(
    GRAPH_NODES_OUTPUT_FILE,
    index=False,
    )
    graph_edges.to_csv(
    GRAPH_EDGES_OUTPUT_FILE,
    index=False,
)

    print("Anomaly scoring completed.")
    print(f"Output written to: {ANOMALY_OUTPUT_FILE.resolve()}")

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
    print(f"Graph edges written to: {GRAPH_EDGES_OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()