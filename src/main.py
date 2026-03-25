"""命令行入口 — 每日自动分析"""

import json
import logging
from datetime import datetime
from pathlib import Path

from src.config import load_config
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
    all_results = []
    market_labels = {"us": "美股", "hk": "港股", "a_share": "A股"}
    api_key = config.api_keys.anthropic
    model = config.ai.model

    for market_key in ("us", "hk", "a_share"):
        stocks = getattr(config.watchlist, market_key, [])
        if not stocks:
            continue

        print(f"\n{'='*50}")
        print(f"  {market_labels[market_key]} 分析")
        print(f"{'='*50}")

        for stock in stocks:
            print(f"\n分析 {stock.symbol} ({stock.name})...")
            try:
                df = fetch_history(stock.symbol, market_key, config.technical.lookback_days)
                quote = fetch_quote(stock.symbol, market_key)
                fundamentals = fetch_fundamentals(stock.symbol, market_key)

                if not df.empty:
                    df = compute_indicators(df, config.technical)
                    tech_signal = generate_technical_signal(df)
                else:
                    tech_signal = {"trend": "unknown", "momentum": "unknown", "signals": []}

                buffett_result = analyze_buffett(fundamentals, config.buffett_strategy)

                result = AnalysisResult(
                    symbol=stock.symbol,
                    name=stock.name,
                    market=market_key,
                    price=quote.get("price", 0) or tech_signal.get("price", 0),
                    change_pct=quote.get("change_pct", 0),
                    tech_signal=tech_signal,
                    buffett_result=buffett_result,
                    fundamentals=fundamentals,
                )
                result.compute_overall()

                ai_text = analyze_stock(result, api_key=api_key, model=model)
                result.ai_analysis = ai_text
                all_results.append(result)

                grade = buffett_result.get("grade", "?")
                pct = buffett_result.get("percentage", 0)
                print(f"  评级: {grade} ({pct}%) | 趋势: {tech_signal.get('trend')} | 建议: {buffett_result.get('recommendation')}")

            except Exception as e:
                logger.error(f"  分析 {stock.symbol} 失败: {e}")

    # 保存报告
    if all_results:
        report_dir = Path("data/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")

        report_lines = [f"# 每日投研报告 -- {today}\n"]
        report_lines.append(generate_market_overview(all_results, api_key=api_key, model=model))
        report_lines.append("\n---\n")

        for r in sorted(all_results, key=lambda x: x.overall_score, reverse=True):
            report_lines.append(f"\n## {r.symbol} ({r.name})")
            report_lines.append(f"评级: **{r.buffett_result.get('grade')}** | 综合: {r.overall_score}")
            report_lines.append(f"建议: {r.action}")
            if r.ai_analysis:
                report_lines.append(f"\n{r.ai_analysis}")
            report_lines.append("\n---")

        report_path = report_dir / f"report_{today}.md"
        report_path.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"\n报告已保存: {report_path}")

        json_path = report_dir / f"data_{today}.json"
        json_data = [{
            "symbol": r.symbol, "name": r.name, "market": r.market,
            "price": r.price, "grade": r.buffett_result.get("grade"),
            "score": r.overall_score, "recommendation": r.recommendation,
            "action": r.action,
        } for r in all_results]
        json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    print(f"巴菲特智能投研系统 -- {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    run_daily_analysis()


if __name__ == "__main__":
    main()
