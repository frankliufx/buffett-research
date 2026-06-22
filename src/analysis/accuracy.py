"""Per-analyst hit rate computation for hedge fund decisions.

Hit logic:
  bullish + current_price > decision_price → hit
  bearish + current_price < decision_price → hit
  neutral → skip (not counted)
"""
from __future__ import annotations


def compute_hedge_fund_accuracy(
    decisions: list[dict],
    current_prices: dict[str, float],
) -> dict[str, dict]:
    """Compute per-analyst prediction accuracy.

    Args:
        decisions: Output of get_decisions_for_accuracy(). Each dict must have
            symbol, market, price (float), votes_payload (list of vote dicts).
        current_prices: {"{market}:{symbol}": float} — current price lookup.

    Returns:
        {analyst_id: {name, total, hits, hit_rate, avg_confidence}}
        Analysts with 0 evaluated votes are omitted.
    """
    stats: dict[str, dict] = {}

    for decision in decisions:
        symbol = decision.get("symbol", "")
        market = decision.get("market", "")
        entry_price = decision.get("price")
        votes = decision.get("votes_payload") or []

        if not symbol or not market or entry_price is None:
            continue

        key = "{}:{}".format(market, symbol)
        current_price = current_prices.get(key)
        if current_price is None:
            continue

        price_went_up = current_price > entry_price
        price_went_down = current_price < entry_price

        for vote in votes:
            analyst_id = vote.get("id")
            if not analyst_id:
                continue

            signal = (vote.get("signal") or "").lower()
            if signal == "neutral":
                continue

            confidence = vote.get("confidence")
            analyst_name = vote.get("name", analyst_id)

            if analyst_id not in stats:
                stats[analyst_id] = {
                    "name": analyst_name,
                    "total": 0,
                    "hits": 0,
                    "_confidence_sum": 0.0,
                    "avg_confidence": 0.0,
                    "hit_rate": 0.0,
                }

            rec = stats[analyst_id]
            rec["total"] += 1

            is_hit = (signal == "bullish" and price_went_up) or \
                     (signal == "bearish" and price_went_down)
            if is_hit:
                rec["hits"] += 1

            if confidence is not None:
                rec["_confidence_sum"] += float(confidence)

    for rec in stats.values():
        total = rec["total"]
        rec["hit_rate"] = rec["hits"] / total if total > 0 else 0.0
        rec["avg_confidence"] = rec["_confidence_sum"] / total if total > 0 else 0.0
        del rec["_confidence_sum"]

    return {aid: rec for aid, rec in stats.items() if rec["total"] > 0}
