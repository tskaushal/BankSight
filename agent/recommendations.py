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
    """
    Finds 'regular' customers closest to crossing into 'priority'.
    Ranks by RELATIVE remaining gap (gap / threshold) so a customer
    needing a small proportional push ranks above one with a huge
    absolute balance but tiny absolute volume gap.
    """
    bal_hi = thresholds['priority_balance_threshold']
    vol_hi = thresholds['priority_volume_threshold']

    regular = segmented_df[segmented_df['Segment'] == 'regular'].copy()

    regular['balance_gap'] = bal_hi - regular['Balance']
    regular['volume_gap'] = vol_hi - regular['TotalVolume']

    regular['rel_balance_need'] = regular['balance_gap'].clip(lower=0) / bal_hi
    regular['rel_volume_need'] = regular['volume_gap'].clip(lower=0) / vol_hi
    regular['total_relative_need'] = regular['rel_balance_need'] + regular['rel_volume_need']

    candidates = regular[regular['total_relative_need'] > 0].copy()
    candidates = candidates.sort_values('total_relative_need').head(top_n)

    def suggest_action(row):
        needs_balance = row['balance_gap'] > 0
        needs_volume = row['volume_gap'] > 0

        if needs_balance and needs_volume:
            return (f"Needs ₹{row['balance_gap']:,.0f} more balance AND "
                    f"₹{row['volume_gap']:,.0f} more total spend. "
                    f"Suggest a combined savings incentive + spend-based reward.")
        elif needs_balance:
            return (f"Spend is already sufficient. Needs ₹{row['balance_gap']:,.0f} "
                    f"more balance. Suggest a targeted savings/deposit campaign.")
        else:
            return (f"Balance is already sufficient. Needs ₹{row['volume_gap']:,.0f} "
                    f"more total spend. Suggest a spend-based cashback incentive.")

    candidates['suggested_action'] = candidates.apply(suggest_action, axis=1)
    candidates['Balance'] = candidates['Balance'].round(0)
    candidates['TotalVolume'] = candidates['TotalVolume'].round(0)
    candidates['balance_gap'] = candidates['balance_gap'].round(0)
    candidates['volume_gap'] = candidates['volume_gap'].round(0)

    return candidates[['CustomerID', 'Balance', 'TotalVolume',
                        'balance_gap', 'volume_gap', 'suggested_action']]


def find_retention_risks(segmented_df, thresholds, top_n=10):
    """
    Identifies 'regular' customers closest to falling into 'dormant' -
    mirrors find_transition_candidates but looking downward.
    """
    bal_lo = thresholds['regular_balance_threshold']
    vol_lo = thresholds['regular_volume_threshold']

    regular = segmented_df[segmented_df['Segment'] == 'regular'].copy()

    regular['balance_cushion'] = regular['Balance'] - bal_lo
    regular['volume_cushion'] = regular['TotalVolume'] - vol_lo

    regular['rel_balance_cushion'] = regular['balance_cushion'] / bal_lo
    regular['rel_volume_cushion'] = regular['volume_cushion'] / vol_lo
    regular['risk_score'] = regular[['rel_balance_cushion', 'rel_volume_cushion']].min(axis=1)

    at_risk = regular.sort_values('risk_score').head(top_n).copy()

    def suggest_retention_action(row):
        return (f"Only ₹{row['balance_cushion']:,.0f} balance and ₹{row['volume_cushion']:,.0f} "
                f"spend above the dormant threshold. Suggest proactive retention outreach "
                f"(e.g. fee waiver, personalized offer) before they disengage further.")

    at_risk['retention_action'] = at_risk.apply(suggest_retention_action, axis=1)
    at_risk['Balance'] = at_risk['Balance'].round(0)
    at_risk['TotalVolume'] = at_risk['TotalVolume'].round(0)
    at_risk['balance_cushion'] = at_risk['balance_cushion'].round(0)
    at_risk['volume_cushion'] = at_risk['volume_cushion'].round(0)

    return at_risk[['CustomerID', 'Balance', 'TotalVolume', 'balance_cushion',
                     'volume_cushion', 'retention_action']]


if __name__ == "__main__":
    from pipeline import run_pipeline

    segmented, thresholds, _ = run_pipeline()

    print("Recommendations by segment:")
    for seg in ['priority', 'regular', 'dormant']:
        print(f"\n{seg}:")
        for r in recommend_for_segment(seg):
            print(f"  - {r}")

    print("\nTop transition candidates (regular -> priority):")
    print(find_transition_candidates(segmented, thresholds).to_string())

    print("\nTop retention risks (regular -> dormant):")
    print(find_retention_risks(segmented, thresholds).to_string())