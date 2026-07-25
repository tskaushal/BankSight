import pandas as pd


def explain_customer(customer_id, segmented_df, thresholds):
    row = segmented_df[segmented_df['CustomerID'] == customer_id]

    if row.empty:
        return None

    row = row.iloc[0]
    segment = row['Segment']
    balance = row['Balance']
    volume = row['TotalVolume']

    bal_hi = thresholds['priority_balance_threshold']

    vol_hi = thresholds['priority_volume_threshold']
    bal_lo = thresholds['regular_balance_threshold']
    
    vol_lo = thresholds['regular_volume_threshold']

    
    reasons = []

    if segment == 'priority':
        reasons.append(f"Balance of {balance:,.0f} is above the priority threshold ({bal_hi:,.0f})")
        reasons.append(f"Total spend of {volume:,.0f} is above the priority threshold ({vol_hi:,.0f})")
        explanation = (f"Customer {customer_id} is PRIORITY because they meet BOTH conditions: "
                        + " and ".join(reasons) + ".")

    elif segment == 'regular':
        met_balance = balance >= bal_lo
        met_volume = volume >= vol_lo
        if met_balance:
            reasons.append(f"Balance of {balance:,.0f} is above the regular threshold ({bal_lo:,.0f})")
        if met_volume:
            reasons.append(f"Total spend of {volume:,.0f} is above the regular threshold ({vol_lo:,.0f})")

        missing = []
        if balance < bal_hi:
            missing.append(f"balance is below the priority threshold ({bal_hi:,.0f})")
        if volume < vol_hi:
            missing.append(f"total spend is below the priority threshold ({vol_hi:,.0f})")

        explanation = (f"Customer {customer_id} is REGULAR: " + " and ".join(reasons) +
                        f". Not priority because " + " and ".join(missing) + ".")

    else:
        explanation = (f"Customer {customer_id} is DORMANT: balance ({balance:,.0f}) and total spend "
                        f"({volume:,.0f}) are both below the regular thresholds "
                        f"(balance {bal_lo:,.0f}, volume {vol_lo:,.0f}).")

    return {
        'customer_id': customer_id,
        'segment': segment,
        'balance': balance,
        'total_volume': volume,
        'explanation': explanation
    }


if __name__ == "__main__":
    from pipeline import run_pipeline

    segmented, thresholds, _ = run_pipeline()
    test_id = segmented.iloc[0]['CustomerID']
    result = explain_customer(test_id, segmented, thresholds)
    print(result['explanation'])

    fake_result = explain_customer('C9999999999', segmented, thresholds)
    print("\nfake id result:", fake_result)