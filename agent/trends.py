import pandas as pd


def segment_by_location(segmented_df, top_n=10):
    """which city have the most priority customers and segment """
    counts = segmented_df.groupby(['Location', 'Segment']).size().unstack(fill_value=0)

    if 'priority' in counts.columns:
        counts = counts.sort_values('priority', ascending=False)

    return counts.head(top_n)


def segment_by_gender(segmented_df):
    return segmented_df.groupby(['Gender', 'Segment']).size().unstack(fill_value=0)


def segment_by_age_group(segmented_df):
    df = segmented_df.copy()
    df['AgeGroup'] = pd.cut(df['Age'], bins=[0, 25, 35, 45, 55, 65, 100],
                              labels=['18-25', '26-35', '36-45', '46-55', '56-65', '65+'])
    return df.groupby(['AgeGroup', 'Segment'], observed=True).size().unstack(fill_value=0)


def top_cities_by_balance(segmented_df, top_n=10, min_customers=50):
    """
    Average balance and customer count per city
    
    """
    city_stats = segmented_df.groupby('Location').agg(
        avg_balance=('Balance', 'mean'),
        avg_volume=('TotalVolume', 'mean'),
        customer_count=('CustomerID', 'count')
    )
    city_stats = city_stats[city_stats['customer_count'] >= min_customers]
    return city_stats.sort_values('avg_balance', ascending=False).head(top_n)


def correlation_summary(segmented_df):
    """ correlation between key  features """
    numeric_cols = ['Balance', 'TotalVolume', 'AvgAmount', 'TransactionCount', 'Age']
    available = [c for c in numeric_cols if c in segmented_df.columns]
    return segmented_df[available].corr()


def missing_value_summary(raw_or_cleaned_df):
    """Nulls per column """
    nulls = raw_or_cleaned_df.isnull().sum()
    pct = (nulls / len(raw_or_cleaned_df) * 100).round(2)
    return pd.DataFrame({'missing_count': nulls, 'missing_pct': pct})[nulls > 0]


if __name__ == "__main__":
    from pipeline import run_pipeline

    segmented, thresholds, cleaned = run_pipeline()

    print("Segment mix by top cities (by priority count):")
    print(segment_by_location(segmented))

    print("\nSegment mix by gender:")
    print(segment_by_gender(segmented))

    print("\nSegment mix by age group:")
    print(segment_by_age_group(segmented))

    print("\nTop cities by average balance (min 50 customers):")
    print(top_cities_by_balance(segmented))

    print("\nCorrelation between key features:")
    print(correlation_summary(segmented))