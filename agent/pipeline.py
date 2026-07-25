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
        return pd.read_csv(SAMPLE_FILE)
    else:
        raise FileNotFoundError("no data found - need bank_transactions.csv or sample.csv in data/ folderr")


def clean_all(df):
    df = df.copy()

    df['CustomerDOB'] = pd.to_datetime(df['CustomerDOB'], errors='coerce', dayfirst=True)
    df.loc[df['CustomerDOB'].dt.year == 1800, 'CustomerDOB'] = pd.NaT
    df['Age'] = 2016 - df['CustomerDOB'].dt.year
    df.loc[(df['Age'] > 100) | (df['Age'] < 18), 'Age'] = np.nan

    df['TransactionDate'] = pd.to_datetime(df['TransactionDate'], format='%d/%m/%y', errors='coerce')

    gender_map = {'M': 'Male', 'F': 'Female', 'T': 'Other'}
    df['Gender'] = df['CustGender'].map(gender_map).fillna('Unknown')

    df['Location'] = df['CustLocation'].fillna('Unknown').str.strip().str.upper()

    df.rename(columns={
        'CustAccountBalance': 'Balance',
        'TransactionAmount (INR)': 'TransactionAmount'
    }, inplace=True)
    df['Balance'] = df['Balance'].clip(lower=0)
    df['TransactionAmount'] = df['TransactionAmount'].clip(lower=0)

    df.drop(columns=['CustomerDOB', 'CustGender', 'CustLocation'], inplace=True, errors='ignore')
    df.dropna(subset=['CustomerID', 'TransactionDate', 'TransactionAmount'], inplace=True)

    return df


def build_features(df):
    features = df.groupby('CustomerID').agg({
        'TransactionAmount': ['count', 'sum', 'mean', 'std', 'max', 'min'],
        'Balance': 'last',
        'Age': 'first',
        'Gender': 'first',
        'Location': 'first'
    }).reset_index()

    features.columns = ['CustomerID', 'TransactionCount', 'TotalVolume', 'AvgAmount',
                         'StdAmount', 'MaxAmount', 'MinAmount', 'Balance', 'Age',
                         'Gender', 'Location']
    features['StdAmount'] = features['StdAmount'].fillna(0)

    last_txn = df.groupby('CustomerID')['TransactionDate'].max().reset_index()
   
    last_txn.columns = ['CustomerID', 'LastTxnDate']
   
    features = features.merge(last_txn, on='CustomerID', how='left')
    features['DaysSinceLastTxn'] = (df['TransactionDate'].max() - features['LastTxnDate']).dt.days

    features.dropna(subset=['Balance', 'TransactionCount'], inplace=True)
    return features


def segment(features, priority_pct=0.75, regular_pct=0.25):
    balance_hi = features['Balance'].quantile(priority_pct)
    volume_hi = features['TotalVolume'].quantile(priority_pct)
    balance_lo = features['Balance'].quantile(regular_pct)
    volume_lo = features['TotalVolume'].quantile(regular_pct)

    def classify(row):
        if row['Balance'] >= balance_hi and row['TotalVolume'] >= volume_hi:
            return 'priority'
        elif row['Balance'] >= balance_lo or row['TotalVolume'] >= volume_lo:
            return 'regular'
        else:
            return 'dormant'

    features = features.copy()
    features['Segment'] = features.apply(classify, axis=1)

    thresholds = {
        'priority_balance_threshold': balance_hi,
        'priority_volume_threshold': volume_hi,
        'regular_balance_threshold': balance_lo,
        'regular_volume_threshold': volume_lo,
    }
    return features, thresholds


def run_pipeline():

    raw = load_raw()
    cleaned = clean_all(raw)
    features = build_features(cleaned)
    segmented, thresholds = segment(features)
    return segmented, thresholds, cleaned