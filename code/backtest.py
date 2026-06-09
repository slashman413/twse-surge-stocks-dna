"""歷史回測報表產生器 — TWSE 量化交易策略回測.

使用 data_loader + strategy v2 對指定年份區間進行回溯，
輸出買賣訊號統計與績效摘要。

用法：
    python backtest.py --ticker 2330 --start 2004 --end 2026
    python backtest.py --all --start 2004 --end 2004
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from data_loader import TWSEStockLoader
from strategy import (
    BigStockBuySignalV2,
    BigStockSellSignalV2,
    MarketSignalV2,
    SectorSignalV2,
    StockSurgeSignal,
    EntrySignal,
    CrashExitSignal,
    check_macd_surge,
    TradeSignal,
    MarketState,
)

REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORT_DIR, exist_ok=True)


def run_backtest(
    ticker: str,
    start_year: int = 2004,
    end_year: int = 2026,
    progress: bool = True,
) -> dict[str, Any]:
    """對單一股票執行歷史回測.

    Args:
        ticker: 股票代號
        start_year: 起始年份
        end_year: 結束年份
        progress: 顯示進度

    Returns:
        {
            "ticker": 股票代號,
            "period": f"{start}-{end}",
            "total_days": N,
            "buy_signals": [...],
            "sell_signals": [...],
            "market_states": {...},
            "signal_stats": {...},
        }
    """
    loader = TWSEStockLoader()
    start_str = f"{start_year}-01-01"
    end_str = f"{end_year}-12-31"

    if progress:
        print(f"📥 載入 {ticker} {start_str}~{end_str} ...")

    tf = loader.load_multi_timeframe(ticker, start=start_str, end=end_str, adjusted=True)
    daily = tf["daily"]
    weekly = tf["weekly"]
    monthly = tf["monthly"]

    if daily.empty:
        return {"ticker": ticker, "error": "無資料"}

    if progress:
        print(f"   日線 {len(daily)} 行, 週線 {len(weekly)} 行, 月線 {len(monthly)} 行")

    # ── 逐日掃描 ──
    buy_signals: list[dict] = []
    sell_signals: list[dict] = []
    market_states: Counter = Counter()
    surge_days = 0
    total_days = len(daily)

    # 大盤判定 (使用整段資料)
    ms = MarketSignalV2()
    market = ms.assess(daily)
    market_final = {
        "state": market.state.value,
        "score": market.score,
        "reasons": market.reasons,
    }

    # 每 60 天取樣一次完整訊號 (避免過多重複)
    sample_interval = 60

    for i in range(0, total_days, sample_interval):
        chunk = daily.iloc[:i+1]
        chunk_close = chunk["Adj_Close"]
        chunk_high = chunk["Adj_High"]
        chunk_low = chunk["Adj_Low"]

        if len(chunk) < 60:
            continue

        date_str = str(chunk["Date"].iloc[-1].date())

        # 買進訊號
        bbs = BigStockBuySignalV2()
        buy = bbs.evaluate(ticker, daily=chunk, weekly=weekly, monthly=monthly)
        if buy.signal in (TradeSignal.STRONG_BUY, TradeSignal.BUY):
            buy_signals.append({
                "date": date_str,
                "signal": buy.signal.value,
                "confidence": round(buy.confidence, 2),
                "met": buy.conditions_met,
            })

        # 賣出訊號
        bss = BigStockSellSignalV2()
        sell = bss.evaluate(ticker, daily=chunk, weekly=weekly, monthly=monthly)
        if sell.signal in (TradeSignal.STRONG_SELL, TradeSignal.SELL):
            sell_signals.append({
                "date": date_str,
                "signal": sell.signal.value,
                "confidence": round(sell.confidence, 2),
                "met": sell.conditions_met,
            })

        # 飆漲訊號
        surge = StockSurgeSignal()
        s = surge.evaluate(chunk)
        if s["both_surge"]:
            surge_days += 1

    if progress:
        print(f"   買進訊號: {len(buy_signals)} 次")
        print(f"   賣出訊號: {len(sell_signals)} 次")
        print(f"   飆漲訊號: {surge_days} 次")

    return {
        "ticker": ticker,
        "period": f"{start_year}-{end_year}",
        "total_days": total_days,
        "market": market_final,
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "surge_days": surge_days,
        "total_samples": total_days // sample_interval,
    }


def generate_report(results: list[dict[str, Any]]) -> str:
    """產生回測報表文字.

    Args:
        results: run_backtest 結果列表

    Returns:
        報表文字
    """
    lines = []
    lines.append("=" * 60)
    lines.append("  TWSE 量化策略歷史回測報告")
    lines.append(f"  產生時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 60)

    for r in results:
        if "error" in r:
            lines.append(f"\n❌ {r['ticker']}: {r['error']}")
            continue

        lines.append(f"\n{'─' * 40}")
        lines.append(f"  📈 {r['ticker']} ({r['period']})")
        lines.append(f"{'─' * 40}")
        lines.append(f"  總樣本數: {r['total_days']} 日")
        lines.append(f"  掃描頻率: 每 60 日取樣一次")

        # 大盤狀態
        m = r.get("market", {})
        if m:
            lines.append(f"\n  大盤狀態: {m.get('state', 'N/A')} (score={m.get('score', 0)})")
            for reason in m.get("reasons", [])[:5]:
                lines.append(f"    • {reason}")

        # 買進訊號統計
        buys = r.get("buy_signals", [])
        lines.append(f"\n  🟢 買進訊號: {len(buys)} 次")
        high_conf = [b for b in buys if b["confidence"] >= 0.75]
        if high_conf:
            lines.append(f"    高信心度 (≥75%): {len(high_conf)} 次")
        for b in buys[:10]:
            lines.append(f"    + {b['date']} | {b['signal']} ({b['confidence']*100:.0f}%)")
            for cond in b["met"][:3]:
                lines.append(f"      └ {cond}")
        if len(buys) > 10:
            lines.append(f"    ... 尚有 {len(buys)-10} 筆")

        # 賣出訊號統計
        sells = r.get("sell_signals", [])
        lines.append(f"\n  🔴 賣出訊號: {len(sells)} 次")
        high_conf_s = [s for s in sells if s["confidence"] >= 0.6]
        if high_conf_s:
            lines.append(f"    高信心度 (≥60%): {len(high_conf_s)} 次")
        for s in sells[:10]:
            lines.append(f"    - {s['date']} | {s['signal']} ({s['confidence']*100:.0f}%)")
            for cond in s["met"][:3]:
                lines.append(f"      └ {cond}")
        if len(sells) > 10:
            lines.append(f"    ... 尚有 {len(sells)-10} 筆")

        # 飆漲訊號
        lines.append(f"\n  ⚡ 飆漲訊號 (DIF210+ADX300雙螺旋): {r.get('surge_days', 0)} 次")

        # 總結
        lines.append(f"\n  📊 摘要")
        lines.append(f"     取樣次數: {r.get('total_samples', 0)}")
        lines.append(f"     買進率: {len(buys)/max(r.get('total_samples',1),1)*100:.1f}%")
        lines.append(f"     賣出率: {len(sells)/max(r.get('total_samples',1),1)*100:.1f}%")

    lines.append(f"\n{'=' * 60}")
    lines.append("  報告完畢")
    lines.append(f"{'=' * 60}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="TWSE 歷史回測報表")
    parser.add_argument("--ticker", default=None, help="股票代號")
    parser.add_argument("--all", action="store_true", help="回測所有可用股票")
    parser.add_argument("--watchlist", default="2330,2454,2317,2308,2301", help="逗號分隔清單")
    parser.add_argument("--start", type=int, default=2004, help="起始年份")
    parser.add_argument("--end", type=int, default=2026, help="結束年份")
    parser.add_argument("--output", default=None, help="輸出檔案路徑")
    args = parser.parse_args()

    if args.all:
        loader = TWSEStockLoader()
        tickers = loader.list_available_tickers()
        # 過濾掉非數字代號 (權證、認購等)
        tickers = [t for t in tickers if t.isdigit() and len(t) == 4][:50]  # 前50檔測試
    elif args.ticker:
        tickers = [args.ticker]
    else:
        tickers = [t.strip() for t in args.watchlist.split(",")]

    results = []
    for t in tickers:
        r = run_backtest(t, args.start, args.end)
        results.append(r)

    report = generate_report(results)

    output_path = args.output or os.path.join(
        REPORT_DIR, f"backtest_{date.today().isoformat()}.txt",
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    # ── 輸出 JSON (供 GitHub Pages dashboard 使用) ──
    json_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..",
        "twse-surge-stocks-dna", "docs", "backtest_data.json",
    ) if os.path.exists("D:/twse-surge-stocks-dna") else None

    if json_path and os.path.exists(os.path.dirname(json_path)):
        import json as json_mod
        summary = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_until": f"{args.end}",
            "period": f"{args.start}-{args.end}",
            "tickers_tested": len(results),
            "ticker": args.ticker or "multiple",
            "market": results[0].get("market") if results else None,
            "buy_signals": [],
            "sell_signals": [],
        }
        for r in results:
            for b in r.get("buy_signals", []):
                entry = dict(b)
                entry["ticker"] = r.get("ticker", "")
                summary["buy_signals"].append(entry)
            for s in r.get("sell_signals", []):
                entry = dict(s)
                entry["ticker"] = r.get("ticker", "")
                summary["sell_signals"].append(entry)

        with open(json_path, "w", encoding="utf-8") as f:
            json_mod.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"📊 Dashboard JSON: {json_path}")

    print(report)
    print(f"\n📁 報表已儲存: {output_path}")


if __name__ == "__main__":
    main()
