import json
import re
import requests

CLOUD_FUNCTION_URL = "https://banksight-parser-578208846224.europe-west1.run.app"


def _rule_based_parse(query):
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


def _apply_overrides(query, parsed):
    q = query.lower()
    is_segmentation_request = (
        re.search(r"segment .*into", q) or re.search(r"classify .*into", q) or re.search(r"group .*into", q)
    ) and not parsed.get("customer_id")

    if is_segmentation_request:
        parsed["intent"] = "segment_overview"

    return parsed


def parse_intent(query):
    try:
        response = requests.post(CLOUD_FUNCTION_URL, json={"query": query}, timeout=15)
        parsed = response.json()

        if "error" in parsed:
            raise Exception(parsed["error"])

        return _apply_overrides(query, parsed)

    except Exception as e:
        print(f"[Cloud function call failed, using rule-based fallback: {e}]")
        fallback = _rule_based_parse(query)
        fallback["_source"] = "rule_based_fallback"
        return _apply_overrides(query, fallback)

def generate_answer(query, data):
    """for natural text and stuff"""
    try:
        response = requests.post(
            CLOUD_FUNCTION_URL,
            json={"mode": "answer", "query": query, "data": str(data)},
            timeout=15
        )
        result = response.json()
        return result.get("answer", "Here's what I found:")
    except Exception as e:
        print(f"[Answer generation failed: {e}]")
        return "Here's what I found:"

if __name__ == "__main__":
    test_queries = [
        "Segment customers into priority, regular and dormant based on balance and transactions",
        "On what basis were priority customers selected?",
        "Why is customer C1010011 in priority?",
    ]
    for q in test_queries:
        print(f"\nQuery: {q}")
        print(parse_intent(q))