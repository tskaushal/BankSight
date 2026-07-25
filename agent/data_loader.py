import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
DATA_FILE = DATA_DIR / 'bank_transactions.csv'

FULL_FILE = DATA_DIR / 'bank_transactions.csv'
SAMPLE_FILE = DATA_DIR / 'sample.csv'

if FULL_FILE.exists():
    df = pd.read_csv(FULL_FILE)
elif SAMPLE_FILE.exists():
    print("Full dataset not found, using bundled 1000-row sample instead.")
    df = pd.read_csv(SAMPLE_FILE)
else:
    raise FileNotFoundError("No data found. See README for setup instructions.")

def load_data():
    if not DATA_FILE.exists():
        print(f"File not found: {DATA_FILE}")
        print("Put bank_transactions.csv in the data/ folder")
        return None

    df = pd.read_csv(DATA_FILE)
    print(f"loaded {df.shape[0]} rows, {df.shape[1]} cols")

    print("\ncolumns:", list(df.columns))

    print("\ndtypes:")
    print(df.dtypes)

    print("\nnulls per column:")
    nulls = df.isnull().sum()
    
    print(nulls[nulls > 0])

    print("\n", df.describe())
    
    #  checker  if the colums we need are there or not 
    needed = ['CustomerID', 'CustAccountBalance', 'TransactionAmount (INR)',
               'TransactionDate', 'CustomerDOB', 'CustGender', 'CustLocation']
    missing = [c for c in needed if c not in df.columns]
    if missing:
        print(f"\n missing  columns: {missing}")
    else:
        print(f"\nall expected columnns present, {df['CustomerID'].nunique()} unique customers")

    return df


if __name__ == "__main__":
    df = load_data()

    # sample code saving
    if df is not None:
        df.head(1000).to_csv(DATA_DIR / 'sample.csv', index=False)
        print(f"\nsaved 1000-row sample to {DATA_DIR / 'sample.csv'}")