import streamlit as st
import pandas as pd

from pipeline import run_pipeline
from recommendations import recommend_for_segment, find_transition_candidates, find_retention_risks
from explainability import explain_customer
from personas import generate_personas
from intent_parser import parse_intent, generate_answer
import trends

st.set_page_config(page_title="BankSight - Customer Segmentation Agent", layout="wide")
st.title("BankSight")

with st.sidebar:
    st.markdown("### About")
    st.caption("Customer Segmentation & Personalization Agent for Retail Banking")


@st.cache_data
def get_data():
    return run_pipeline()

segmented, thresholds, cleaned = get_data()

col1, col2, col3 = st.columns(3)
counts = segmented['Segment'].value_counts()
col1.metric("Priority", counts.get('priority', 0))
col2.metric("Regular", counts.get('regular', 0))
col3.metric("Dormant", counts.get('dormant', 0))

st.bar_chart(counts)

if "history" not in st.session_state:
    st.session_state.history = []


def find_edge_cases(segmented_df, thresholds, margin=0.03, top_n=10):
    bal_hi = thresholds['priority_balance_threshold']
    vol_hi = thresholds['priority_volume_threshold']
    bal_lo = thresholds['regular_balance_threshold']
    vol_lo = thresholds['regular_volume_threshold']

    df = segmented_df.copy()
    near_priority = (
        (df['Balance'].between(bal_hi * (1 - margin), bal_hi * (1 + margin))) |
        (df['TotalVolume'].between(vol_hi * (1 - margin), vol_hi * (1 + margin)))
    )
    near_regular = (
        (df['Balance'].between(bal_lo * (1 - margin), bal_lo * (1 + margin))) |
        (df['TotalVolume'].between(vol_lo * (1 - margin), vol_lo * (1 + margin)))
    )
    edge_cases = df[near_priority | near_regular]
    return edge_cases[['CustomerID', 'Balance', 'TotalVolume', 'Segment']].head(top_n), len(edge_cases)


def handle_query(query):
    parsed = parse_intent(query)

    if parsed.get("needs_clarification"):
        return parsed.get("clarification_question", "Could you clarify that?"), None

    intent = parsed.get("intent")
    seg_filter = parsed.get("segment_filter")
    customer_id = parsed.get("customer_id")
    dim = parsed.get("trend_dimension")
    q_lower = query.lower()

    if any(p in q_lower for p in ["at risk", "becoming dormant", "risk of dormant", "retention"]) and not customer_id:
        intent = "retention_risk"
    elif any(p in q_lower for p in ["edge case", "boundary", "boundaries", "borderline"]):
        intent = "edge_cases"

    if intent == "segment_overview":
        summary_data = {
            "total_customers": len(segmented),
            "priority_count": int(counts.get('priority', 0)),
            "regular_count": int(counts.get('regular', 0)),
            "dormant_count": int(counts.get('dormant', 0)),
        }
        table = segmented[['CustomerID', 'Balance', 'TotalVolume', 'Segment']].head(30)
        text = generate_answer(query, summary_data)
        return text, table

    elif intent == "criteria":
        text = generate_answer(query, thresholds)
        return text, None

    elif intent == "aggregate":
        avg_by_segment = segmented.groupby('Segment')[['Balance', 'TotalVolume', 'AvgAmount']].mean().round(0)
        text = generate_answer(query, avg_by_segment.to_dict())
        table = avg_by_segment.applymap(lambda x: f"₹{x:,.0f}")
        return text, table

    elif intent == "transition":
        table = find_transition_candidates(segmented, thresholds)
        text = generate_answer(query, table.to_dict(orient='records'))
        return text, table

    elif intent == "retention_risk":
        table = find_retention_risks(segmented, thresholds)
        text = generate_answer(query, table.to_dict(orient='records'))
        return text, table

    elif intent == "edge_cases":
        table, total_count = find_edge_cases(segmented, thresholds)
        text = generate_answer(query, {"total_edge_case_count": total_count,
                                        "sample": table.to_dict(orient='records')})
        return text, table

    elif intent == "explain_customer":
        if not customer_id:
            return "Which customer ID would you like me to look up?", None
        result = explain_customer(customer_id, segmented, thresholds)
        if result is None:
            return f"I couldn't find customer {customer_id} in the dataset. Can you double check the ID?", None
        text = generate_answer(query, result)
        return text, None

    elif intent == "recommend":
        seg = seg_filter or "priority"
        recs = recommend_for_segment(seg)
        text = generate_answer(query, {"segment": seg, "recommendations": recs})
        return text, None

    elif intent == "trend":
        if dim == "location":
            table = trends.segment_by_location(segmented)
            text = generate_answer(query, table.to_dict())
            return text, table
        elif dim == "gender":
            counts_g, pct_g = trends.segment_by_gender(segmented)
            text = generate_answer(query, counts_g.to_dict())
            return text, counts_g
        elif dim == "age":
            table = trends.segment_by_age_group(segmented)
            text = generate_answer(query, table.to_dict())
            return text, table
        elif dim == "correlation":
            table = trends.correlation_summary(segmented)
            text = generate_answer(query, table.to_dict())
            return text, table
        elif dim == "recency":
            table = trends.recency_by_segment(segmented)
            text = generate_answer(query, table.to_dict())
            return text, table
        else:
            table = trends.segment_size_summary(segmented)
            text = generate_answer(query, table.to_dict())
            return text, table

    elif intent == "persona":
        personas = generate_personas(segmented)
        if seg_filter and seg_filter in personas:
            return personas[seg_filter]['description'], None
        text = "\n\n".join(f"{s.upper()}: {p['description']}" for s, p in personas.items())
        return text, None

    else:
        return ("I'm not sure how to answer that. Try asking about segments, criteria, averages, "
                "recommendations, trends, retention risk, edge cases, or a specific customer ID."), None


query = st.chat_input("Ask about your customers...")

if query:
    st.session_state.history.append(("user", query, None))
    text, table = handle_query(query)
    st.session_state.history.append(("agent", text, table))

for entry in st.session_state.history:
    role, text, table = entry
    with st.chat_message(role):
        st.write(text)
        if table is not None:
            st.dataframe(table)