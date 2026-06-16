TWSE 資料爬蟲 — 台灣證券交易所資料抓取模組
============================================

策略：
  ⚠️ 每次請求後隨機 sleep 2~5 分鐘，避免 IP 被封鎖
  ⚠️ 支援 retry + exponential backoff
  ⚠️ 僅交易日才發請求（skip 週末）

API 格式 (2025+)：
  MI_INDEX 資料在 response['tables'][8]（每日收盤行情全部）
  除權息標記在 漲跌(+/-) 欄位 = '<p>X</p>'

儲存路徑：
  Raw/{year}/                    — 每年分目錄
    {YYYYMMDD}_daily.parquet     — 該日全市場 OHLCV
    {YYYYMMDD}_exdiv.csv         — 該日除權息標記清單
  Raw/_progress.json             — 進度檔 (支援中斷續爬)

使用方法：
    python twse_crawler.py --year 2026
    python twse_crawler.py --year-range 2004 2026

from __future__ import annotations

import json
import os
import random
import sys
import time
import logging
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import requests

# ── 設定 ──────────────────────────────────────────────────────

TWSE_DAILY_URL = (
)

# 請求間隔（秒）
REQ_SLEEP_MIN = 2    # 2 秒
REQ_SLEEP_MAX = 5   # 5 秒

# Retry
MAX_RETRIES = 3
BACKOFF_BASE = 30

# User-Agent 池
USER_AGENTS = [
]

logging.basicConfig(
    level=logging.INFO,
    force=True,
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)


# ── 工具函式 ──────────────────────────────────────────────────

def _random_ua() -> dict[str, str]:


def _is_trading_day(d: date) -> bool:
    return d.weekday() < 5


def _sleep(secs: int | tuple[int, int] | None = None):
    if secs is None:
        secs = random.randint(REQ_SLEEP_MIN, REQ_SLEEP_MAX)
    elif isinstance(secs, tuple):
        secs = random.randint(*secs)
    if secs > 0:
        _secs = secs
        mins, sec_remain = divmod(_secs, 60)
        time.sleep(_secs)


def _fmt_date(d: date) -> str:


def _request_with_retry(url: str) -> dict[str, Any] | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=_random_ua(), timeout=60)
            resp.raise_for_status()
            data = resp.json()
                return None
            return data
        except Exception as e:
            if attempt < MAX_RETRIES:
                backoff = BACKOFF_BASE * (2 ** (attempt - 1))
                time.sleep(backoff)
            else:
                return None
    return None


# ── 解析 MI_INDEX ────────────────────────────────────────────
#
# 新格式 (2025+)：資料在 response['tables'][8]
#   fields: [證券代號, 證券名稱, 成交股數, 成交筆數, 成交金額,
#            開盤價, 最高價, 最低價, 收盤價, 漲跌(+/-), 漲跌價差, ...]
#   漲跌(+/-) = '<p>X</p>' 代表當日為除權息日

DAILY_FIELDS = {
}


def _parse_daily_table(table: dict[str, Any], d: date) -> pd.DataFrame:

    if not rows:
        return pd.DataFrame()

    # 建立欄位 index
    col_idx: dict[str, int] = {}
    for i, f in enumerate(fields):
        col_idx[f.strip()] = i

    needed = list(DAILY_FIELDS.keys())
    if any(c not in col_idx for c in needed):
        missing = [c for c in needed if c not in col_idx]
        return pd.DataFrame()

    records = []
    for row in rows:
        for cn, en in DAILY_FIELDS.items():
            val = row[col_idx[cn]]
            rec[en] = val
        # 除權息標記
        records.append(rec)

    df = pd.DataFrame(records)

    # 數值清洗
        df[col] = (
            df[col]
            .astype(str)
        )
        .astype(str)
    )

    return df


def _extract_exdiv_list(df: pd.DataFrame, d: date) -> pd.DataFrame | None:
    if exdiv.empty:
        return None


# ── 單日爬取 ──────────────────────────────────────────────────

def fetch_one_day(d: date, *, save: bool = True) -> dict[str, Any]:

    每次請求後隨機 sleep 2~5 分鐘。

    Args:
        d: 日期
        save: 是否存檔

    Returns:

    date_str = _fmt_date(d)
    url = TWSE_DAILY_URL.format(date_str=date_str)

    data = _request_with_retry(url)
    if data is None:
        return result

    if len(tables) < 9:
        return result

    df = _parse_daily_table(tables[8], d)
    if df.empty:
        return result


    # 儲存日線
    if save:
        year_dir = os.path.join(RAW_DIR, str(d.year))
        os.makedirs(year_dir, exist_ok=True)


    # 除權息清單
    exdiv = _extract_exdiv_list(df, d)
    if exdiv is not None and not exdiv.empty:
        if save:
    else:

    return result


# ── 年度爬取 ──────────────────────────────────────────────────

def fetch_year(
    year: int,
    *,
    progress_file: str | None = None,
) -> dict[str, Any]:

    Args:
        year: 西元年份 (2004~2026)
        progress_file: 進度 JSON 路徑 (支援續爬)

    Returns:
        統計摘要
    # 載入進度
    completed_dates: set[str] = set()
    if progress_file and os.path.exists(progress_file):
        try:
            with open(progress_file) as f:
                prog = json.load(f)
        except Exception:
            pass

    start = date(year, 1, 1)
    end = date(year, 12, 31)
    if end > date.today():
        end = date.today()

    total_days = 0
    total_rows = 0
    exdiv_events = 0
    year_dir = os.path.join(RAW_DIR, str(year))
    os.makedirs(year_dir, exist_ok=True)

    current = start
    while current <= end:
        date_str = _fmt_date(current)

        # 跳過已完成的
        if date_str in completed_dates:
            current += timedelta(days=1)
            continue

        # 跳過週末
        if not _is_trading_day(current):
            current += timedelta(days=1)
            continue

        result = fetch_one_day(current)

            total_days += 1
            completed_dates.add(date_str)

            # 更新進度
            if progress_file:
                try:
                        json.dump({
                        }, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

        # 跨日 sleep (每次請求後)
        _sleep()

        current += timedelta(days=1)

    return {
    }


def year_is_complete(year: int, progress_file: str) -> bool:
    if not os.path.exists(progress_file):
        return False
    try:
        with open(progress_file) as f:
            prog = json.load(f)
    except Exception:
        return False
        return False

    # 計算該年交易日數（到今天的粗略值）
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    if end > date.today():
        end = date.today()
    trading_days = sum(1 for i in range((end - start).days + 1)
                       if (start + timedelta(days=i)).weekday() < 5)


# ── 年度區間爬取（含跨年 sleep）───────────────────────────────

YEAR_SLEEP_MIN = 10   # 10 秒
YEAR_SLEEP_MAX = 30  # 30 秒


def fetch_year_range(
    start_year: int,
    end_year: int,
    *,
    sleep_between: tuple[int, int] = (YEAR_SLEEP_MIN, YEAR_SLEEP_MAX),
) -> list[dict[str, Any]]:

    Args:
        start_year: 起始年 (e.g. 2004)
        end_year: 截止年 (e.g. 2026)
        sleep_between: 年度之間的 sleep 範圍 (秒)

    Returns:
        各年統計摘要列表
    results = []

    for year in range(start_year, end_year + 1):


        # 檢查是否已完整
        if year_is_complete(year, progress_file):
            # Load previous result
            try:
                with open(progress_file) as f:
                    prog = json.load(f)
                results.append({
                })
            except Exception:

            # 仍要跨年 sleep
            if year < end_year:
                _sleep(sleep_between)
            continue

        result = fetch_year(year, progress_file=progress_file)
        results.append(result)


        # 跨年 sleep（4~10 分鐘）
        if year < end_year:
            _sleep(sleep_between)

    return results


# ── 合併年度資料 ──────────────────────────────────────────────

def merge_year(year: int) -> dict[str, str | int]:

    Returns:
    year_dir = os.path.join(RAW_DIR, str(year))
    if not os.path.isdir(year_dir):


    # 合併日線
    daily_files = sorted(f for f in os.listdir(year_dir)
    if daily_files:
        dfs = []
        for f in daily_files:
            dfs.append(pd.read_parquet(os.path.join(year_dir, f)))
        all_df = pd.concat(dfs, ignore_index=True)
        all_df.to_parquet(merged_path, index=False)

    # 合併除權息
    exdiv_files = sorted(f for f in os.listdir(year_dir)
    if exdiv_files:
        dfs = []
        for f in exdiv_files:
            dfs.append(pd.read_csv(os.path.join(year_dir, f)))
        all_exdiv = pd.concat(dfs, ignore_index=True)

    return result


def merge_all_years() -> dict[str, str | int]:
    daily_parts = []
    exdiv_parts = []

    for y in sorted(os.listdir(RAW_DIR)):
        if not y.isdigit():
            continue
        year_dir = os.path.join(RAW_DIR, y)
        if os.path.exists(daily_path):
            daily_parts.append(pd.read_parquet(daily_path))
        if os.path.exists(exdiv_path):
            exdiv_parts.append(pd.read_csv(exdiv_path))

    result: dict[str, str | int] = {}

    if daily_parts:
        full = pd.concat(daily_parts, ignore_index=True)
        full.to_parquet(path, index=False)

    if exdiv_parts:
        full = pd.concat(exdiv_parts, ignore_index=True)

    return result


# ── CLI ───────────────────────────────────────────────────────

    import argparse

    args = parser.parse_args()

    if args.merge is not None:
        if args.merge == -1:
            # merge all years individually
            for y in sorted(os.listdir(RAW_DIR)):
                if y.isdigit():
                    merge_year(int(y))
        else:
            merge_year(args.merge)
    elif args.merge_all:
        merge_all_years()
    elif args.year:
        fetch_year(args.year,
        merge_year(args.year)
    elif args.year_range:
        results = fetch_year_range(*args.year_range)
        # 合併各年
        for r in results:
            try:
            except Exception as e:
        merge_all_years()
    else:
        parser.print_help()
