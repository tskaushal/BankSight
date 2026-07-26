import json
import re
from google import genai


GEMINI_API_KEY = "AQ.Ab8RN6L2G5RRQ5uY842dnKBQSmEiFQ6g3ID_mnwa-ZIYXYHS5g"

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-3.5-flash"

INTENT_PROMPT = """You are an intent parser for a bank customer segmentation agent.
Given a user's natural language query, extract the intent and any relevant entities.

Return ONLY valid JSON, no other text, no markdown code blocks. Format:
{{
  "intent": one of ["segment_overview", "criteria", "aggregate", "transition", "explain_customer", "recommend", "trend", "persona", "unclear"],
  "customer_id": string or null,
  "segment_filter": one of ["priority", "regular", "dormant", null],
  "trend_dimension": one of ["location", "gender", "age", "correlation", "recency", null],
  "needs_clarification": true or false,
  "clarification_question": string or null
}}

Guidance:
- "segment_overview": general questions about segmentation / how customers are grouped
- "criteria": asking what rules/basis were used to select a segment
- "aggregate": asking for averages/sums/stats across segments
- "transition": asking which customers could move segments, or how to convert them
- "explain_customer": asking about a SPECIFIC customer ID
- "recommend": asking what products/strategies to offer a segment
- "trend": asking about patterns across location, gender, age, correlations, or recency
- "persona": asking for a description of what a segment "looks like"
- "unclear": doesn't map to any of the above

If the query mentions a customer ID (format like C followed by digits), extract it exactly.
If missing something critical (e.g. asks about "a customer" with no ID), set
needs_clarification true with a short clarification_question.

Query: "{query}"
"""


def _rule_based_parse(query):
    """Fallback parser - used only if the LLM call fails (bad key, no internet,
    rate limit, malformed response). No external dependency, always works."""
    q = query.lower().strip()

    result = {
        "intent": "unclear", "customer_id": None, "segment_filter": None,
        "trend_dimension": None, "needs_clarification": False,
        "clarification_question": None
    }

    id_match = re.search(r'\bC\d{6,}\b', query, re.IGNORECASE)
    if id_match:
        result["customer_id"] = id_match.group().upper()

    for seg in ["priority", "regular", "dormant"]:
        if seg in q:
            result["segment_filter"] = seg
            break

    if result["customer_id"]:
        result["intent"] = "explain_customer"
    elif any(p in q for p in ["on what basis", "how were", "what criteria", "what rules"]):
        result["intent"] = "criteria"
    elif any(p in q for p in ["convert", "become priority", "transition", "potential to"]):
        result["intent"] = "transition"
    elif any(p in q for p in ["recommend", "what products", "cross-sell", "upsell"]):
        result["intent"] = "recommend"
    elif any(p in q for p in ["typical", "describe", "persona", "look like"]):
        result["intent"] = "persona"
    elif any(p in q for p in ["trend", "breakdown", "by city", "correlation", "recency"]):
        result["intent"] = "trend"
        if "city" in q or "location" in q:
            result["trend_dimension"] = "location"
        elif "correlation" in q:
            result["trend_dimension"] = "correlation"
        elif "recency" in q:
            result["trend_dimension"] = "recency"
    elif any(p in q for p in ["average", "mean", "total", "how many"]):
        result["intent"] = "aggregate"
    elif any(p in q for p in ["segment", "group", "cluster"]):
        result["intent"] = "segment_overview"
    else:
        result["needs_clarification"] = True
        result["clarification_question"] = "Could you rephrase that?"

    return result


def parse_intent(query):
    """Primary: LLM-based parsing via Gemini. Falls back to rule-based only
    if the LLM call errors out for any reason."""
    try:
        prompt = INTENT_PROMPT.format(query=query)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        text = response.text.strip()
        if text.startswith("```"):
            text = text.strip("`").replace("json", "", 1).strip()

        parsed = json.loads(text)
        parsed["_source"] = "llm"
        return parsed

    except Exception as e:
        print(f"[LLM parse failed, using rule-based fallback: {e}]")
        fallback = _rule_based_parse(query)
        fallback["_source"] = "rule_based_fallback"
        return fallback


if __name__ == "__main__":
    test_queries = [
        "Segment customers into priority, regular and dormant based on balance and transactions",
        "On what basis were priority customers selected?",
        "What is the average transaction size for priority and regular customers?",
        "Which regular customers can be converted to priority? What should be done?",
        "Why is customer C1010011 in priority?",
        "What products should we recommend to dormant customers?",
        "Show me the segment breakdown by city",
        "What does a typical priority customer look like?",
    ]

    for q in test_queries:
        print(f"\nQuery: {q}")
        print(parse_intent(q))