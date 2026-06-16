"""
TWSE 量化資料載入層 — Data Access Layer
=========================================

功能：
    1. 從爬蟲 Raw/ 目錄讀取股票日線 (parquet)
    2. 套用 Backward Adjustment 還原權值
    3. Resample 日線 → 週線 / 月線
    4. yfinance 補償（爬蟲尚未爬到的資料）

依賴：
    pip install pandas numpy pyarrow yfinance

使用方式：
    from data_loader import TWSEStockLoader

    loader = TWSEStockLoader()
    daily = loader.load_daily("2330", adjusted=True)
    weekly = loader.resample_weekly(daily)
    monthly = loader.resample_monthly(daily)
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime
from typing import Literal, Optional

import numpy as np
import pandas as pd

# ── 路徑 ──────────────────────────────────────────────────────

DATA_DIR = os.environ.get("TWSE_DATA_DIR", "D:/TWSE-Data")
RAW_DIR = os.path.join(DATA_DIR, "Raw")
ADJ_DIR = os.path.join(DATA_DIR, "Adjusted")
ADJ_FILE = os.path.join(ADJ_DIR, "adjusted_all.parquet")


# ── Backward Adjustment ───────────────────────────────────────


def _calc_cumulative_factors(
    dates: np.ndarray,
    closes: np.ndarray,
    event_map: dict[pd.Timestamp, tuple[float, float]],
) -> np.ndarray:
    """計算 backward adjustment 的累積調整因子."""
    factors = np.ones(len(dates))
    date_idx = {pd.Timestamp(d): i for i, d in enumerate(dates)}
    for ex_date, (dividend, split_ratio) in event_map.items():
        if ex_date in date_idx:
            idx = date_idx[ex_date]
            if closes[idx] > 0:
                adj_factor = (closes[idx] + dividend) / closes[idx] / split_ratio
                factors[:idx] *= adj_factor
    return factors


def apply_backward_adjustment(
    df: pd.DataFrame,
    event_map: dict[pd.Timestamp, tuple[float, float]] | None = None,
) -> pd.DataFrame:
    """對 DataFrame 套用 Backward Adjustment.

    欄位需求: Date, Open, High, Low, Close, Volume
    輸出: 增加 Adj_Open, Adj_High, Adj_Low, Adj_Close, Adj_Volume
    """
    result = df.copy()
    if event_map is None:
        event_map = {}
    dates = result["Date"].values if "Date" in result.columns else result.index.values
    closes = result["Close"].values.astype(np.float64)
    factors = _calc_cumulative_factors(dates, closes, event_map)

    result["Adj_Close"] = result["Close"].values * factors
    result["Adj_Open"] = result["Open"].values * factors
    result["Adj_High"] = result["High"].values * factors
    result["Adj_Low"] = result["Low"].values * factors
    result["Adj_Volume"] = result["Volume"].values

    return result


# ── 股票資料載入器 ─────────────────────────────────────────────


class TWSEStockLoader:
    """TWSE 股票資料載入器.

    支援：
        - 從 Adjusted/all.parquet 載入（已還原權值）
        - 從 Raw/ 目錄載入原始資料並即時還原
        - 多時間框架 (日/週/月)
        - yfinance 補償（近期資料）
    """

    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self.raw_dir = os.path.join(data_dir, "Raw")
        self.adj_dir = os.path.join(data_dir, "Adjusted")
        self._adjusted_cache: pd.DataFrame | None = None
        self._stock_names: dict[str, str] = {}

    def load_daily(
        self,
        ticker: str,
        start: str | None = None,
        end: str | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame:
        """載入單一股票日線資料.

        Args:
            ticker: 股票代號 (如 "2330")
            start: 起始日期 (如 "2004-01-01")
            end: 結束日期 (如 "2026-12-31")
            adjusted: 是否使用還原權值

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume
            (if adjusted: also Adj_Open, Adj_High, Adj_Low, Adj_Close, Adj_Volume)
        """
        ticker = str(ticker).zfill(4)
        if self._adjusted_cache is None and os.path.exists(ADJ_FILE):
            self._adjusted_cache = pd.read_parquet(ADJ_FILE)
            self._adjusted_cache["Date"] = pd.to_datetime(self._adjusted_cache["Date"])
            self._adjusted_cache["Ticker"] = self._adjusted_cache["Ticker"].astype(str).str.zfill(4)

        df = None
        if adjusted and self._adjusted_cache is not None:
            sub = self._adjusted_cache[self._adjusted_cache["Ticker"] == ticker].copy()
            if not sub.empty:
                df = sub.sort_values("Date")

        if df is None or df.empty:
            df = self._load_from_raw(ticker, adjusted)

        if df is None or df.empty:
            df = self._load_from_yfinance(ticker)

        if df is None or df.empty:
            return pd.DataFrame()

        if start:
            df = df[df["Date"] >= start]
        if end:
            df = df[df["Date"] <= end]

        return df.reset_index(drop=True)

    def _load_from_raw(self, ticker: str, adjusted: bool = True) -> pd.DataFrame:
        """從 Raw/ 目錄載入原始資料."""
        raw_file = os.path.join(self.raw_dir, f"{ticker}.parquet")
        if not os.path.exists(raw_file):
            return pd.DataFrame()
        df = pd.read_parquet(raw_file)
        if df.empty:
            return df
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)
        if adjusted:
            df = apply_backward_adjustment(df)
        return df

    def _load_from_yfinance(self, ticker: str) -> pd.DataFrame:
        """從 yfinance 載入補償資料."""
        try:
            import yfinance as yf
            tw_stock = yf.Ticker(f"{ticker}.TW")
            hist = tw_stock.history(period="max")
            if hist.empty:
                return pd.DataFrame()
            hist = hist.reset_index()
            hist.columns = [c.replace(" ", "_") for c in hist.columns]
            hist["Date"] = pd.to_datetime(hist["Date"].dt.date)
            df = hist[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
            df = apply_backward_adjustment(df)
            return df
        except Exception:
            return pd.DataFrame()

    def load_multi_timeframe(
        self,
        ticker: str,
        start: str | None = None,
        end: str | None = None,
        adjusted: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """載入多時間框架資料 (日/週/月).

        Returns:
            {"daily": DataFrame, "weekly": DataFrame, "monthly": DataFrame}
        """
        daily = self.load_daily(ticker, start=start, end=end, adjusted=adjusted)
        if daily.empty:
            return {"daily": pd.DataFrame(), "weekly": pd.DataFrame(), "monthly": pd.DataFrame()}
        weekly = self.resample_weekly(daily)
        monthly = self.resample_monthly(daily)
        return {"daily": daily, "weekly": weekly, "monthly": monthly}

    @staticmethod
    def resample_weekly(daily: pd.DataFrame) -> pd.DataFrame:
        """日線 → 週線."""
        if daily.empty:
            return daily
        df = daily.set_index("Date")
        weekly = df.resample("W-FRI").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum",
        }).dropna()
        if "Adj_Open" in df.columns:
            adj_weekly = df.resample("W-FRI").agg({
                "Adj_Open": "first", "Adj_High": "max", "Adj_Low": "min",
                "Adj_Close": "last", "Adj_Volume": "sum",
            }).dropna()
            weekly = weekly.join(adj_weekly)
        weekly = weekly.reset_index()
        weekly.columns = [c.replace(" ", "_") for c in weekly.columns]
        return weekly

    @staticmethod
    def resample_monthly(daily: pd.DataFrame) -> pd.DataFrame:
        """日線 → 月線."""
        if daily.empty:
            return daily
        df = daily.set_index("Date")
        monthly = df.resample("ME").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum",
        }).dropna()
        if "Adj_Open" in df.columns:
            adj_monthly = df.resample("ME").agg({
                "Adj_Open": "first", "Adj_High": "max", "Adj_Low": "min",
                "Adj_Close": "last", "Adj_Volume": "sum",
            }).dropna()
            monthly = monthly.join(adj_monthly)
        monthly = monthly.reset_index()
        monthly.columns = [c.replace(" ", "_") for c in monthly.columns]
        return monthly

    def list_available_tickers(self, adjusted_only: bool = True) -> list[str]:
        """列出所有可用股票代號."""
        if adjusted_only and os.path.exists(ADJ_FILE):
            if self._adjusted_cache is None:
                self._adjusted_cache = pd.read_parquet(ADJ_FILE)
                self._adjusted_cache["Ticker"] = self._adjusted_cache["Ticker"].astype(str).str.zfill(4)
            return sorted(self._adjusted_cache["Ticker"].unique())
        raw_files = []
        if os.path.exists(self.raw_dir):
            raw_files = [f.replace(".parquet", "") for f in os.listdir(self.raw_dir)
                         if f.endswith(".parquet")]
        return sorted(raw_files)

    def get_stock_name(self, ticker: str) -> str:
        """取得股票中文名稱."""
        ticker = str(ticker).zfill(4)
        if ticker in self._stock_names:
            return self._stock_names[ticker]
        try:
            import yfinance as yf
            tw = yf.Ticker(f"{ticker}.TW")
            info = tw.info
            name = info.get("longName") or info.get("shortName") or ticker
            if name and name != ticker:
                self._stock_names[ticker] = str(name)
                return str(name)
        except Exception:
            pass
        self._stock_names[ticker] = ticker
        return ticker


# ── 快速測試 ──────────────────────────────────────────────────


def _demo() -> None:
    loader = TWSEStockLoader()
    tickers = ["2330", "2454", "2317"]
    for t in tickers:
        tf = loader.load_multi_timeframe(t)
        print(f"\n{t} {loader.get_stock_name(t)}")
        print(f"  日線: {len(tf['daily'])} rows")
        print(f"  週線: {len(tf['weekly'])} rows")
        print(f"  月線: {len(tf['monthly'])} rows")


if __name__ == "__main__":
    _demo()
