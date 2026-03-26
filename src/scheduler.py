"""定时推送调度器"""

import logging
import threading
import time
from datetime import datetime, date
from pathlib import Path

import schedule

from src.config import load_config, get_active_provider
from src.data.price import fetch_history, fetch_quote
from src.data.financial import fetch_fundamentals
from src.analysis.technical import compute_indicators, generate_technical_signal
from src.analysis.fundamental import analyze_buffett
from src.analysis.signals import AnalysisResult
from src.ai.summarizer import analyze_stock, generate_market_overview
from src.output.notify import (send_notification, format_daily_push,
                                check_and_send_price_alerts, format_weekly_portfolio_email)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Background thread state ────────────────────────────────────────────────
_bg_thread = None  # type: threading.Thread | None
_bg_lock = threading.Lock()
_LAST_RUN_FILE = Path(__file__).parent.parent / "data" / "cache" / "last_scheduler_run.txt"


def run_and_push():
    """执行分析并推送"""
    logger.info("开始每日分析...")
    config = load_config()
    provider = get_active_provider(config)
    all_results = []

    for market_key in ("us", "hk", "a_share"):
        stocks = getattr(config.watchlist, market_key, [])
        for stock in stocks:
            try:
                df = fetch_history(stock.symbol, market_key, config.technical.lookback_days)
                quote = fetch_quote(stock.symbol, market_key)
                fund = fetch_fundamentals(stock.symbol, market_key)

                if not df.empty:
                    df = compute_indicators(df, config.technical)
                    tech = generate_technical_signal(df)
                else:
                    tech = {"trend": "unknown", "momentum": "unknown", "signals": [], "trend_score": 0}

                buffett = analyze_buffett(fund, config.buffett_strategy)

                result = AnalysisResult(
                    symbol=stock.symbol, name=stock.name, market=market_key,
                    price=quote.get("price", 0) or tech.get("price", 0),
                    change_pct=quote.get("change_pct", 0),
                    tech_signal=tech, buffett_result=buffett, fundamentals=fund,
                )
                result.compute_overall()
                all_results.append(result)
                logger.info("  {} [{}] {:.0f}%".format(
                    stock.symbol, buffett.get("grade", "?"), buffett.get("percentage", 0)))
            except Exception as e:
                logger.error("  {} 分析失败: {}".format(stock.symbol, e))

    if not all_results:
        logger.warning("无分析结果，跳过推送")
        return

    # 生成市场总览
    overview = ""
    if provider:
        try:
            overview = generate_market_overview(all_results, provider=provider)
        except Exception as e:
            logger.error("AI 市场总览生成失败: {}".format(e))

    # 格式化推送内容
    title, content = format_daily_push(all_results, overview)

    # 发送每日报告
    success = send_notification(title, content, config.notify)
    if success:
        logger.info("推送发送成功")
    else:
        logger.warning("推送发送失败")

    # 价格提醒检查
    try:
        triggered = check_and_send_price_alerts(config)
        if triggered:
            logger.info(f"价格提醒已触发并发送: {[t['symbol'] for t in triggered]}")
    except Exception as e:
        logger.error(f"价格提醒检查失败: {e}")

    # 每周日发送持仓回顾邮件
    today_wd = date.today().weekday()  # 0=Mon, 6=Sun
    if today_wd == 6:  # Sunday
        try:
            from src.ai.summarizer import generate_weekly_report
            from src.config import get_premium_provider
            premium = get_premium_provider(config)

            # Generate AI weekly report
            market_summary = "\n".join(
                "- {} ({}): Grade {} ({:.0f}%)".format(
                    r.symbol, r.name, r.buffett_result.get("grade", "?"),
                    r.buffett_result.get("percentage", 0))
                for r in all_results[:15])
            weekly_ai = ""
            if premium:
                try:
                    weekly_ai = generate_weekly_report(
                        market_summary, market_summary, "N/A", premium)
                except Exception:
                    pass

            # Format and send weekly digest
            # TODO: iterate all users when multi-user scheduler is implemented
            title, content = format_weekly_portfolio_email("frank", weekly_ai)
            send_notification(title, content, config.notify)
            logger.info("Weekly portfolio digest sent")
        except Exception as e:
            logger.warning("Weekly digest failed: %s", e)

    # 记录最后运行时间
    try:
        _LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LAST_RUN_FILE.write_text(datetime.now().isoformat())
    except Exception:
        pass


def check_price_alerts_now() -> list:
    """独立执行价格提醒检查（不触发每日报告），供 Settings 页手动调用"""
    config = load_config()
    return check_and_send_price_alerts(config)


def get_last_run_time() -> str:
    """返回最后一次调度运行的时间字符串，或 'Never'"""
    try:
        if _LAST_RUN_FILE.exists():
            raw = _LAST_RUN_FILE.read_text().strip()
            dt = datetime.fromisoformat(raw)
            return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return "Never"


def _bg_scheduler_loop():
    """Background thread: rebuild schedule from config and run pending jobs."""
    logger.info("Background scheduler loop started")
    while True:
        try:
            config = load_config()
            notify = config.notify
            if not notify.enabled:
                time.sleep(300)
                continue

            schedule.clear()
            if notify.schedule_days == "mon-fri":
                for day in (schedule.every().monday, schedule.every().tuesday,
                            schedule.every().wednesday, schedule.every().thursday,
                            schedule.every().friday):
                    day.at(notify.schedule_time).do(run_and_push)
            else:
                schedule.every().day.at(notify.schedule_time).do(run_and_push)

            schedule.run_pending()
        except Exception as e:
            logger.error(f"Background scheduler error: {e}")
        time.sleep(60)


def start_background_scheduler():
    """Start the background scheduler thread (idempotent — safe to call on every page load)."""
    global _bg_thread
    with _bg_lock:
        if _bg_thread is None or not _bg_thread.is_alive():
            _bg_thread = threading.Thread(
                target=_bg_scheduler_loop, daemon=True, name="buffett-scheduler"
            )
            _bg_thread.start()
            logger.info("Background scheduler thread started")


def main():
    config = load_config()
    notify = config.notify

    if not notify.enabled:
        logger.warning("推送未启用。请在 config.yaml 或 Web 设置页面中启用。")
        logger.info("直接执行一次分析...")
        run_and_push()
        return

    schedule_time = notify.schedule_time
    logger.info("定时推送已启动，每日 {} 执行".format(schedule_time))

    if notify.schedule_days == "mon-fri":
        schedule.every().monday.at(schedule_time).do(run_and_push)
        schedule.every().tuesday.at(schedule_time).do(run_and_push)
        schedule.every().wednesday.at(schedule_time).do(run_and_push)
        schedule.every().thursday.at(schedule_time).do(run_and_push)
        schedule.every().friday.at(schedule_time).do(run_and_push)
    else:
        schedule.every().day.at(schedule_time).do(run_and_push)

    logger.info("等待下次执行... (Ctrl+C 退出)")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
