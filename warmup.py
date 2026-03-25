#!/usr/bin/env python3
"""预热缓存 — 一次性拉取所有关注列表数据，后续页面秒开

用法:
    python warmup.py          # 预热全部数据
    python warmup.py --quick  # 仅预热基本面（跳过K线，更快）
"""

import sys
import time

from src.config import load_config
from src.data.price import fetch_quote, fetch_history
from src.data.financial import fetch_fundamentals
from src.data.macro import get_buffett_indicator


def main():
    quick = "--quick" in sys.argv
    config = load_config()

    print("=" * 50)
    print("  巴菲特投研系统 — 数据预热")
    print("=" * 50)

    # 1. 巴菲特指标
    print("\n[1/2] 巴菲特指标...")
    t0 = time.time()
    try:
        bi = get_buffett_indicator()
        for k in ("cn", "us", "hk"):
            d = bi[k]
            live = "LIVE" if d["is_live"] else "REF"
            print("  {} {}% ({}) [{}]".format(d["name"], d["ratio"], d["label"], live))
        print("  OK ({:.1f}s)".format(time.time() - t0))
    except Exception as e:
        print("  WARN: {}".format(e))

    # 2. 个股数据
    print("\n[2/2] 个股数据预热...")
    all_stocks = []
    for market_key, market_name in [("us", "US"), ("hk", "HK"), ("a_share", "A-Share")]:
        stocks = getattr(config.watchlist, market_key, [])
        for s in stocks:
            all_stocks.append((s.symbol, s.name, market_key, market_name))

    total = len(all_stocks)
    success = 0
    for i, (symbol, name, market, label) in enumerate(all_stocks, 1):
        t0 = time.time()
        status = []
        try:
            # 基本面（最重要，含ROE/利润率等）
            fund = fetch_fundamentals(symbol, market)
            has_roe = fund.get("roe") is not None
            status.append("Fund" + ("+" if has_roe else "-"))

            # 行情
            quote = fetch_quote(symbol, market)
            status.append("Quote" + ("+" if quote.get("price") else "-"))

            if not quick:
                # K线历史
                df = fetch_history(symbol, market, config.technical.lookback_days)
                status.append("K" + ("+{}d".format(len(df)) if not df.empty else "-"))

            elapsed = time.time() - t0
            print("  [{}/{}] {} {} ({}) {} ({:.1f}s)".format(
                i, total, symbol, name, label, " ".join(status), elapsed))
            success += 1
        except Exception as e:
            print("  [{}/{}] {} {} — ERROR: {}".format(i, total, symbol, name, e))

    print("\n" + "=" * 50)
    print("  预热完成: {}/{} 只股票成功".format(success, total))
    if quick:
        print("  (快速模式，K线数据未预热)")
    print("  缓存目录: data/cache/")
    print("  现在启动 streamlit 将秒开！")
    print("=" * 50)


if __name__ == "__main__":
    main()
