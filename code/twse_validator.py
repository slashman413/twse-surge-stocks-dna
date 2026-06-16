TWSE 還原權值驗證器 — 與 yfinance 比對確認資料正確性
=====================================================

使用方式：
    python twse_validator.py --tickers 2330,2454,2317,2412,2308
    python twse_validator.py --tickers 2330 --full  # 完整檢驗

策略：
    1. 用 yfinance 抓取指定台股的原始 OHLCV + 還原收盤價 (Adj Close)
    2. 用我們 adjuster.py 的 Backward Adjustment 計算還原價
    3. 比對兩者的 Adj Close，計算 MAPE (平均絕對百分比誤差)
    4. 若有偏差，分析原因（股利缺失、配股率差異等）

驗證通過條件：MAPE < 0.5% 且最大單日誤差 < 2%

from __future__ import annotations

import os
import sys
import argparse
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

# ── 路徑 ──────────────────────────────────────────────────────

# ── 還原權值計算 (獨立版, 與 adjuster.py 邏輯一致) ──────────


def backward_adjust(
    prices: pd.DataFrame,
    dividends: pd.DataFrame | None = None,
) -> pd.DataFrame:

    與 twse_adjuster.py 的 _compute_cumulative_factors 邏輯相同，
    但獨立於 adjuster.py 模組。

    Args:
        prices: 原始日線，須含 ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        dividends: 除權息資料，須含 ['Date', 'Cash_Dividend', 'Stock_Dividend']
                   若 None 則不回補（僅用 yfinance 的 dividend 欄位）

    Returns:
        含 Adj_Open, Adj_High, Adj_Low, Adj_Close, CumFactor 的 DataFrame
    n = len(result)


    # 建立事件查詢
    event_map: dict[pd.Timestamp, tuple[float, float]] = {}
    if dividends is not None:
        for _, row in dividends.iterrows():
            )

    # 遞迴計算累積因子（從最新日往舊日）
    cum_factors = np.ones(n, dtype=np.float64)
    cum_factor = 1.0

    for i in range(n - 1, -1, -1):
        cum_factors[i] = cum_factor

        evt = event_map.get(dates[i])
        if evt is not None and i > 0:
            d_cash, d_stock = evt
            prev_close = float(closes[i - 1])
            if np.isnan(prev_close) or prev_close <= 0:
                continue

            denom = 1.0 + d_stock / 1000.0
            ref_price = (prev_close - d_cash) / denom
            event_factor = ref_price / prev_close
            event_factor = min(event_factor, 1.0)
            cum_factor *= event_factor


    return result


# ═══════════════════════════════════════════════════════════════
# yfinance 資料擷取
# ═══════════════════════════════════════════════════════════════

def fetch_yf_data(
    ticker: str,
) -> dict[str, pd.DataFrame]:

    Args:

    Returns:
        {
        }
    tk = yf.Ticker(yf_ticker)

    # 抓歷史資料 (auto_adjust=False 取得原始 + Adj Close)
    hist = tk.history(period=period, auto_adjust=False)
    if hist.empty:
        # 試 OTC
        tk = yf.Ticker(yf_ticker)
        hist = tk.history(period=period, auto_adjust=False)

    if hist.empty:

    # 重新命名欄位
    hist = hist.rename(columns={
    })
    hist.reset_index(inplace=True)

    # 股利資料 (從 tk.dividends 取得，更可靠)
    div = tk.dividends
    splits = tk.splits

    div_df = pd.DataFrame()
    if not div.empty:
        div_df = div.reset_index()

    split_df = pd.DataFrame()
    if not splits.empty:
        split_df = splits.reset_index()

    return {
    }


# ═══════════════════════════════════════════════════════════════
# 驗證比對
# ═══════════════════════════════════════════════════════════════

def validate_ticker(
    ticker: str,
    plot: bool = False,
) -> dict[str, any]:

    Args:
        ticker: 台股代號
        period: 回測期間
        plot: 是否輸出 HTML 圖表

    Returns:
        驗證報告 dict

    # 1. 從 yfinance 抓資料
    yf_data = fetch_yf_data(ticker, period=period)

    if hist.empty:


    # 2. 建立 dividends 資料 (從 yfinance)
    div_events = []
        # 合併到 hist 上，找出有配息的日期
        for _, row in hist_with_div.iterrows():
                div_events.append({
                })

    # 3. 處理股票分割
    split_events = []
        for _, row in hist_with_split.iterrows():
                # yfinance split ratio: 2.0 = 2:1 split
                # For 配股: Stock_Dividend = (ratio - 1) * 1000
                if ratio > 0:
                    stock_div = max(0, (ratio - 1.0) * 1000.0)
                    split_events.append({
                    })

    # 合併所有事件 (按日期排序)
    all_events = pd.DataFrame(div_events + split_events)
    if not all_events.empty:

        # 顯示前幾筆
        for _, evt in all_events.head(10).iterrows():
            parts = []

        if len(all_events) > 10:
    else:

    # 4. 用我們的 Backward Adjustment 計算
    prices_for_adj = hist.rename(columns={

    adj_result = backward_adjust(prices_for_adj, all_events if not all_events.empty else None)

    # 5. 比對：我們的 Adj_Close vs yfinance 的 Adj Close
    # yfinance auto_adjust=False 已經有 'Adj Close' 欄位
    comp = adj_result.copy()

    # 對齊日期

    # 6. 計算誤差指標
    if valid.empty:
        return {
        }

        * 100
    )


    recent = valid.tail(min(252, len(valid)))


    # 找出最大誤差日

    # 7. 判斷
    passed = mape < 0.5 and max_err < 2.0

    # 8. 找出疑似缺失的股利事件
    # 檢查 CumFactor 在股利日前後是否有變化
    missing_divs = []
    if not all_events.empty and len(valid) > 20:
        for _, evt in all_events.iterrows():
            # 找事件日前後的 CumFactor 變化
            if not before.empty and not after.empty:
                if abs(cf_before - cf_after) < 1e-8:
                    missing_divs.append(evt_date)

    if missing_divs:
        for d in missing_divs[:5]:

    return {
    }


# ═══════════════════════════════════════════════════════════════
# 大量驗證 (多檔股票)
# ═══════════════════════════════════════════════════════════════

def validate_batch(
    tickers: list[str],
) -> pd.DataFrame:

    Args:
        tickers: 股票代號列表
        period: 回測期間

    Returns:
        驗證摘要 DataFrame
    results = []
    for i, ticker in enumerate(tickers):
        try:
            r = validate_ticker(ticker, period=period)
            results.append(r)
        except Exception as e:

    summary = pd.DataFrame(results)

    # 摘要
    total = len(results)


    return summary


# ═══════════════════════════════════════════════════════════════
# 股利資料匯出 (給 adjuster.py 用)
# ═══════════════════════════════════════════════════════════════

def export_dividends_from_yf(
    tickers: list[str],
    output_path: str | None = None,
) -> pd.DataFrame:

    對每檔股票抓取 dividend history + stock splits，
    轉換成 adjuster.py 接受的格式:
        Date, Ticker, Cash_Dividend, Stock_Dividend

    Args:
        tickers: 股票代號列表
        output_path: 匯出 CSV 路徑 (None=不回檔)
        period: 往回抓取期間

    Returns:
        合併的股利 DataFrame
    all_divs = []

    for i, ticker in enumerate(tickers):
        try:
            # 試上市

            dividends = tk.dividends
            splits = tk.splits

            if dividends.empty and splits.empty:
                # 試上櫃
                dividends = tk.dividends
                splits = tk.splits

            events = []

            # 現金股利
            if not dividends.empty:
                for dt, amt in dividends.items():
                    dt_naive = pd.Timestamp(dt).tz_localize(None)
                    events.append({
                    })

            # 股票股利 (從 split ratio 換算)
            if not splits.empty:
                for dt, ratio in splits.items():
                    dt_naive = pd.Timestamp(dt).tz_localize(None)
                    if ratio != 1.0 and ratio > 0:
                        stock_div = max(0, (ratio - 1.0) * 1000.0)
                        events.append({
                        })

            if events:
                all_divs.append(df)
            else:

        except Exception as e:

    if not all_divs:
        return pd.DataFrame()


    if output_path:

    return merged


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


    args = parser.parse_args()

    if args.export_dividends:
        export_dividends_from_yf(tickers, output_path=args.export_dividends,
    else:
        validate_batch(tickers, period=args.period)
