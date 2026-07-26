import streamlit as st
import pandas as pd

from pipeline import run_pipeline
from recommendations import recommend_for_segment, find_transition_candidates
from explainability import explain_customer
from personas import generate_personas
from intent_parser import parse_intent
import trends

st.set_page_config(page_title="BankSight - Customer Segmentation Agent", layout="wide")
st.title("BankSight")
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


def handle_query(query):
    parsed = parse_intent(query)

    if parsed.get("needs_clarification"):
        return parsed.get("clarification_question", "Could you clarify that?")

    intent = parsed.get("intent")
    seg_filter = parsed.get("segment_filter")
    customer_id = parsed.get("customer_id")
    dim = parsed.get("trend_dimension")

    if intent == "segment_overview":
        return segmented[['CustomerID', 'Balance', 'TotalVolume', 'Segment']].head(30)

    elif intent == "criteria":
        return (
            f"Priority requires balance >= {thresholds['priority_balance_threshold']:,.0f} "
            f"AND total spend >= {thresholds['priority_volume_threshold']:,.0f}. "
            f"Regular requires balance >= {thresholds['regular_balance_threshold']:,.0f} "
            f"OR total spend >= {thresholds['regular_volume_threshold']:,.0f}."
        )

    elif intent == "aggregate":
        avg_by_segment = segmented.groupby('Segment')[['Balance', 'TotalVolume', 'AvgAmount']].mean().round(1)
        return avg_by_segment

    elif intent == "transition":
        return find_transition_candidates(segmented, thresholds)

    elif intent == "explain_customer":
        if not customer_id:
            return "Which customer ID would you like me to look up?"
        result = explain_customer(customer_id, segmented, thresholds)
        if result is None:
            return f"I couldn't find customer {customer_id} in the dataset. Can you double check the ID?"
        return result['explanation']

    elif intent == "recommend":
        seg = seg_filter or "priority"
        recs = recommend_for_segment(seg)
        return f"Recommended for {seg} customers:\n" + "\n".join(f"- {r}" for r in recs)

    elif intent == "trend":
        if dim == "location":
            return trends.segment_by_location(segmented)
        elif dim == "gender":
            counts_g, pct_g = trends.segment_by_gender(segmented)
            return counts_g
        elif dim == "age":
            return trends.segment_by_age_group(segmented)
        elif dim == "correlation":
            return trends.correlation_summary(segmented)
        elif dim == "recency":
            return trends.recency_by_segment(segmented)
        else:
            return trends.segment_size_summary(segmented)

    elif intent == "persona":
        personas = generate_personas(segmented)
        if seg_filter and seg_filter in personas:
            return personas[seg_filter]['description']
        return "\n\n".join(f"{s.upper()}: {p['description']}" for s, p in personas.items())

    else:
        return "I'm not sure how to answer that. Try asking about segments, criteria, averages, recommendations, trends, or a specific customer ID."


query = st.chat_input("Ask about your customers...")

if query:
    st.session_state.history.append(("user", query))
    response = handle_query(query)
    st.session_state.history.append(("agent", response))

for role, content in st.session_state.history:
    with st.chat_message(role):
        if isinstance(content, pd.DataFrame):
            st.dataframe(content)
        else:
            st.write(content)