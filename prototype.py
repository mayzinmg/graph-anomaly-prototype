from pathlib import Path
import pandas as pd

<<<<<<< HEAD
DATA_FILE = Path("data/transactions.csv")

def main()-> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Data file not found: {DATA_FILE.resolve()}")
    transactions_df = pd.read_csv(DATA_FILE)
    print("Transaction data")
    print(transactions_df)

    print("\nNumber of transactions:")
    print(len( transactions_df))

=======
DATA_FILE= Path("data/transactions.csv")
REQUIRED_COLUMNS= {
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

def main()-> None:
    if not DATA_FILE.exists():
        raise FileExistsError(f"Cannot find the dataset:")
    
    transactions= pd.read_csv(DATA_FILE)
    missing_columns= REQUIRED_COLUMNS.difference(transactions.columns)
    if missing_columns:
        raise ValueError(
            "Missing required columns: "+",".join(sorted(missing_columns))
    )
    transactions["event_time"]=pd.to_datetime(
        transactions["event_time"],errors="raise"
    )
    transactions["amount"]=pd.to_numeric(
        transactions["amount"],errors="raise"
    )
    print("Dataset validation passed.")
    print(f"Transactions: {len(transactions)}")
    print("\nColumn data types:")
    print(transactions.dtypes)
>>>>>>> 81e7ccfcc23a6422fd5daa9460bdd201c14b9cb7

if __name__ == "__main__":
    main()