"""
CI Daily Scan — full market, v12-style signals, live K-line data
=================================================================
Uses yfinance only, no local data. Outputs:
  - docs/yearly_backtests/signals_data.json  — live daily signals
  - docs/yearly_backtests/live_kline.json    — K-line for top signals
  - docs/latest_scan.html                    — standalone scan report

Usage:
    python code/ci_scan.py
"""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime

import numpy as np
import pandas as pd
import yfinance as yf

# ── Paths ──────────────────────────────────────────────────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNALS_DIR = os.path.join(REPO_ROOT, "docs", "yearly_backtests")
SIGNALS_FILE = os.path.join(SIGNALS_DIR, "signals_data.json")
KLINE_FILE = os.path.join(SIGNALS_DIR, "live_kline.json")
HTML_FILE = os.path.join(REPO_ROOT, "docs", "latest_scan.html")
os.makedirs(SIGNALS_DIR, exist_ok=True)

# ── Comprehensive TWSE Stock List ──────────────────────────────
# ~430 liquid common stocks (4-digit, excluding 00-08 prefixes, ETFs, warrants)
TWSE_STOCKS = [
    # ── 半導體 ──
    "2330", "2454", "2303", "2344", "2408", "2449", "3034", "3035", "3189",
    "3221", "3257", "3260", "3374", "3406", "3443", "3529", "3530", "3532",
    "3563", "3583", "3588", "3624", "3645", "3661", "3679", "3680", "3707",
    "3714", "4919", "4952", "4961", "4966", "4968", "5234", "5269", "5285",
    "5347", "5483", "6104", "6116", "6139", "6147", "6191", "6202", "6223",
    "6231", "6239", "6243", "6257", "6261", "6271", "6286", "6415", "6423",
    "6435", "6451", "6456", "6462", "6488", "6515", "6531", "6533", "6552",
    "6568", "6573", "6585", "6625", "6640", "6643", "6651", "6667", "6669",
    "6679", "6683", "6690", "6695", "6706", "6719", "6728", "6732", "6735",
    "6742", "6756", "6768", "6770", "6789", "6799", "6805", "6807",
    # ── 電子零組件 ──
    "2317", "2308", "2324", "2327", "2328", "2347", "2356", "2357", "2360",
    "2368", "2376", "2382", "2385", "2392", "2395", "2402", "2404", "2413",
    "2415", "2421", "2428", "2431", "2436", "2442", "2450", "2451", "2455",
    "2457", "2460", "2464", "2467", "2477", "2478", "2480", "2485", "2489",
    "2492", "2495", "2497", "2498", "2499", "2504", "3013", "3017", "3023",
    "3026", "3029", "3032", "3037", "3041", "3042", "3044", "3045", "3050",
    "3054", "3055", "3059", "3060", "3062", "3090", "3231", "3413", "3416",
    "3432", "3444", "3450", "3454", "3481", "3494", "3501", "3504", "3515",
    "3518", "3526", "3528", "3535", "3545", "3548", "3550", "3557", "3561",
    "3576", "3587", "3591", "3596", "3605", "3607", "3617", "3628", "3646",
    "3653", "3665", "3669", "3673", "3689", "3694", "3701", "3702", "3704",
    "3705", "3706", "3712", "4106", "4915", "4916", "4930", "4935", "4938",
    "4942", "4943", "4956", "4958", "4967", "4977", "4989", "4994", "5007",
    "6112", "6115", "6117", "6120", "6121", "6125", "6128", "6133", "6142",
    "6150", "6153", "6155", "6165", "6176", "6184", "6189", "6196", "6201",
    "6205", "6206", "6208", "6209", "6213", "6214", "6215", "6217", "6220",
    "6224", "6225", "6230", "6245", "6277", "6282", "6285", "6412", "6414",
    # ── 金融 ──
    "2801", "2809", "2812", "2816", "2820", "2823", "2832", "2834", "2836",
    "2838", "2845", "2849", "2850", "2851", "2852", "2855", "2867", "2880",
    "2881", "2882", "2883", "2884", "2885", "2886", "2887", "2888", "2889",
    "2890", "2891", "2892", "2897", "5864", "5871", "5876", "5880",
    # ── 傳產龍頭 ──
    "1101", "1102", "1103", "1104", "1108", "1109", "1110", "1201", "1210",
    "1213", "1215", "1216", "1217", "1218", "1219", "1220", "1225", "1227",
    "1229", "1231", "1232", "1233", "1234", "1235", "1236", "1240", "1301",
    "1303", "1304", "1305", "1307", "1308", "1309", "1310", "1312", "1313",
    "1314", "1315", "1316", "1319", "1323", "1326", "1336", "1337", "1338",
    "1339", "1340", "1341", "1342", "1402", "1409", "1410", "1413", "1414",
    "1416", "1417", "1418", "1419", "1423", "1432", "1434", "1436", "1437",
    "1438", "1439", "1440", "1441", "1442", "1443", "1444", "1445", "1446",
    "1447", "1449", "1451", "1452", "1453", "1454", "1455", "1456", "1457",
    "1459", "1460", "1463", "1464", "1465", "1466", "1467", "1468", "1470",
    "1471", "1472", "1473", "1474", "1475", "1476", "1477", "1503", "1504",
    "1506", "1507", "1513", "1514", "1515", "1516", "1517", "1519", "1521",
    "1522", "1524", "1525", "1526", "1527", "1528", "1529", "1530", "1531",
    "1532", "1533", "1535", "1536", "1537", "1538", "1539", "1540", "1541",
    # ── 鋼鐵 ──
    "2002", "2006", "2007", "2008", "2009", "2010", "2012", "2013", "2014",
    "2015", "2017", "2020", "2022", "2023", "2024", "2025", "2027", "2028",
    "2029", "2030", "2031", "2032", "2033", "2034", "2038",
    # ── 航運 ──
    "2601", "2603", "2605", "2606", "2607", "2608", "2609", "2610", "2611",
    "2612", "2613", "2614", "2615", "2616", "2617", "2618", "2630", "2633",
    "2634", "2636", "2637", "2641", "2642", "2645",
    # ── 營建 ──
    "2501", "2504", "2505", "2509", "2511", "2514", "2515", "2516", "2520",
    "2524", "2526", "2527", "2528", "2530", "2534", "2535", "2536", "2537",
    "2538", "2539", "2540", "2542", "2543", "2545", "2546", "2547", "2548",
    "2596", "2597",
    # ── 汽車 ──
    "2201", "2204", "2206", "2207", "2208", "2227", "2228", "2231", "2233",
    "2236", "2239", "2241", "2243",
    # ── 資訊服務 ──
    "3029", "5203", "5210", "5211", "5212", "5213", "5215", "5222", "5227",
    "5230", "5287", "5299", "5406", "5410", "5438", "5469", "5471", "5484",
    "5487", "5490", "5498", "5508", "5511", "5512", "5514", "5515", "5519",
    "5520", "5521", "5522", "5523", "5525", "5531", "5533", "5534",
    # ── 高價/其他 ──
    "3008", "6409", "6416", "6417", "6426", "6431", "6438", "6446", "6457",
    "6472", "6477", "6485", "6491", "6492", "6496", "6504", "6505", "6510",
    "6525", "6526", "6534", "6541", "6550", "6558", "6560", "6578", "6579",
    "6581", "6591", "6592", "6598", "6605", "6606", "6624", "6631", "6637",
    "6641", "6649", "6655", "6657", "6658", "6664", "6666", "6668", "6670",
    "6671", "6672", "6680", "6684", "6689", "6691", "6692", "6698", "6703",
    "6712", "6715", "6716", "6721", "6724", "6733", "6737", "6739", "6743",
    "6747", "6753", "6757", "6761", "6762", "6763", "6765", "6767", "6771",
    "6776", "6781", "6782", "6788", "6792", "6794", "6796", "6799", "6804",
    "6806", "6808", "6811", "6813", "6815", "6816", "6817", "6818", "6820",
    "6821", "6823", "6826", "6830", "6831", "6834", "6835", "6838", "6841",
    "6843", "6844", "6845", "6846", "6847", "6850", "6854", "6855", "6856",
    "6861", "6863", "6869", "6870", "6873", "6875", "6877", "6879", "6881",
    "6885", "6886", "6890", "6894", "6895", "6899", "6901", "6902", "6904",
    "6906", "6910", "6913", "6914", "6915", "6916", "6918", "6919", "6921",
    "6922", "6923", "6924", "6925", "6926", "6928", "6929", "6930", "6931",
    "6932", "6933", "6935", "6936", "6937", "6938", "6939", "6940", "6941",
    "6944", "6945", "6946", "6947", "6949", "6950", "6951", "6952", "6953",
    "6955", "6956", "6957", "6958", "6959", "6960", "6961", "6963", "6965",
    "6966", "6967", "6968", "6970", "6971", "6972", "6973", "6975", "6976",
    "6977", "6978", "6980", "6981", "6983", "6984", "6985", "6986", "6990",
    "6991", "6992", "6993", "6994", "6995", "6996", "6997", "6998", "6999",
]

# Filter to 4-digit only (exclude delisted/invalid)
TWSE_STOCKS = sorted(set(t for t in TWSE_STOCKS if len(t) == 4 and t[:2] not in ('00','01','02','03','04','05','06','07','08')))

TOP_N = 30         # max signals in output
KLINE_DAYS = 120   # days of K-line per stock
PARALLEL = 6       # concurrent yfinance downloads


# ═══════════════════════════════════════════════════════════════
# Indicator helpers (standalone, no pandas dependency issues)
# ═══════════════════════════════════════════════════════════════

def safe_last(arr, default=0.0):
    if arr is None or (hasattr(arr, "empty") and arr.empty):
        return default
    vals = pd.Series(arr).dropna()
    return float(vals.iloc[-1]) if len(vals) > 0 else default


def macd_dif(close: pd.Series, fast=12, slow=26) -> pd.Series:
    return close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()


def macd_full(close: pd.Series, fast=12, slow=26, signal=9):
    dif = macd_dif(close, fast, slow)
    dea = dif.ewm(span=signal, adjust=False).mean()
    histogram = dif - dea
    return {"dif": dif, "dea": dea, "histogram": histogram}


def rsi(close: pd.Series, period=14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def dmi(high: pd.Series, low: pd.Series, close: pd.Series, period=14):
    h = high.values
    l = low.values
    c = close.values
    n = len(h)
    up = np.zeros(n)
    down = np.zeros(n)
    for i in range(1, n):
        up_ = h[i] - h[i-1]
        down_ = l[i-1] - l[i]
        if up_ > 0 and up_ > down_:
            up[i] = up_
        if down_ > 0 and down_ > up_:
            down[i] = down_
    tr = np.maximum(h - l, np.abs(h - np.roll(c, 1)))
    tr = np.maximum(tr, np.abs(l - np.roll(c, 1)))
    tr[tr <= 0] = np.nan
    atr = pd.Series(tr).ewm(span=period, adjust=False).mean().values
    up_ema = pd.Series(up).ewm(span=period, adjust=False).mean().values
    down_ema = pd.Series(down).ewm(span=period, adjust=False).mean().values
    pdi = up_ema / np.maximum(atr, 1e-10) * 100
    mdi = down_ema / np.maximum(atr, 1e-10) * 100
    dx = np.abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-10) * 100
    adx = pd.Series(dx).ewm(span=period, adjust=False).mean().values
    return {"adx": pd.Series(adx), "+di": pd.Series(pdi), "-di": pd.Series(mdi)}


def wr(high, low, close, period=14) -> pd.Series:
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    return (hh - close) / (hh - ll).replace(0, np.nan) * -100


# ═══════════════════════════════════════════════════════════════
# Market Assessment (v12-style: DIF210 + MACD四箭頭 + ADX300 + W%R50)
# ═══════════════════════════════════════════════════════════════

def assess_market(taiex: pd.DataFrame) -> dict:
    close = taiex["Close"]
    n = len(close)

    # DIF210 (parameters: fast=200, slow=209) — v12 market gate
    dif210 = macd_dif(close, fast=200, slow=209)
    dif210_now = safe_last(dif210, 0.0)

    # ADX 300 — trend strength
    dm = dmi(taiex["High"], taiex["Low"], close, period=300)
    adx300 = safe_last(dm["adx"], 0.0)

    # W%R 50 — oversold/overbought at market level
    wr50 = safe_last(wr(taiex["High"], taiex["Low"], close, period=50), -50.0)

    # RSI 60 — medium-term momentum
    rsi60_val = safe_last(rsi(close, 60), 50.0)

    # MACD四箭頭 (12,26,9)
    m = macd_full(close)
    dif_now = safe_last(m["dif"], 0.0)
    dif_prev = safe_last(m["dif"].shift(1), 0.0)
    hist_now = safe_last(m["histogram"], 0.0)
    hist_prev = safe_last(m["histogram"].shift(1), 0.0)

    score = 0
    arrows = 0
    reasons = []

    # DIF210 多空閘門
    if dif210_now > 0:
        score += 25
        reasons.append(f"DIF210={dif210_now:.0f}>0")
    else:
        reasons.append(f"DIF210={dif210_now:.0f}<0")

    # MACD四箭頭
    if dif_now > 0:
        arrows += 1
    if dif_now > dif_prev:
        arrows += 1
    if hist_now > 0:
        arrows += 1
    if hist_now > hist_prev:
        arrows += 1
    score += arrows * 8
    if arrows >= 3:
        score += 10
        reasons.append(f"MACD四箭頭={arrows}")

    # ADX300 趨勢強度
    if adx300 > 30:
        score += 15
        reasons.append(f"ADX300={adx300:.0f}")
    elif adx300 > 20:
        score += 5

    # W%R50
    if wr50 > -50:
        score += 10
        reasons.append(f"W%R50={wr50:.0f}")

    # RSI60
    if rsi60_val > 50:
        score += 10
        reasons.append(f"RSI60={rsi60_val:.0f}")
    if rsi60_val > 80:
        score -= 10
        reasons.append(f"RSI60過熱={rsi60_val:.0f}")

    market_bullish = score >= 40
    market_crash = dif210_now < -300 and rsi60_val < 35
    market_trend_up = dif_now > 0 and adx300 > 20

    return {
        "score": score,
        "arrows": arrows,
        "dif210": round(float(dif210_now), 1),
        "adx300": round(float(adx300), 1),
        "rsi60": round(float(rsi60_val), 1),
        "wr50": round(float(wr50), 1),
        "market_bullish": market_bullish,
        "market_crash": market_crash,
        "market_trend_up": market_trend_up,
        "reasons": reasons[:6],
        "taiex_close": safe_last(close, 0.0),
    }


# ═══════════════════════════════════════════════════════════════
# Stock Evaluation (v12-inspired: 8 conditions)
# ═══════════════════════════════════════════════════════════════

def evaluate_stock(ticker: str, df: pd.DataFrame, market: dict) -> dict | None:
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    n = len(close)

    if n < 200:
        return None

    # --- Indicators ---
    m = macd_full(close)
    dif_now = safe_last(m["dif"], 0.0)
    hist_now = safe_last(m["histogram"], 0.0)
    hist_prev = safe_last(m["histogram"].shift(1), 0.0)
    dif_slope = dif_now - safe_last(m["dif"].shift(3), dif_now)

    dm = dmi(high, low, close)
    adx = safe_last(dm["adx"], 0.0)
    pdi = safe_last(dm["+di"], 0.0)
    mdi = safe_last(dm["-di"], 0.0)

    rsi14 = safe_last(rsi(close, 14), 50.0)
    rsi60 = safe_last(rsi(close, 60), 50.0)

    wr14 = safe_last(wr(high, low, close, 14), -50.0)
    wr50 = safe_last(wr(high, low, close, 50), -50.0)

    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()

    close_now = safe_last(close, 0.0)
    ma20_now = safe_last(ma20, 0.0)
    ma50_now = safe_last(ma50, 0.0)
    ma200_now = safe_last(ma200, 0.0)

    dist_ma20 = (close_now - ma20_now) / ma20_now * 100 if ma20_now > 0 else 0
    dist_ma50 = (close_now - ma50_now) / ma50_now * 100 if ma50_now > 0 else 0
    dist_ma200 = (close_now - ma200_now) / ma200_now * 100 if ma200_now > 0 else 0

    vol_ma20 = volume.rolling(20).mean()
    vol_ratio = safe_last(volume / vol_ma20, 0.0)

    # --- MACD四箭頭 (daily) ---
    arrows = 0
    if dif_now > 0:
        arrows += 1
    if dif_slope > 0:
        arrows += 1
    if hist_now > 0:
        arrows += 1
    if hist_now > hist_prev:
        arrows += 1

    # --- Buy scoring (v12 inspired) ---
    buy_score = 0
    buy_details = []

    # 1. 大盤多頭閘門 (market gate)
    if market.get("market_bullish") and market.get("market_trend_up"):
        buy_score += 20
        buy_details.append("大盤多頭")

    # 2. MACD四箭頭
    buy_score += arrows * 6
    if arrows >= 3:
        buy_score += 8
        buy_details.append(f"MACD{arrows}箭")

    # 3. ADX > 20 (有趨勢)
    if adx > 20:
        buy_score += 8
        buy_details.append(f"ADX{adx:.0f}")

    # 4. +DI > -DI (多頭排列)
    if pdi > mdi:
        buy_score += 6

    # 5. 拉回MA20 (-3% ~ +1%) — v12 pullback entry
    if -3 < dist_ma20 < 1:
        buy_score += 15
        buy_details.append(f"拉回MA20")
    elif 1 <= dist_ma20 < 3:
        buy_score += 8
    elif dist_ma20 <= -3 and dist_ma20 > -6:
        buy_score += 5

    # 6. RSI14 30~60 (非過熱/非超賣)
    if 35 < rsi14 < 60:
        buy_score += 10
        buy_details.append(f"RSI{rsi14:.0f}")
    elif 30 <= rsi14 <= 35:
        buy_score += 5

    # 7. W%R 非過熱
    if wr14 < -20:
        buy_score += 5
    if wr50 < -30:
        buy_score += 5

    # 8. 價格在MA50之上 (中期多頭)
    if dist_ma50 > 0:
        buy_score += 5

    # 9. 成交量正常 or 擴增
    if vol_ratio > 0.5:
        buy_score += 3

    # --- Sell scoring ---
    sell_score = 0
    sell_details = []

    if dif_now < 0:
        sell_score += 15
        sell_details.append("MACD<0")
    if adx > 25 and mdi > pdi:
        sell_score += 12
        sell_details.append("DMI空頭")
        if adx > 30:
            sell_score += 5
            sell_details.append(f"ADX{adx:.0f}")
    if rsi14 > 75:
        sell_score += 10
        sell_details.append("RSI過熱")
    if wr14 > -20:
        sell_score += 8
        sell_details.append("W%R過熱")
    if dist_ma20 > 12:
        sell_score += 8
        sell_details.append("乖離過大")
    if dist_ma50 < -5:
        sell_score += 8
        sell_details.append("跌破MA50")

    # --- Decision (raised thresholds to filter marginal signals) ---
    is_buy = buy_score >= 55
    is_sell = sell_score >= 40

    if is_buy and not is_sell:
        quality = min(buy_score, 100)
        bonus = min(arrows, 4)
        signal = "BUY"
    elif is_sell and not is_buy:
        quality = min(sell_score, 100)
        bonus = 0
        signal = "SELL"
    else:
        return None

    return {
        "ticker": ticker,
        "name": "",
        "date": str(df.index[-1].date()) if isinstance(df.index[-1], pd.Timestamp) else str(df["Date"].iloc[-1].date()),
        "score": round(buy_score if is_buy else -sell_score, 1),
        "close": round(float(close_now), 2) if close_now == close_now else 0.0,
        "dist_ma20": round(dist_ma20, 2),
        "rsi14": round(rsi14, 2),
        "quality": quality,
        "bonus": bonus,
        "arrows": arrows,
        "signal": signal,
        "details": buy_details if is_buy else sell_details,
    }


# ═══════════════════════════════════════════════════════════════
# K-line builder (for dashboard modal)
# ═══════════════════════════════════════════════════════════════

def build_kline_data(ticker: str, df: pd.DataFrame) -> list[dict] | None:
    """Build K-line data in the format expected by dashboard openKline()."""
    close = df["Close"]
    open_ = df["Open"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    n = len(close)

    if n < 50:
        return None

    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    rsi14 = rsi(close, 14)
    dm = dmi(high, low, close)

    # Take last KLINE_DAYS
    start = max(0, n - KLINE_DAYS)
    result = []

    for i in range(start, n):
        d = df.index[i]
        if isinstance(d, pd.Timestamp):
            date_str = d.strftime("%Y-%m-%d")
        else:
            date_str = str(df["Date"].iloc[i].date()) if "Date" in df.columns else str(i)

        c = float(close.iloc[i])
        if c == 0 or (c != c):  # NaN check (NaN != NaN)
            continue

        row = {
            "d": date_str,
            "c": c,
            "o": float(open_.iloc[i]),
            "h": float(high.iloc[i]),
            "l": float(low.iloc[i]),
            "v": float(volume.iloc[i]),
            "ma20": round(float(ma20.iloc[i]), 2) if not pd.isna(ma20.iloc[i]) else None,
            "ma50": round(float(ma50.iloc[i]), 2) if not pd.isna(ma50.iloc[i]) else None,
            "rsi14": round(float(rsi14.iloc[i]), 1) if not pd.isna(rsi14.iloc[i]) else 50.0,
            "dist_ma20": round((c / ma20.iloc[i] - 1) * 100, 2) if ma20.iloc[i] > 0 else 0,
            "dist_ma50": round((c / ma50.iloc[i] - 1) * 100, 2) if ma50.iloc[i] > 0 else 0,
            "adx": round(float(dm["adx"].iloc[i]), 1) if not pd.isna(dm["adx"].iloc[i]) else 0,
            "pdi": round(float(dm["+di"].iloc[i]), 1) if not pd.isna(dm["+di"].iloc[i]) else 0,
            "mdi": round(float(dm["-di"].iloc[i]), 1) if not pd.isna(dm["-di"].iloc[i]) else 0,
        }
        result.append(row)

    return result[-KLINE_DAYS:] if len(result) > KLINE_DAYS else result


# ═══════════════════════════════════════════════════════════════
# Name lookup
# ═══════════════════════════════════════════════════════════════

def fetch_stock_data(ticker: str) -> pd.DataFrame | None:
    """Download 1 year of daily data for a single stock."""
    try:
        df = yf.download(f"{ticker}.TW", period="1y", auto_adjust=True, progress=False)
        if df.empty:
            return None
        # Flatten MultiIndex columns
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        return df
    except Exception:
        return None


def fetch_names(tickers: list[str]) -> dict[str, str]:
    """Fetch Chinese stock names in parallel."""
    names = {}
    def _get_name(t):
        try:
            tk = yf.Ticker(f"{t}.TW")
            info = tk.info
            n = info.get("longName") or info.get("shortName") or t
            names[t] = str(n)
        except Exception:
            names[t] = t
    with ThreadPoolExecutor(max_workers=PARALLEL) as ex:
        for t in tickers:
            ex.submit(_get_name, t)
    return names


# ═══════════════════════════════════════════════════════════════
# HTML Report Generator
# ═══════════════════════════════════════════════════════════════

def generate_html(output: dict, names: dict[str, str], scan_date: date):
    signals = output["signals"]
    market = output.get("market_assessment", output)

    market_status = "🟢 多頭" if market.get("market_bullish") else "🔴 空頭"
    market_color = "#22c55e" if market.get("market_bullish") else "#ef4444"
    if market.get("market_crash"):
        market_status = "💀 崩盤"
        market_color = "#dc2626"

    buy_rows = ""
    sell_rows = ""
    for s in signals:
        details_html = "<br>".join(
            f"<span style='color:#22c55e'>✅</span> {d}" for d in s.get("details", [])[:4]
        )
        rsi_str = str(round(s["rsi14"])) if isinstance(s.get("rsi14"), (int, float)) else str(s.get("rsi14", "?"))
        dist_str = f"{s['dist_ma20']:+.2f}%" if isinstance(s.get("dist_ma20"), (int, float)) else str(s.get("dist_ma20", "?"))

        if s["signal"] == "BUY":
            buy_rows += f"""
            <tr>
                <td style="font-weight:bold;color:#22c55e">{s['ticker']}</td>
                <td>{names.get(s['ticker'], s['ticker'])}</td>
                <td>{s.get('close', '?'):,.2f}</td>
                <td>{s['score']:.1f}</td>
                <td>{rsi_str}</td>
                <td>{dist_str}</td>
                <td style="font-size:0.8rem">{details_html}</td>
            </tr>"""
        else:
            sell_rows += f"""
            <tr>
                <td style="font-weight:bold;color:#ef4444">{s['ticker']}</td>
                <td>{names.get(s['ticker'], s['ticker'])}</td>
                <td>{s.get('close', '?'):,.2f}</td>
                <td>{s['score']:.1f}</td>
                <td>{rsi_str}</td>
                <td>{dist_str}</td>
                <td style="font-size:0.8rem">{details_html}</td>
            </tr>"""

    reasons_html = "".join(f"<li>{r}</li>" for r in market.get("reasons", [])[:5])
    buy_count = output.get("buy_count", signals.count({"signal": "BUY"}))
    sell_count = output.get("sell_count", signals.count({"signal": "SELL"}))

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TWSE 每日掃描 — {scan_date}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #0f172a; color: #e2e8f0; line-height: 1.6;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 4px; }}
  .subtitle {{ color: #94a3b8; font-size: 0.85rem; margin-bottom: 20px; }}
  .market-card {{
    padding: 16px; border-radius: 12px; margin-bottom: 16px;
    border: 1px solid #334155; background: #1e293b;
  }}
  .market-state {{
    display: inline-block; padding: 6px 16px; border-radius: 20px;
    color: white; font-weight: 700; font-size: 1.1rem;
  }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; background: #1e293b; border-radius: 12px; overflow: hidden; }}
  th {{ text-align: left; padding: 10px 12px; background: #334155; font-size: 0.8rem; text-transform: uppercase; color: #94a3b8; }}
  td {{ padding: 8px 12px; border-top: 1px solid #334155; font-size: 0.85rem; }}
  tr:hover {{ background: rgba(51,65,85,0.4); }}
  .section-title {{ font-size: 1.1rem; margin: 20px 0 4px; }}
  .footer {{ text-align: center; margin-top: 32px; padding: 16px; color: #475569; font-size: 0.75rem; }}
  .reasons {{ font-size: 0.85rem; color: #94a3b8; margin-top: 8px; }}
  .reasons li {{ margin-left: 16px; }}
</style>
</head>
<body>
<div class="container">
  <h1>📊 TWSE 量化每日掃描</h1>
  <div class="subtitle">{scan_date} ｜ 掃描 {output.get('scanned_count', 0)} 檔</div>

  <div class="market-card">
    <span class="market-state" style="background:{market_color}">{market_status}</span>
    <span style="margin-left:12px;font-size:0.9rem;color:#94a3b8;">
      加權指數: {market.get('taiex_close', 0):,.0f} ｜
      score: {market.get('score', 0)} ｜
      DIF210: {market.get('dif210', 0):.0f} ｜
      MACD四箭頭: {market.get('arrows', 0)} ｜
      ADX300: {market.get('adx300', 0):.0f}
    </span>
    <ol class="reasons">{reasons_html}</ol>
  </div>

  <h2 class="section-title" style="color:#22c55e">🟢 建議買進 ({output.get('buy_count', 0)}檔)</h2>
  <table>
    <tr><th>代號</th><th>名稱</th><th>收盤</th><th>評分</th><th>RSI14</th><th>乖離MA20</th><th>條件</th></tr>
    {buy_rows or '<tr><td colspan="7" style="text-align:center;color:#475569;padding:20px;">無符合條件的買進訊號</td></tr>'}
  </table>

  <h2 class="section-title" style="color:#ef4444;margin-top:24px;">🔴 建議賣出 ({output.get('sell_count', 0)}檔)</h2>
  <table>
    <tr><th>代號</th><th>名稱</th><th>收盤</th><th>評分</th><th>RSI14</th><th>乖離MA20</th><th>條件</th></tr>
    {sell_rows or '<tr><td colspan="7" style="text-align:center;color:#475569;padding:20px;">無符合條件的賣出訊號</td></tr>'}
  </table>

  <div class="footer">
    Generated by hermes-agent-deepseek-v4-flash · TWSE Quant Screener · {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
  </div>
</div>
</body>
</html>"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Saved HTML report to {HTML_FILE}")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    today = date.today()
    print(f"🔍 TWSE Daily Scan — {today}")
    print(f"    Stock list: {len(TWSE_STOCKS)} tickers")
    print(f"    Parallel workers: {PARALLEL}")

    # ── 1. Download market index ──
    print("\n📊 Downloading market index (^TWII)...")
    twii = yf.download("^TWII", period="3y", auto_adjust=True, progress=False)
    if twii.empty:
        print("❌ Failed to download ^TWII")
        sys.exit(1)
    twii.columns = [c[0] if isinstance(c, tuple) else c for c in twii.columns]

    market = assess_market(twii)
    print(f"    Market score: {market['score']} | {market['arrows']} arrows")
    print(f"    DIF210={market['dif210']:.0f} ADX300={market['adx300']:.0f}")
    print(f"    Bullish: {market['market_bullish']} | Trend: {market['market_trend_up']} | Crash: {market['market_crash']}")
    for r in market["reasons"]:
        print(f"      • {r}")

    # ── 2. Download stock data in parallel ──
    print(f"\n📈 Downloading {len(TWSE_STOCKS)} stocks from yfinance ({PARALLEL} workers)...")
    stocks_data = {}
    loaded = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=PARALLEL) as executor:
        future_map = {executor.submit(fetch_stock_data, t): t for t in TWSE_STOCKS}
        for i, future in enumerate(as_completed(future_map)):
            ticker = future_map[future]
            try:
                df = future.result()
                if df is not None and len(df) >= 200:
                    stocks_data[ticker] = df
                    loaded += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

            if (i + 1) % 50 == 0 or (i + 1) == len(TWSE_STOCKS):
                print(f"    Progress: {i+1}/{len(TWSE_STOCKS)} (loaded: {loaded}, failed: {failed})")

    print(f"    Loaded {loaded} stocks ({failed} skipped)")

    # ── 3. Evaluate signals ──
    print("\n🔍 Evaluating signals...")
    signals = []
    for ticker, df in stocks_data.items():
        sig = evaluate_stock(ticker, df, market)
        if sig:
            signals.append(sig)

    signals.sort(key=lambda s: s["score"], reverse=True)
    top_signals = signals[:TOP_N]
    buy_count = sum(1 for s in top_signals if s["signal"] == "BUY")
    sell_count = sum(1 for s in top_signals if s["signal"] == "SELL")
    print(f"    Total signals: {len(signals)} | Top {TOP_N}: {buy_count} BUY, {sell_count} SELL")

    # ── 4. Fetch names ──
    print("\n🏷️  Fetching stock names...")
    signal_tickers = [s["ticker"] for s in top_signals]
    names = fetch_names(signal_tickers)
    for s in top_signals:
        s["name"] = names.get(s["ticker"], s["ticker"])

    # ── 5. Build K-line data for top signals ──
    print("\n📉 Building K-line data for top signals...")
    kline_data = {}
    with ThreadPoolExecutor(max_workers=PARALLEL) as executor:
        future_map = {}
        for s in top_signals:
            t = s["ticker"]
            if t in stocks_data:
                future_map[executor.submit(build_kline_data, t, stocks_data[t])] = t
        for future in as_completed(future_map):
            t = future_map[future]
            try:
                kd = future.result()
                if kd and len(kd) >= 20:
                    kline_data[t] = {"kline": kd}
            except Exception:
                pass

    print(f"    K-line data for {len(kline_data)} stocks")

    # ── 6. Save signals_data.json ──
    output = {
        "date": today.isoformat(),
        "market_bullish": market["market_bullish"],
        "market_crash": market["market_crash"],
        "market_trend_up": market["market_trend_up"],
        "market_score": market["score"],
        "taiex_close": market["taiex_close"],
        "reasons": market["reasons"],
        "market_assessment": market,
        "scanned_count": loaded,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "signals": top_signals,
    }

    with open(SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved {len(top_signals)} signals to {SIGNALS_FILE}")

    # ── 7. Save live_kline.json ──
    # Clean NaN values from kline_data before serializing (NaN is invalid JSON)
    def _clean(obj):
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_clean(v) for v in obj]
        elif isinstance(obj, float):
            return 0.0 if (obj != obj) else obj  # NaN → 0.0
        return obj

    kline_data = _clean(kline_data)
    with open(KLINE_FILE, "w", encoding="utf-8") as f:
        json.dump(kline_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved K-line data ({len(kline_data)} stocks) to {KLINE_FILE}")

    # ── 8. Generate HTML report ──
    output["buy_count"] = buy_count
    output["sell_count"] = sell_count
    generate_html(output, names, today)

    print(f"\n✅ CI scan complete — {loaded} stocks, {len(signals)} signals, {len(kline_data)} K-lines")


if __name__ == "__main__":
    main()
