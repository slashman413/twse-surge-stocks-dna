"""
TWSE 技術指標計算模組
====================

提供 MACD, DMI, RSI, WR, VR, N2, 6K/9K 等技術指標。
所有函數皆支援 pandas Series 向量化運算。
"""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
import pandas as pd


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, pd.Series]:
    """MACD 計算.

    支援自訂週期，例如 macd(close, 200, 209, 210).

    Args:
        close: 收盤價序列
        fast: 快線 EMA 週期 (default 12)
        slow: 慢線 EMA 週期 (default 26)
        signal: 訊號線 EMA 週期 (default 9)

    Returns:
        {"macd": macd_line, "signal": signal_line, "histogram": histogram, "hist_diff": hist_diff}
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    hist_diff = histogram.diff()

    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram,
        "hist_diff": hist_diff,
    }


def macd_4arrows(
    close: pd.Series,
    fast: int = 200,
    slow: int = 209,
    signal: int = 210,
) -> dict[str, Any]:
    """MACD 四箭頭攻擊強度.

    箭頭定義：
        arrow0: MACD 柱狀圖 (histogram) > 0
        arrow1: MACD 柱狀圖持續增加 (histogram.diff() > 0)
        arrow2: DIF (macd_line) 向上 (macd_line.diff() > 0)
        arrow3: 訊號線 (signal_line) 向上 (signal_line.diff() > 0)

    Args:
        close: 收盤價序列
        fast: 快線週期
        slow: 慢線週期
        signal: 訊號線週期

    Returns:
        {
            "all_up": 四箭頭全上 (bool),
            "arrows_count": 箭頭數量 (0~4),
            "arrow0": 柱狀圖 > 0,
            "arrow1": 柱狀圖增加,
            "arrow2": DIF 向上,
            "arrow3": 訊號線向上,
            "macd": macd_line,
        }
    """
    m = macd(close, fast, slow, signal)
    hist = m["histogram"]
    macd_line = m["macd"]
    sig = m["signal"]

    arrow0 = hist > 0
    arrow1 = hist.diff() > 0
    arrow2 = macd_line.diff() > 0
    arrow3 = sig.diff() > 0

    arrows_count = arrow0.astype(int) + arrow1.astype(int) + arrow2.astype(int) + arrow3.astype(int)
    all_up = arrows_count >= 4

    return {
        "all_up": all_up,
        "arrows_count": arrows_count,
        "arrow0": arrow0,
        "arrow1": arrow1,
        "arrow2": arrow2,
        "arrow3": arrow3,
        "macd": macd_line,
    }


def dmi(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> dict[str, pd.Series]:
    """DMI 指標計算 (Directional Movement Index).

    含 +DI, -DI, ADX, ADXR。

    Args:
        high: 最高價序列
        low: 最低價序列
        close: 收盤價序列
        period: 週期 (default 14)

    Returns:
        {"plus_di": +DI, "minus_di": -DI, "adx": ADX, "adxr": ADXR}
    """
    high = high.astype(np.float64)
    low = low.astype(np.float64)
    close = close.astype(np.float64)

    # True Range
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)

    pos_mask = (up_move > down_move) & (up_move > 0)
    neg_mask = (down_move > up_move) & (down_move > 0)

    plus_dm[pos_mask] = up_move[pos_mask]
    minus_dm[neg_mask] = down_move[neg_mask]

    # Smoothed ATR
    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan)

    # ADX
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(span=period, adjust=False).mean()

    # ADXR
    adxr = (adx + adx.shift(period)) / 2

    return {
        "plus_di": plus_di,
        "minus_di": minus_di,
        "adx": adx,
        "adxr": adxr,
    }


def wr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """威廉指標 W%R (Williams %R).

    W%R = (最高價 - 收盤價) / (最高價 - 最低價) * -100

    Args:
        high: 最高價序列
        low: 最低價序列
        close: 收盤價序列
        period: 週期 (default 14)

    Returns:
        W%R 序列 (-100 ~ 0)
    """
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    denom = hh - ll
    denom = denom.replace(0, np.nan)
    return -100 * (hh - close) / denom


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI 計算 (Relative Strength Index).

    使用 Wilder 平滑法 (EMA with alpha=1/period)。

    Args:
        close: 收盤價序列
        period: 週期 (default 14)

    Returns:
        RSI 序列 (0~100)
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return rsi


def vr(
    close: pd.Series,
    volume: pd.Series | None = None,
    period: int = 2,
) -> dict[str, pd.Series]:
    """VR 量價指標 (Volume Ratio).

    VR = 上漲日成交量 / 下跌日成交量 * 100
    VR2 = 2 期平滑

    Args:
        close: 收盤價序列
        volume: 成交量序列 (可選，若 None 則以 1 代替)
        period: 平滑期數 (default 2)

    Returns:
        {"vr": VR, "vr2": VR2}
    """
    if volume is None:
        volume = pd.Series(1.0, index=close.index)

    up = close.diff() > 0
    down = close.diff() < 0

    avs = (volume * up).rolling(period).sum()
    bvs = (volume * down).rolling(period).sum()
    bvs = bvs.replace(0, np.nan)

    vr_series = 100 * avs / bvs
    vr2 = vr_series.rolling(2).mean()

    return {"vr": vr_series, "vr2": vr2}


def n2(
    high: pd.Series,
    low: pd.Series,
    period: int = 42,
) -> pd.Series:
    """N2 指標：近 N 期高低點平均.

    N2 = (近 N 期最高 + 近 N 期最低) / 2

    Args:
        high: 最高價序列
        low: 最低價序列
        period: 期數 (default 42 = 約 2 個月)

    Returns:
        N2 序列
    """
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    return (hh + ll) / 2


def _is_doji(open_p: float, close_p: float, threshold_pct: float = 0.1) -> bool:
    """判斷是否為十字K線 (Doji).

    實體 < 範圍的 threshold_pct %.
    """
    if open_p == 0 or close_p == 0:
        return False
    body = abs(close_p - open_p)
    range_p = abs(close_p - open_p) / max(open_p, close_p) * 100
    if open_p == close_p:
        return True
    return range_p < threshold_pct


def _is_inside_bar_v2(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    open_p: pd.Series | None = None,
    lookback: int = 3,
) -> pd.Series:
    """判斷是否為 Inside Bar v2.

    條件：
        - 今天最高 < 前一日最高
        - 今天最低 > 前一日最低
        - 連續 lookback 根 K 線的實體逐漸縮小

    Args:
        high: 最高價序列
        low: 最低價序列
        close: 收盤價序列
        open_p: 開盤價序列 (可選)
        lookback: 回溯期數

    Returns:
        布林序列
    """
    inside = (high < high.shift(1)) & (low > low.shift(1))
    if lookback > 1 and open_p is not None:
        body = (close - open_p).abs()
        shrinking = body < body.shift(1)
        for i in range(1, lookback):
            shrinking = shrinking & (body.shift(i - 1) < body.shift(i))
        return inside & shrinking
    return inside


def k6k9(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    open_p: pd.Series | None = None,
) -> dict[str, Any]:
    """6K/9K 理論 — K 線組合訊號.

    上漲型 (UP):
        - UP_6K: 連續 6 根紅K (收 > 開)
        - UP_6K_300: 6 根紅K且累積 > 300 點
        - UP_9K: 連續 9 根紅K
    下跌型 (DOWN):
        - DOWN_6K: 連續 6 根黑K (收 < 開)
        - DOWN_6K_300: 6 根黑K且累積跌幅 > 300 點
        - DOWN_9K: 連續 9 根黑K

    十字K線 (Doji) 合併規則：
        - 十字K與前一根方向相同則合併

    Args:
        high: 最高價序列
        low: 最低價序列
        close: 收盤價序列
        open_p: 開盤價序列 (可選，預設使用 close.shift(1) 估算)

    Returns:
        {
            "signal": 是否觸發訊號 (bool),
            "signal_type": 訊號類型 (str),
            "count": 連續紅/黑K 根數,
            "type": "red" 或 "black",
        }
    """
    if open_p is None:
        open_p = close.shift(1).fillna(method="bfill")

    # 判斷紅K (收 > 開) 和黑K (收 < 開)
    is_red = close > open_p
    is_black = close < open_p

    # 十字K處理：與前一根方向相同則合併
    doji = _is_doji_vec(open_p, close)
    for i in range(1, len(is_red)):
        if doji.iloc[i]:
            if i > 0:
                is_red.iloc[i] = is_red.iloc[i - 1]
                is_black.iloc[i] = is_black.iloc[i - 1]

    # 計算連續紅/黑K
    red_streak = _calc_streak(is_red)
    black_streak = _calc_streak(is_black)

    # 累積漲跌幅
    cum_change = close.diff().rolling(6).sum()

    result = pd.Series(index=close.index, dtype=object)
    signal_type = pd.Series(index=close.index, dtype=object)
    result_count = pd.Series(0, index=close.index, dtype=int)
    result_type = pd.Series("", index=close.index, dtype=object)

    # 上漲型訊號
    up6 = red_streak >= 6
    up6_300 = up6 & (cum_change > 300)
    up9 = red_streak >= 9

    result[up6] = True
    signal_type[up6] = "UP_6K"
    result_count[up6] = red_streak[up6]
    result_type[up6] = "red"

    result[up6_300] = True
    signal_type[up6_300] = "UP_6K_300"
    result_count[up6_300] = red_streak[up6_300]
    result_type[up6_300] = "red"

    result[up9] = True
    signal_type[up9] = "UP_9K"
    result_count[up9] = red_streak[up9]
    result_type[up9] = "red"

    # 下跌型訊號
    down6 = black_streak >= 6
    down6_300 = down6 & (cum_change < -300)
    down9 = black_streak >= 9

    result[down6] = True
    signal_type[down6] = "DOWN_6K"
    result_count[down6] = black_streak[down6]
    result_type[down6] = "black"

    result[down6_300] = True
    signal_type[down6_300] = "DOWN_6K_300"
    result_count[down6_300] = black_streak[down6_300]
    result_type[down6_300] = "black"

    result[down9] = True
    signal_type[down9] = "DOWN_9K"
    result_count[down9] = black_streak[down9]
    result_type[down9] = "black"

    return {
        "signal": result,
        "signal_type": signal_type,
        "count": result_count,
        "type": result_type,
        "red_streak": red_streak,
        "black_streak": black_streak,
    }


def _is_doji_vec(open_p: pd.Series, close_p: pd.Series, threshold_pct: float = 0.1) -> pd.Series:
    """向量化判斷十字K線."""
    body = (close_p - open_p).abs()
    avg = (open_p + close_p) / 2
    pct = body / avg.replace(0, np.nan) * 100
    return pct < threshold_pct


def _calc_streak(condition: pd.Series) -> pd.Series:
    """計算連續滿足條件的天數.

    Args:
        condition: 布林序列

    Returns:
        連續天數序列
    """
    streak = condition.astype(int).groupby(
        (condition != condition.shift(1)).cumsum()
    ).cumsum()
    return streak * condition


def _demo() -> None:
    """快速測試所有指標 (範例)."""
    np.random.seed(42)
    n = 500
    dates = pd.date_range("2020-01-01", periods=n, freq="D")
    close = 100 + np.cumsum(np.random.randn(n) * 2)
    high = close + np.abs(np.random.randn(n))
    low = close - np.abs(np.random.randn(n))
    volume = np.random.randint(1000, 10000, n)
    open_p = close - np.random.randn(n)

    df = pd.DataFrame({
        "Close": close, "High": high, "Low": low,
        "Volume": volume, "Open": open_p,
    }, index=dates)

    print(f"MACD: {macd(df['Close'])}")
    print(f"MACD 4 Arrows: {macd_4arrows(df['Close'])}")
    print(f"DMI: {dmi(df['High'], df['Low'], df['Close'])}")
    print(f"W%R: {wr(df['High'], df['Low'], df['Close'])}")
    print(f"RSI: {rsi(df['Close'])}")
    print(f"VR: {vr(df['Close'], df['Volume'])}")
    print(f"N2: {n2(df['High'], df['Low'])}")
    print(f"6K/9K: {k6k9(df['High'], df['Low'], df['Close'], df['Open'])}")


if __name__ == "__main__":
    _demo()
