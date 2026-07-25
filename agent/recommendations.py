import pandas as pd

RECOMMENDATIONS = {
    'priority': [
        'Wealth management consultation',
        'Premium credit card upgrade',
        'Investment / mutual fund products'
    ],
    'regular': [
        'Savings account upgrade with better interest rate',
        'Personal loan pre-approval',
        'Standard credit card offer'
    ],
    'dormant': [
        'Reactivation campaign (cashback on next transaction)',
        'No-fee account check-in',
        'Simple small-ticket loan offer to re-engage'
    ]
}


def recommend_for_segment(segment_name):
    return RECOMMENDATIONS.get(segment_name, ['No recommendation available'])


def find_transition_candidates(segmented_df, thresholds, top_n=10):
    regular = segmented_df[segmented_df['Segment'] == 'regular'].copy()

    regular['balance_gap'] = thresholds['priority_balance_threshold'] - regular['Balance']
    regular['freq_gap'] = thresholds['priority_freq_threshold'] - regular['TransactionCount']

    candidates = regular[(regular['balance_gap'] > 0) | (regular['freq_gap'] > 0)].copy()
    candidates = candidates.sort_values('balance_gap').head(top_n)

    def suggest_action(row):
        if row['balance_gap'] > 0 and row['freq_gap'] > 0:
            return (f"Needs +{row['balance_gap']:.0f} balance and "
                    f"+{row['freq_gap']:.0f} more transactions. "
                    f"Suggest a savings incentive + engagement nudge.")
        elif row['balance_gap'] > 0:
            return (f"Already transacts frequently enough. Needs +{row['balance_gap']:.0f} "
                    f"balance. Suggest targeted savings/deposit campaign.")
        else:
            return (f"Balance already sufficient. Needs +{row['freq_gap']:.0f} more "
                    f"transactions. Suggest cashback or engagement incentive.")

    candidates['suggested_action'] = candidates.apply(suggest_action, axis=1)

    return candidates[['CustomerID', 'Balance', 'TransactionCount',
                        'balance_gap', 'freq_gap', 'suggested_action']]


if __name__ == "__main__":
    from pipeline import run_pipeline

    segmented, thresholds, _ = run_pipeline()

    print("Recommendations by segment:")
    for seg in ['priority', 'regular', 'dormant']:
        print(f"\n{seg}:")
        for r in recommend_for_segment(seg):
            print(f"  - {r}")

    print("\nTop transition candidates (regular -> priority):")
    candidates = find_transition_candidates(segmented, thresholds)
    print(candidates.to_string())