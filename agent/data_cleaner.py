import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
FULL_FILE = DATA_DIR / 'bank_transactions.csv'
SAMPLE_FILE = DATA_DIR / 'sample.csv'


def load_raw():
    if FULL_FILE.exists():
        return pd.read_csv(FULL_FILE)
    elif SAMPLE_FILE.exists():
        print("using sample, full file not found")
        return pd.read_csv(SAMPLE_FILE)
    else:
        raise FileNotFoundError("no data, check readme")


def clean_dates(df):
    df['CustomerDOB'] = pd.to_datetime(df['CustomerDOB'], errors='coerce', dayfirst=True)

    # 1800 s are not real date fo birhts obv
    bad_dob = df['CustomerDOB'].dt.year == 1800
    print(f"{bad_dob.sum()} rows with fake 1800 dob")
    df.loc[bad_dob, 'CustomerDOB'] = pd.NaT

    df['Age'] = 2016 - df['CustomerDOB'].dt.year  
    df.loc[df['Age'] > 100, 'Age'] = np.nan
    df.loc[df['Age'] < 18, 'Age'] = np.nan  # no bank acount for people under 18

    df['TransactionDate'] = pd.to_datetime(df['TransactionDate'], format='%d/%m/%y', errors='coerce')

    return df


def clean_gender(df):
    gender_map = {'M': 'Male', 'F': 'Female', 'T': 'Other'}
    df['Gender'] = df['CustGender'].map(gender_map)
    df['Gender'] = df['Gender'].fillna('Unknown')
    return df


def clean_money(df):
    df.rename(columns={
        'CustAccountBalance': 'Balance',
        'TransactionAmount (INR)': 'TransactionAmount'
    }, inplace=True)

    df['Balance'] = df['Balance'].clip(lower=0)
    df['TransactionAmount'] = df['TransactionAmount'].clip(lower=0)

    zero_txns = (df['TransactionAmount'] == 0).sum()
    print(f"{zero_txns} transactions are 0 amount, leaving them in for now")

    return df


def clean_all(df):
    df = df.copy()
    print("shape before:", df.shape)

    df = clean_dates(df)
    df = clean_gender(df)
    df = clean_money(df)

    df.drop(columns=['CustomerDOB', 'CustGender'], inplace=True, errors='ignore')

    n = len(df)
    df.dropna(subset=['CustomerID', 'TransactionDate', 'TransactionAmount'], inplace=True)
    print(f"dropped {n - len(df)} rows, missing customerid/date/amount")

    print("shape after:", df.shape)
    return df


def build_customer_features(df):
    features = df.groupby('CustomerID').agg({
        'TransactionAmount': ['count', 'sum', 'mean', 'std', 'max', 'min'],
        'Balance': 'last',
        'Age': 'first',
        'Gender': 'first'
    }).reset_index()

    features.columns = ['CustomerID', 'TransactionCount', 'TotalVolume', 'AvgAmount',
                         'StdAmount', 'MaxAmount', 'MinAmount', 'Balance', 'Age',
                         'Gender']

    features['StdAmount'] = features['StdAmount'].fillna(0)  

    last_txn = df.groupby('CustomerID')['TransactionDate'].max().reset_index()
    last_txn.columns = ['CustomerID', 'LastTxnDate']
    features = features.merge(last_txn, on='CustomerID', how='left')
    features['DaysSinceLastTxn'] = (df['TransactionDate'].max() - features['LastTxnDate']).dt.days

    features.dropna(subset=['Balance', 'TransactionCount'], inplace=True)

    print(f"{features.shape[0]} customers after feature building")
    return features


if __name__ == "__main__":
    raw = load_raw()
    clean = clean_all(raw)
    features = build_customer_features(clean)

    clean.to_csv(DATA_DIR / 'transactions_cleaned.csv', index=False)
    features.to_csv(DATA_DIR / 'customer_features.csv', index=False)

    print("saved both files to data/")