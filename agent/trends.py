import pandas as pd


def segment_by_location(segmented_df, top_n=10):
    counts = segmented_df.groupby(['Location', 'Segment']).size().unstack(fill_value=0)
    if 'priority' in counts.columns:
        counts = counts.sort_values('priority', ascending=False)
    return counts.head(top_n)


def segment_by_gender(segmented_df):
    counts = segmented_df.groupby(['Gender', 'Segment']).size().unstack(fill_value=0)
    pct = counts.div(counts.sum(axis=1), axis=0) * 100
    return counts, pct.round(1)


def segment_by_age_group(segmented_df):
    df = segmented_df.copy()
    df['AgeGroup'] = pd.cut(df['Age'], bins=[0, 25, 35, 45, 55, 65, 100],
                              labels=['18-25', '26-35', '36-45', '46-55', '56-65', '65+'])
    return df.groupby(['AgeGroup', 'Segment'], observed=True).size().unstack(fill_value=0)


def top_cities_by_balance(segmented_df, top_n=10, min_customers=50):
    city_stats = segmented_df.groupby('Location').agg(
        avg_balance=('Balance', 'mean'),
        avg_volume=('TotalVolume', 'mean'),
        customer_count=('CustomerID', 'count')
    )
    city_stats = city_stats[city_stats['customer_count'] >= min_customers]
    return city_stats.sort_values('avg_balance', ascending=False).head(top_n)


def correlation_summary(segmented_df):
    numeric_cols = ['Balance', 'TotalVolume', 'AvgAmount', 'TransactionCount', 'Age']
    available = [c for c in numeric_cols if c in segmented_df.columns]
    return segmented_df[available].corr()


def missing_value_summary(raw_or_cleaned_df):
    nulls = raw_or_cleaned_df.isnull().sum()
    pct = (nulls / len(raw_or_cleaned_df) * 100).round(2)
    return pd.DataFrame({'missing_count': nulls, 'missing_pct': pct})[nulls > 0]


def recency_by_segment(segmented_df):
    """days since last transaction per segment"""
    return segmented_df.groupby('Segment')['DaysSinceLastTxn'].agg(
        ['mean', 'median', 'min', 'max']
    ).round(1)


def median_vs_mean_by_segment(segmented_df):
    """median shows the typical customers """
    return segmented_df.groupby('Segment').agg(
        mean_balance=('Balance', 'mean'),
        median_balance=('Balance', 'median'),
        mean_volume=('TotalVolume', 'mean'),
        median_volume=('TotalVolume', 'median'),
    ).round(0)


def segment_size_summary(segmented_df):
    """Segment size distribution - doubles as a basic model evaluation
    sanity check (are segments reasonably balanced)."""
    counts = segmented_df['Segment'].value_counts()
    pct = (counts / len(segmented_df) * 100).round(1)
    return pd.DataFrame({'count': counts, 'pct': pct})


def transaction_amount_distribution(segmented_df):
    """Spread of average transaction size per segment."""
    return segmented_df.groupby('Segment')['AvgAmount'].agg(
        ['mean', 'median', 'std', 'min', 'max']
    ).round(1)


def gender_balance_gap(segmented_df):
    """Average balance by gender within each segment."""
    return segmented_df.groupby(['Segment', 'Gender'])['Balance'].mean().unstack(fill_value=0).round(0)


if __name__ == "__main__":
    from pipeline import run_pipeline

    segmented, thresholds, cleaned = run_pipeline()

    print(" Segment size summary ")
    print(segment_size_summary(segmented))

    print("\n Segment mix by top cities (by priority count) ")
    print(segment_by_location(segmented))

    print("\n Segment mix by gender (counts) ")
    counts, pct = segment_by_gender(segmented)
    print(counts)
    print("\n Segment mix by gender (% within gender) ")
    print(pct)

    print("\n Segment mix by age group ")
    print(segment_by_age_group(segmented))

    print("\n Top cities by average balance (min 50 customers) ")
    print(top_cities_by_balance(segmented))

    print("\n Correlation between key features ")
    print(correlation_summary(segmented))

    print("\n Recency (days since last transaction) by segment ")
    print(recency_by_segment(segmented))

    print("\n Mean vs median balance/volume by segment ")
    print(median_vs_mean_by_segment(segmented))

    print("\n Transaction amount distribution by segment ")
    print(transaction_amount_distribution(segmented))

    print("\n Average balance by gender within each segment ")
    print(gender_balance_gap(segmented))