from pathlib import Path
import pandas as pd

DATA_FILE = Path("data/transactions.csv")

def main()-> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Data file not found: {DATA_FILE.resolve()}")
    transactions_df = pd.read_csv(DATA_FILE)
    print("Transaction data")
    print(transactions_df)

    print("\nNumber of transactions:")
    print(len( transactions_df))


if __name__ == "__main__":
    main()