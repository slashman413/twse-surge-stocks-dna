#!/usr/bin/env python3
Goodinfo 股利資料輔助爬蟲 v1
================================
用途：補足 yfinance 缺少的 TWSE 早期除權息資料
方式：透過瀏覽器渲染 Goodinfo 股利政策頁，提取 divDetail 中的歷年股利表

限制：需有 Hermes browser 工具；每次只能查一檔；約需 10-20 秒/檔

輸出：CSV 格式 (Date, Ticker, Cash_Dividend, Stock_Dividend)

import re, sys, argparse, csv, io
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# 從 divDetail 文字中解析股利資料 (Goodinfo 格式)
# ═══════════════════════════════════════════════════════════════

def parse_goodinfo_dividend(text: str, ticker: str) -> list[dict]:

    Goodinfo 格式範例 (每年一行):
        2004	2003	0.604	0	0.604	1.409	0	1.409	2.012	109	109
        ↑      ↑      ↑      ↑  ↑     ↑      ↑  ↑     ↑     ↑   ↑
        發放年 所屬年  現金股利 ... 股票股利 ...  合計  填息天 填權天

    Returns:
        [{Date, Ticker, Cash_Dividend, Stock_Dividend}, ...]
    results = []
    # 每行: 年份開頭，有 tab 分隔
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) < 11:
            continue
        # 第1欄必須是4位數年份
        pay_year_str = parts[0].strip()
        if not re.match(r'^\d{4}$', pay_year_str):
            continue

        try:
            pay_year = int(pay_year_str)
            own_year = int(parts[1].strip()) if parts[1].strip().isdigit() else pay_year - 1
            cash_div = float(parts[2].strip()) if parts[2].strip().replace('.', '', 1).replace('-', '', 1).isdigit() else 0
            stock_div = float(parts[4].strip()) if parts[4].strip().replace('.', '', 1).replace('-', '', 1).isdigit() else 0
        except (ValueError, IndexError):
            continue

        # 只處理有股利的事件
        if cash_div == 0 and stock_div == 0:
            continue

        # 除權息日通常在 6~9 月，我們用 07-01 做標記 (實際日期需要更精確)
        # Goodinfo 表格不含精確日期
        results.append({
        })

    return results


# ═══════════════════════════════════════════════════════════════
# 整合到現有調整管線
# ═══════════════════════════════════════════════════════════════

def merge_with_existing(new_rows: list[dict], existing_csv: str = None) -> list[dict]:
    if not existing_csv:
        return new_rows

    import pandas as pd
    try:
        existing = pd.read_csv(existing_csv)
        # 將 new_rows 轉成 DataFrame
        new_df = pd.DataFrame(new_rows)

        # merge: Goodinfo 優先
        combined = pd.concat([existing, new_df], ignore_index=True)
    except Exception:
        return new_rows


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

    print()
