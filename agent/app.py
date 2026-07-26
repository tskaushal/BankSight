import streamlit as st
import pandas as pd
import time
import random

from pipeline import run_pipeline
from recommendations import recommend_for_segment, find_transition_candidates, find_retention_risks
from explainability import explain_customer
from personas import generate_personas
from intent_parser import parse_intent, generate_answer
import trends

st.set_page_config(page_title="BankSight - Customer Segmentation Agent", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

h1, h2, h3 { font-family: 'Sora', sans-serif !important; }
p, div, span, label { font-family: 'Inter', sans-serif; }
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; }
[data-testid="stMetricLabel"] { font-family: 'Inter', sans-serif !important; }
[data-testid="stChatMessage"] { border-radius: 10px !important; }
[data-testid="stDataFrame"] { font-family: 'JetBrains Mono', monospace !important; }
</style>
""", unsafe_allow_html=True)

header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.title("BankSight")
    st.caption("AI-Powered Customer Segmentation & Personalization for Retail Banking")
with header_col2:
    st.markdown("&nbsp;")
    st.success("Live · Dataset Loaded", icon="🟢")


@st.cache_data
def get_data():
    return run_pipeline()

segmented, thresholds, cleaned = get_data()
counts = segmented['Segment'].value_counts()
total = len(segmented)


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


def evaluate_segmentation(segmented_df):
    sizes = segmented_df['Segment'].value_counts()
    size_pct = (sizes / len(segmented_df) * 100).round(1)
    stats = segmented_df.groupby('Segment')[['Balance', 'TotalVolume']].agg(['mean', 'median']).round(0)

    priority_min_balance = segmented_df[segmented_df['Segment'] == 'priority']['Balance'].min()
    regular_median_balance = segmented_df[segmented_df['Segment'] == 'regular']['Balance'].median()
    regular_max_balance = segmented_df[segmented_df['Segment'] == 'regular']['Balance'].max()

    return {
        "segment_sizes": sizes.to_dict(),
        "segment_size_pct": size_pct.to_dict(),
        "mean_median_by_segment": stats.to_dict(),
        "priority_min_balance": float(priority_min_balance),
        "regular_median_balance": float(regular_median_balance),
        "regular_max_balance": float(regular_max_balance),
        "note": ("Priority requires clearing BOTH balance and volume thresholds (AND logic), "
                 "while regular only needs ONE (OR logic). Some regular customers can have a "
                 "higher balance than the priority minimum (wealthy but low-activity customers) "
                 "- intentional, since priority reflects engagement as well as wealth.")
    }


col1, col2, col3 = st.columns(3)
col1.metric("Priority", f"{counts.get('priority',0):,}", f"{counts.get('priority',0)/total*100:.1f}% of base")
col2.metric("Regular", f"{counts.get('regular',0):,}", f"{counts.get('regular',0)/total*100:.1f}% of base")
col3.metric("Dormant", f"{counts.get('dormant',0):,}", f"{counts.get('dormant',0)/total*100:.1f}% of base")

kcol1, kcol2, kcol3, kcol4 = st.columns(4)
kcol1.metric("Total Customers", f"{total:,}")
kcol2.metric("Avg Balance", f"₹{segmented['Balance'].mean():,.0f}")
kcol3.metric("Avg Transaction", f"₹{segmented['AvgAmount'].mean():,.0f}")
kcol4.metric("Avg Age", f"{segmented['Age'].mean():.0f} yrs")

left, right = st.columns([2, 1])
with left:
    st.subheader("Segment Sizes")
    st.bar_chart(counts)
with right:
    st.subheader("Insights")
    top_city = segmented.groupby('Location').size().idxmax()
    richest_segment_gap = (segmented[segmented['Segment']=='priority']['Balance'].mean() /
                            segmented[segmented['Segment']=='regular']['Balance'].mean())
    _, edge_case_count = find_edge_cases(segmented, thresholds)
    st.markdown(f"""
- Most customers are based in **{top_city}**
- Priority customers hold **{richest_segment_gap:.1f}x** the average balance of regular customers
- **{edge_case_count:,}** customers sit near a segment boundary
- Dormant customers average just **₹{segmented[segmented['Segment']=='dormant']['Balance'].mean():,.0f}** balance
    """)

st.divider()
st.subheader("Ask BankSight")
st.caption('Try: "Show priority customers in Mumbai" · "Why is customer C1010011 priority?" · "Which regular customers might become dormant?"')

if "history" not in st.session_state:
    st.session_state.history = []


def handle_query(query):
    parsed = parse_intent(query)

    intent = parsed.get("intent")
    seg_filter = parsed.get("segment_filter")
    customer_id = parsed.get("customer_id")
    dim = parsed.get("trend_dimension")
    q_lower = query.lower()

    if any(p in q_lower for p in ["at risk", "becoming dormant", "risk of dormant", "retention"]) and not customer_id:
        intent = "retention_risk"
        parsed["needs_clarification"] = False
    elif any(p in q_lower for p in ["edge case", "boundary", "boundaries", "borderline"]):
        intent = "edge_cases"
        parsed["needs_clarification"] = False
    elif any(p in q_lower for p in ["recent", "recency", "last transaction"]) and not customer_id:
        intent = "trend"
        dim = "recency"
        parsed["needs_clarification"] = False
    elif any(p in q_lower for p in ["how good", "how accurate", "evaluate", "evaluation",
                                      "how reliable", "how confident", "validate"]):
        intent = "model_eval"
        parsed["needs_clarification"] = False

    if parsed.get("needs_clarification"):
        return parsed.get("clarification_question", "Could you clarify that?"), None, None

    if intent == "segment_overview":
        summary_data = {
            "total_customers": total,
            "priority_count": int(counts.get('priority', 0)),
            "regular_count": int(counts.get('regular', 0)),
            "dormant_count": int(counts.get('dormant', 0)),
        }
        table = segmented[['CustomerID', 'Balance', 'TotalVolume', 'Segment']].head(30)
        text = generate_answer(query, summary_data)
        return text, table, counts

    elif intent == "criteria":
        text = generate_answer(query, thresholds)
        return text, None, None

    elif intent == "aggregate":
        avg_by_segment = segmented.groupby('Segment')[['Balance', 'TotalVolume', 'AvgAmount']].mean().round(0)
        text = generate_answer(query, avg_by_segment.to_dict())
        chart = avg_by_segment['AvgAmount']
        table = avg_by_segment.applymap(lambda x: f"₹{x:,.0f}")
        return text, table, chart

    elif intent == "transition":
        table = find_transition_candidates(segmented, thresholds)
        text = generate_answer(query, table.to_dict(orient='records'))
        return text, table, None

    elif intent == "retention_risk":
        table = find_retention_risks(segmented, thresholds)
        text = generate_answer(query, table.to_dict(orient='records'))
        return text, table, None

    elif intent == "edge_cases":
        table, total_count = find_edge_cases(segmented, thresholds)
        text = generate_answer(query, {"total_edge_case_count": total_count,
                                        "sample": table.to_dict(orient='records')})
        return text, table, None

    elif intent == "model_eval":
        eval_data = evaluate_segmentation(segmented)
        text = generate_answer(query, eval_data)
        size_table = pd.DataFrame({
            "count": eval_data["segment_sizes"],
            "pct": eval_data["segment_size_pct"]
        })
        return text, size_table, counts

    elif intent == "explain_customer":
        if not customer_id:
            return "Which customer ID would you like to look up ", None, None
        result = explain_customer(customer_id, segmented, thresholds)
        if result is None:
            return f"I couldn't find customer {customer_id} in the dataset. Can you check the id again pls", None, None
        text = generate_answer(query, result)
        return text, None, None

    elif intent == "recommend":
        seg = seg_filter or "priority"
        recs = recommend_for_segment(seg)
        text = generate_answer(query, {"segment": seg, "recommendations": recs})
        return text, None, None

    elif intent == "trend":
        if dim == "location":
            table = trends.segment_by_location(segmented)
            text = generate_answer(query, table.to_dict())
            chart = table['priority'] if 'priority' in table.columns else None
            return text, table, chart
        elif dim == "gender":
            counts_g, pct_g = trends.segment_by_gender(segmented)
            text = generate_answer(query, counts_g.to_dict())
            return text, counts_g, counts_g
        elif dim == "age":
            table = trends.segment_by_age_group(segmented)
            text = generate_answer(query, table.to_dict())
            return text, table, table
        elif dim == "correlation":
            table = trends.correlation_summary(segmented)
            text = generate_answer(query, table.to_dict())
            return text, table, None
        elif dim == "recency":
            table = trends.recency_by_segment(segmented)
            text = generate_answer(query, table.to_dict())
            chart = table['mean']
            return text, table, chart
        else:
            table = trends.segment_size_summary(segmented)
            text = generate_answer(query, table.to_dict())
            return text, table, counts

    elif intent == "persona":
        personas = generate_personas(segmented)
        if seg_filter and seg_filter in personas:
            return personas[seg_filter]['description'], None, None
        text = "\n\n".join(f"{s.upper()}: {p['description']}" for s, p in personas.items())
        return text, None, None

    else:
        return ("I am not sure how to answer that"), None, None


query = st.chat_input("Ask anything about your customers...")

if query:
    st.session_state.history.append(("user", query, None, None))

    # Small loading indicator
    with st.spinner("BankSight is analyzing..."):
        text, table, chart = handle_query(query)

    st.session_state.history.append(("agent", text, table, chart))

for entry in st.session_state.history:
    role, text, table, chart = entry

    with st.chat_message(
        role,
        avatar = "🤖" if role == "agent" else "🧑"
    ):
        st.write(text)

        if table is not None:
            st.dataframe(table)

        if chart is not None:
            st.bar_chart(chart)