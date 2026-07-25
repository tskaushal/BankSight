import pandas as pd


def generate_personas(segmented_df):
    """
    Turns each segment's statistics into a human-readable persona description.
    """
    personas = {}

    total_customers = len(segmented_df)

    for seg in ['priority', 'regular', 'dormant']:
        seg_df = segmented_df[segmented_df['Segment'] == seg]

        if seg_df.empty:
            continue

        pct_of_base = len(seg_df) / total_customers * 100
        avg_balance = seg_df['Balance'].mean()
        avg_volume = seg_df['TotalVolume'].mean()
        avg_age = seg_df['Age'].mean()
        top_gender = seg_df['Gender'].mode()[0] if not seg_df['Gender'].mode().empty else 'Unknown'
        top_city = seg_df['Location'].mode()[0] if 'Location' in seg_df.columns and not seg_df['Location'].mode().empty else 'Unknown'

        if seg == 'priority':
            description = (
                f"High-value, highly engaged customers. Average balance of {avg_balance:,.0f} "
                f"and average total spend of {avg_volume:,.0f} - both well above the customer "
                f"base average. Typically around {avg_age:.0f} years old, most commonly based "
                f"in {top_city}. These customers represent the bank's most valuable relationships "
                f"and should be prioritized for premium services and retention efforts."
            )
        elif seg == 'regular':
            description = (
                f"Moderately active customers with average balance of {avg_balance:,.0f} and "
                f"average spend of {avg_volume:,.0f}. Typically around {avg_age:.0f} years old, "
                f"most commonly based in {top_city}. This is the largest and most diverse "
                f"segment - a mix of customers who are stable but not yet highly engaged, "
                f"and some who may be close to reaching priority status."
            )
        else:
            description = (
                f"Low-activity customers with average balance of {avg_balance:,.0f} and "
                f"average spend of only {avg_volume:,.0f}. Typically around {avg_age:.0f} years "
                f"old, most commonly based in {top_city}. These customers show minimal "
                f"engagement and are at risk of disengaging fully - re-activation campaigns "
                f"are recommended."
            )

        personas[seg] = {
            'segment': seg,
            'pct_of_customer_base': round(pct_of_base, 1),
            'avg_balance': avg_balance,
            'avg_volume': avg_volume,
            'avg_age': avg_age,
            'top_gender': top_gender,
            'top_city': top_city,
            'description': description
        }

    return personas


if __name__ == "__main__":
    from pipeline import run_pipeline

    segmented, thresholds, _ = run_pipeline()
    personas = generate_personas(segmented)

    for seg, info in personas.items():
        print(f"\n=== {seg.upper()} ({info['pct_of_customer_base']}% of customers) ===")
        print(info['description'])