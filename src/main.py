"""命令行入口 — 每日自动分析"""

import json
import logging
from datetime import datetime
from pathlib import Path

from src.config import load_config, get_active_provider
from src.data.price import fetch_history, fetch_quote
from src.data.financial import fetch_fundamentals
from src.analysis.technical import compute_indicators, generate_technical_signal
from src.analysis.fundamental import analyze_buffett
from src.analysis.signals import AnalysisResult
from src.ai.summarizer import analyze_stock, generate_market_overview

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_daily_analysis():
    """执行每日完整分析"""
    config = load_config()
    provider = get_active_provider(config)
    all_results = []
    market_labels = {"us": "美股", "hk": "港股", "a_share": "A股"}

    for market_key in ("us", "hk", "a_share"):
        stocks = getattr(config.watchlist, market_key, [])
        if not stocks:
            continue

        print("\n" + "=" * 50)
        print("  {} 分析".format(market_labels[market_key]))
        print("=" * 50)

        for stock in stocks:
            print("\n分析 {} ({})...".format(stock.symbol, stock.name))
            try:
                df = fetch_history(stock.symbol, market_key, config.technical.lookback_days)
                quote = fetch_quote(stock.symbol, market_key)
                fundamentals = fetch_fundamentals(stock.symbol, market_key)

                if not df.empty:
                    df = compute_indicators(df, config.technical)
                    tech_signal = generate_technical_signal(df)
                else:
                    tech_signal = {"trend": "unknown", "momentum": "unknown",
                                   "signals": [], "trend_score": 0}

                buffett_result = analyze_buffett(fundamentals, config.buffett_strategy)

                result = AnalysisResult(
                    symbol=stock.symbol, name=stock.name, market=market_key,
                    price=quote.get("price", 0) or tech_signal.get("price", 0),
                    change_pct=quote.get("change_pct", 0),
                    tech_signal=tech_signal, buffett_result=buffett_result,
                    fundamentals=fundamentals,
                )
                result.compute_overall()

                ai_text = analyze_stock(result, provider=provider)
                result.ai_analysis = ai_text
                all_results.append(result)

                grade = buffett_result.get("grade", "?")
                pct = buffett_result.get("percentage", 0)
                print("  评级: {} ({}%) | 趋势: {} | 建议: {}".format(
                    grade, pct, tech_signal.get("trend"), buffett_result.get("recommendation")))

            except Exception as e:
                logger.error("  分析 {} 失败: {}".format(stock.symbol, e))

    # 保存报告
    if all_results:
        report_dir = Path("data/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")

        report_lines = ["# 每日投研报告 -- {}\n".format(today)]
        report_lines.append(generate_market_overview(all_results, provider=provider))
        report_lines.append("\n---\n")

        for r in sorted(all_results, key=lambda x: x.overall_score, reverse=True):
            report_lines.append("\n## {} ({})".format(r.symbol, r.name))
            report_lines.append("评级: **{}** | 综合: {}".format(
                r.buffett_result.get("grade"), r.overall_score))
            report_lines.append("建议: {}".format(r.action))
            if r.ai_analysis:
                report_lines.append("\n{}".format(r.ai_analysis))
            report_lines.append("\n---")

        report_path = report_dir / "report_{}.md".format(today)
        report_path.write_text("\n".join(report_lines), encoding="utf-8")
        print("\n报告已保存: {}".format(report_path))

        json_path = report_dir / "data_{}.json".format(today)
        json_data = [{
            "symbol": r.symbol, "name": r.name, "market": r.market,
            "price": r.price, "grade": r.buffett_result.get("grade"),
            "score": r.overall_score, "recommendation": r.recommendation,
            "action": r.action,
        } for r in all_results]
        json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    print("巴菲特智能投研系统 -- {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")))
    print("=" * 60)
    run_daily_analysis()


if __name__ == "__main__":
    main()
