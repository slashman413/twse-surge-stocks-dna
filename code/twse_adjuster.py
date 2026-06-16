TWSE 還原 K 線模組 — Backward Adjustment (向前還原權值)
=====================================================

使用方法：
    python twse_adjuster.py

資料流向：
    Raw/           ← 原始日線 + 除權息 CSV/JSON
    Adjusted/      ← .parquet (依 Ticker 分區)
    Code/          ← 本模組

依賴：pandas, numpy, pyarrow (或 fastparquet)
安裝：pip install pandas numpy pyarrow

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Literal

import numpy as np
import pandas as pd

# ── 路徑設定 ──────────────────────────────────────────────────

# ── 欄位名稱對照 ──────────────────────────────────────────────
RAW_COLUMNS: dict[str, str] = {
}

DIV_COLUMNS: dict[str, str] = {
}



# ═══════════════════════════════════════════════════════════════
# 1. 資料清洗與標準化
# ═══════════════════════════════════════════════════════════════

def _roc_to_ad_year(roc_str: str) -> int:

    Args:

    Returns:
        西元年份
    if not m:
    roc_year = int(m.group(1))
    return roc_year + 1911


def _parse_roc_date(date_str: str) -> pd.Timestamp:
    if len(parts) != 3:
    roc_y, m, d = parts
    year = int(roc_y) + 1911


def _clean_numeric(val: str) -> float:

    Args:

    Returns:
        float 或 NaN
    if isinstance(val, (int, float)):
        return float(val)
        return np.nan
    return float(cleaned)


def clean_twse_data(
    df: pd.DataFrame,
    *,
    inplace: bool = False,
) -> pd.DataFrame:

    處理項目：
        1. 欄位中文化 → 英文 (Date, Ticker, Open, High, Low, Close, Volume)
        2. 民國年 → 西元年 YYYY-MM-DD
        4. Volume 轉 int64 (NaN → 0)

    Args:
        df: 原始 DataFrame (含中文欄名)
        inplace: 是否原地修改

    Returns:
        清洗後的 DataFrame
    result = df if inplace else df.copy()

    # ── 1a. 欄位重新命名 ──
    result.rename(columns=RAW_COLUMNS, inplace=True)
    result = result[list(RAW_COLUMNS.values())]  # 只保留已知欄位

    # ── 1b. 日期轉換 ──

    # ── 1c. 數值清洗 ──

        .apply(_clean_numeric)
        .fillna(0)
    )

    # ── 1d. 前向填補 (依 Ticker 分組, 確保不跨 ticker) ──

    result.reset_index(drop=True, inplace=True)
    return result


def clean_dividend_data(
    df: pd.DataFrame,
    *,
    inplace: bool = False,
) -> pd.DataFrame:

    Args:
        df: 原始除權息 DataFrame
        inplace: 是否原地修改

    Returns:
        清洗後的 DataFrame，現金股利/股票股利 NaN → 0.0
    result = df if inplace else df.copy()
    result.rename(columns=DIV_COLUMNS, inplace=True)
    result = result[list(DIV_COLUMNS.values())]

    )
    )
    result.reset_index(drop=True, inplace=True)
    return result


# ═══════════════════════════════════════════════════════════════
# 2. 還原權值計算 (Backward Adjustment / 向前還原)
# ═══════════════════════════════════════════════════════════════
#
# 計算邏輯：
#   ┌─────────────────────────────────────────────────────────────┐
#   │  向前還原 (Backward Adjustment)：以最新交易日收盤價為基準， │
#   │  將歷史價格依除權息事件向前調整，使其與當前股價具可比性。  │
#   │                                                           │
#   │  累積還原因子 CumFactor 由最新日往舊日遞迴計算：           │
#   │                                                           │
#   │    CumFactor[t-1] = CumFactor[t] × EventFactor[t]         │
#   │                                                           │
#   │  其中 EventFactor[t] 為除權息發生日在 t 的事件因子：       │
#   │    配息 (現金股利 D) :  (Close[t-1] - D) / Close[t-1]     │
#   │    配股 (股票股利 S) :  1 / (1 + S/1000)                  │
#   │    同時發生           :  (Close[t-1] - D) /               │
#   │                          (Close[t-1] × (1 + S/1000))      │
#   │                                                           │
#   │  還原價格 = 原始價格 × CumFactor                          │
#   └─────────────────────────────────────────────────────────────┘
#
#   Volume 同步調整：歷史成交量 × CumFactor（累積因子已含配股成分）
# ═══════════════════════════════════════════════════════════════

def _compute_cumulative_factors(
    dates: np.ndarray,
    closes: np.ndarray,
    ticker_events: pd.DataFrame,
) -> np.ndarray:

    Args:
        dates:   日期陣列 (ascending, datetime64[D])
        closes:  收盤價陣列 (float32, ascending 與 dates 對齊)
        ticker_events: 該股票的除權息事件 DataFrame,
                       含 Date, Cash_Dividend, Stock_Dividend

    Returns:
        cum_factors: 與 dates 同長度的 float64 陣列,
                     cum_factors[-1] == 1.0 (最新日為基準)
    n = len(dates)
    cum_factors = np.ones(n, dtype=np.float64)
    cum_factor = 1.0

    # 建立事件查詢 dict: {日期: (現金股利, 股票股利)}
    event_map: dict[pd.Timestamp, tuple[float, float]] = {}
    for _, row in ticker_events.iterrows():

    # ── 從最新日向舊日遞迴 ──
    for i in range(n - 1, -1, -1):
        cum_factors[i] = cum_factor

        # 若該日有除權息事件，更新累積因子
        evt = event_map.get(dates[i])
        if evt is not None and i > 0:
            d_cash, d_stock = evt

            # 前一天(除權息前)的實際收盤價
            prev_close = float(closes[i - 1])

            # 若前日無交易 (Close=NaN), 跳過此事件因子計算
            if np.isnan(prev_close) or prev_close <= 0:
                continue

            # ── 計算 EventFactor ──
            # 參考價 = (前收 - 配息) / (1 + 配股/1000)
            denom = 1.0 + d_stock / 1000.0
            ref_price = (prev_close - d_cash) / denom

            # EventFactor = 參考價 / 前收
            event_factor = ref_price / prev_close

            # 安全邊界：理論上 event_factor 應接近但 <= 1.0
            event_factor = min(event_factor, 1.0)

            cum_factor *= event_factor

    return cum_factors


def calculate_adjusted_ohlcv(
    daily: pd.DataFrame,
    events: pd.DataFrame,
) -> pd.DataFrame:

    對每一檔股票：
        1. 按日期升冪排序
        2. 從最新日往舊日遞迴計算累積還原因子
        3. 將 OHLC × CumFactor, Volume × CumFactor

    Args:
        daily:  清洗後的日線 DataFrame (含 Date, Ticker, OHLCV)
        events: 清洗後的除權息 DataFrame (含 Date, Ticker,
                Cash_Dividend, Stock_Dividend)

    Returns:
        DataFrame 含：
            Date, Ticker,
            Adj_Open, Adj_High, Adj_Low, Adj_Close,
            Adj_Volume, CumFactor
    result.reset_index(drop=True, inplace=True)

    adj_open = np.empty(len(result), dtype=np.float64)
    adj_high = np.empty(len(result), dtype=np.float64)
    adj_low = np.empty(len(result), dtype=np.float64)
    adj_close = np.empty(len(result), dtype=np.float64)
    adj_volume = np.empty(len(result), dtype=np.float64)
    cum_factors = np.empty(len(result), dtype=np.float64)


    for i, ticker in enumerate(tickers):
        if i > 0 and i % 1000 == 0:
        idx = np.where(mask)[0]


        cf = _compute_cumulative_factors(dates, closes, ticker_events)

        # 向量化應用累積因子
        adj_open[idx] = opens * cf
        adj_high[idx] = highs * cf
        adj_low[idx] = lows * cf
        adj_close[idx] = closes * cf
        adj_volume[idx] = vols * cf
        cum_factors[idx] = cf


    return result


# ═══════════════════════════════════════════════════════════════
# 3. 匯入/匯出
# ═══════════════════════════════════════════════════════════════

def load_raw_daily(path: str | None = None) -> pd.DataFrame:

    爬蟲儲存為 parquet (乾淨格式)，若無 parquet 則 fallback 到 CSV。

    Args:
        path: 指定單一檔案；None 則掃描 RAW_DIR 下各年份子目錄

    Returns:
        原始日線 DataFrame (欄位: Date, Ticker, Open, High, Low, Close, Volume)
    if path:
        # 自動判斷副檔名
            return pd.read_parquet(path)
        return pd.read_csv(path)

    # ── 掃描所有年份子目錄下的 *_daily.parquet ──
    year_dirs = sorted(
        d for d in os.listdir(RAW_DIR)
        if d.isdigit() and os.path.isdir(os.path.join(RAW_DIR, d))
    )
    if not year_dirs:

    dfs = []
    for year in year_dirs:
        year_dir = os.path.join(RAW_DIR, year)
        # Prefer merged yearly file
        if os.path.exists(merged):
            dfs.append(pd.read_parquet(merged))
            continue
        # fallback: 逐日 parquet
        parquet_files = sorted(
            f for f in os.listdir(year_dir)
        )
        if parquet_files:
            for f in parquet_files:
                dfs.append(pd.read_parquet(os.path.join(year_dir, f)))
        else:
            # fallback: CSV
            csv_files = sorted(f for f in os.listdir(year_dir)
            for f in csv_files:
                dfs.append(pd.read_csv(os.path.join(year_dir, f)))

    if not dfs:

    return pd.concat(dfs, ignore_index=True)


def load_raw_dividend(path: str | None = None) -> pd.DataFrame:

    主要來源: _yf_dividends.csv (已格式化: Date, Ticker, Cash_Dividend, Stock_Dividend)

    Args:
        path: 指定單一檔案；None 則掃描 RAW_DIR

    Returns:
        除權息 DataFrame
    if path:
        return pd.read_csv(path)

    # 讀取 _yf_dividends.csv
    if os.path.exists(div_file):
        df = pd.read_csv(div_file)
        # 清理: BOM, 空白
        return df

    # fallback: 掃描各年份的 exdiv CSV
    year_dirs = sorted(
        d for d in os.listdir(RAW_DIR)
        if d.isdigit() and os.path.isdir(os.path.join(RAW_DIR, d))
    )
    dfs = []
    for year in year_dirs:
        year_dir = os.path.join(RAW_DIR, year)
        for f in sorted(os.listdir(year_dir)):
                # exdiv format: Ticker, Close_ExDate — 日期從檔名取得
                date_str = f[:8]  # YYYYMMDD
                div_df = pd.read_csv(os.path.join(year_dir, f))
                dfs.append(div_df)

    if not dfs:

    return pd.concat(dfs, ignore_index=True)


def export_parquet(
    df: pd.DataFrame,
    *,
    output_dir: str = ADJ_DIR,
) -> str:

    Args:
        df: 含還原價格的 DataFrame (需有 Ticker,Date 欄位)
        output_dir: 輸出目錄
        compression: parquet 壓縮

    Returns:
        寫入的完整路徑
    os.makedirs(output_dir, exist_ok=True)

    df.to_parquet(out_path, compression=compression, index=False)

    return out_path


def read_adjusted(
    ticker: str | list[str] | None = None,
    *,
    data_dir: str = ADJ_DIR,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:

    Args:
        ticker: 股票代碼, None=全讀, str=單檔, list=多檔
        data_dir: parquet 根目錄

    Returns:
        DataFrame with Date index, Adj_OHLCV
    # ── 判斷格式：新式單一大檔 vs 舊式分區目錄 ──
    if os.path.exists(single_file):
        # 新式單一大檔：以 row-group filter 快速過濾
        if ticker is None:
            df = pd.read_parquet(single_file)
        elif isinstance(ticker, str):
        else:
            df = pd.read_parquet(
                single_file,
            )
    else:
        # 舊式分區目錄 (Ticker=XXX/*.parquet) 相容
        if ticker is None:
            df = pd.read_parquet(data_dir)
        elif isinstance(ticker, str):
        else:
            df = pd.concat(
                [pd.read_parquet(p) for p in parts],
                ignore_index=False,
            )

    # 確保 Date 為 datetime
        df.index = pd.to_datetime(df.index)
    else:

    if start_date:
        df = df[df.index >= start_date]
    if end_date:
        df = df[df.index <= end_date]

    return df.sort_index()


# ═══════════════════════════════════════════════════════════════
# 4. Pipeline
# ═══════════════════════════════════════════════════════════════

def _ensure_date_col(df: pd.DataFrame) -> pd.DataFrame:
        from datetime import datetime as _dt
        if isinstance(sample, (_dt, pd.Timestamp)):
        else:
    return df


def run_pipeline(
    *,
    daily_path: str | None = None,
    dividend_path: str | None = None,
    output_dir: str = ADJ_DIR,
) -> dict[str, int]:

    Args:
        daily_path: 日線 CSV/Parquet 路徑 (None=自動掃描 RAW_DIR)
        dividend_path: 除權息 CSV 路徑 (None=自動掃描 RAW_DIR)
        output_dir: parquet 輸出目錄

    Returns:
    raw_div = load_raw_dividend(dividend_path)
        div = clean_dividend_data(raw_div)
    else:
        div = raw_div.copy() if not raw_div.empty else raw_div
        _ensure_date_col(div)

    # ── 逐年掃描（避開一次載入 78M 行）──
    year_dirs = sorted(
        d for d in os.listdir(RAW_DIR)
        if d.isdigit() and os.path.isdir(os.path.join(RAW_DIR, d))
    )
    if not year_dirs:

    all_parts = []
    total_tickers: set[str] = set()
    for year in year_dirs:
        year_dir = os.path.join(RAW_DIR, year)
        if os.path.exists(merged):
            df = pd.read_parquet(merged)
        else:
            continue  # skip years without merged parquet

        _ensure_date_col(df)
        adj_part = calculate_adjusted_ohlcv(df, div)
        all_parts.append(adj_part)

    if not all_parts:

    adj = pd.concat(all_parts, ignore_index=True)
    del all_parts

    export_parquet(adj, output_dir=output_dir)

    return summary


    import argparse

    args = parser.parse_args()

    run_pipeline(
        daily_path=args.daily,
        dividend_path=args.dividend,
        output_dir=args.output,
    )
