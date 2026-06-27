from pathlib import Path
import networkx as nx
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
                    "node_type":node_type,
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

def validate_graph_output(
    graph_nodes: pd.DataFrame,
    graph_edges: pd.DataFrame,
) -> None:
    node_ids = set(graph_nodes["node_id"])

    missing_source_nodes = sorted(
        set(graph_edges["source_node_id"]) - node_ids
    )

    missing_target_nodes = sorted(
        set(graph_edges["target_node_id"]) - node_ids
    )

    if missing_source_nodes:
        raise ValueError(
            "Some edge source nodes do not exist in graph_nodes.csv: "
            + ", ".join(missing_source_nodes)
        )

    if missing_target_nodes:
        raise ValueError(
            "Some edge target nodes do not exist in graph_nodes.csv: "
            + ", ".join(missing_target_nodes)
        )

    allowed_relationship_types = {
        "PLACED",
        "USED_DEVICE",
        "PAID_WITH",
        "INVOLVES_PRODUCT",
        "PROCESSED_BY",
    }

    invalid_relationship_types = sorted(
        set(graph_edges["relationship_type"]) - allowed_relationship_types
    )

    if invalid_relationship_types:
        raise ValueError(
            "Invalid relationship types found: "
            + ", ".join(invalid_relationship_types)
        )

    print("Graph validation passed.")
    print(f"Node count: {len(graph_nodes)}")
    print(f"Edge count: {len(graph_edges)}")

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
    graph_nodes = build_graph_nodes(scored)
    graph_edges = build_graph_edges(scored)

    validate_graph_output(graph_nodes, graph_edges)
    print("Graph node columns:", graph_nodes.columns.tolist())
    print("Graph edge columns:", graph_edges.columns.tolist())
    graph = build_networkx_graph(graph_nodes, graph_edges)
    print_networkx_summary(graph)

    inspect_suspicious_node(graph, "Device:D99")
    inspect_suspicious_node(graph, "Card:K99")
    inspect_suspicious_node(graph, "Cashier:E09")

    suspicious_subgraph = extract_suspicious_subgraph(
    graph,
    ["Device:D99", "Card:K99", "Cashier:E09"],
    )

    print_subgraph_summary(suspicious_subgraph)

def build_networkx_graph(
    graph_nodes: pd.DataFrame,
    graph_edges: pd.DataFrame,
) -> nx.DiGraph:
    graph = nx.DiGraph()

    for row in graph_nodes.to_dict("records"):
        graph.add_node(
            row["node_id"],
            node_type=row["node_type"],
            business_id=row["business_id"],
        )

    for row in graph_edges.to_dict("records"):
        graph.add_edge(
            row["source_node_id"],
            row["target_node_id"],
            relationship_type=row["relationship_type"],
            transaction_id=row["transaction_id"],
            event_time=row["event_time"],
        )

    return graph
def inspect_suspicious_node(graph: nx.DiGraph, node_id: str) -> None:
    if node_id not in graph:
        print(f"{node_id} was not found in the graph.")
        return

    print()
    print(f"Inspecting node: {node_id}")

    incoming_nodes = list(graph.predecessors(node_id))
    outgoing_nodes = list(graph.successors(node_id))

    print(f"Incoming connections: {len(incoming_nodes)}")
    for source_node in incoming_nodes:
        edge_data = graph.get_edge_data(source_node, node_id)
        print(
            f"  {source_node} -> {node_id} "
            f"({edge_data['relationship_type']})"
        )

    print(f"Outgoing connections: {len(outgoing_nodes)}")
    for target_node in outgoing_nodes:
        edge_data = graph.get_edge_data(node_id, target_node)
        print(
            f"  {node_id} -> {target_node} "
            f"({edge_data['relationship_type']})"
        )

def print_networkx_summary(graph: nx.DiGraph) -> None:
    print("NetworkX graph built.")
    print(f"NetworkX node count: {graph.number_of_nodes()}")
    print(f"NetworkX edge count: {graph.number_of_edges()}")

def extract_suspicious_subgraph(
    graph: nx.DiGraph,
    center_nodes: list[str],
) -> nx.DiGraph:
    subgraph_node_ids = set(center_nodes)

    for center_node in center_nodes:
        if center_node not in graph:
            continue

        subgraph_node_ids.update(graph.predecessors(center_node))
        subgraph_node_ids.update(graph.successors(center_node))

    return graph.subgraph(subgraph_node_ids).copy()

def print_subgraph_summary(subgraph: nx.DiGraph) -> None:
    print()
    print("Suspicious subgraph extracted.")
    print(f"Subgraph node count: {subgraph.number_of_nodes()}")
    print(f"Subgraph edge count: {subgraph.number_of_edges()}")

    print("Subgraph nodes:")
    for node_id, node_data in subgraph.nodes(data=True):
        print(f"  {node_id} ({node_data['node_type']})")

    print("Subgraph edges:")
    for source_node, target_node, edge_data in subgraph.edges(data=True):
        print(
            f"  {source_node} -> {target_node} "
            f"({edge_data['relationship_type']})"
        )

if __name__ == "__main__":
    main()