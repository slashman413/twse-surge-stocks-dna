import os, sys, time, json
import pandas as pd
import numpy as np
from indicators import macd, dmi, wr, rsi, k6k9, vr
from strategy import (
    BigStockBuySignalV2, BigStockSellSignalV2, _safe_last,
    TradeSignal, MarketState
)

os.makedirs(OUT_DIR, exist_ok=True)

# Load one year at a time
for year in range(2004, 2027):
    t0 = time.time()
    if not os.path.exists(f):
        continue

    # Load all stocks for this year at once
    df = pd.read_parquet(f)

    year_results = []

    for ticker in tickers:
        grp = df[mask].copy()

        # Pre-load
        daily = grp
        n = len(close)

        if n < 60:
            continue

        # Compute all indicators once (vectorized)
        close_s = pd.Series(close, index=range(n))
        high_s = pd.Series(high, index=range(n))
        low_s = pd.Series(low, index=range(n))
        vol_s = pd.Series(volume, index=range(n))

        m = macd(close_s, fast=200, slow=209, signal=210)

        dm = dmi(high_s, low_s, close_s, period=300)

        wr50 = wr(high_s, low_s, close_s, 50).values
        rsi60 = rsi(close_s, 60).values
        rsi14 = rsi(close_s, 14).values
        ma60 = pd.Series(close).rolling(60).mean().values

        # Weekly

        w_vr = 0.0
        if len(weekly) > 2:
            w_denom = w_bvs.replace(0, np.nan)
            w_vr = (100.0 * w_avs / w_denom).iloc[-1] if not w_denom.empty else 0.0

        m_vr = 0.0
        if len(monthly) > 2:
            m_denom = m_bvs.replace(0, np.nan)
            m_vr = (100.0 * m_avs / m_denom).iloc[-1] if not m_denom.empty else 0.0

        m_pdi1 = 0.0
        m_rsi4 = 0.0
        if len(monthly) > 14:

        # Sample every 30 days
        step = 30
        buys = []
        sells = []
        for i in range(min(300, n), n, step):
            d4_latest = float(d4[i]) if i < len(d4) and not np.isnan(d4[i]) else 0
            adx_val = float(adx[i]) if i < len(adx) and not np.isnan(adx[i]) else 0
            adx_dir_val = float(adx_dir[i]) if i < len(adx_dir) else 0
            wr_val = float(wr50[i]) if i < len(wr50) and not np.isnan(wr50[i]) else 0
            rsi60_val = float(rsi60[i]) if i < len(rsi60) and not np.isnan(rsi60[i]) else 50

            met = []

            # C1: MACD 4 arrows >= 3
            if d4_latest >= 3:

            # C2: ADX300 arrow up
            adx300_up = adx_dir_val >= 0.5
            if adx300_up and adx_val > 20:

            # C3: WMS%R50 < -20
            if not np.isnan(wr_val) and wr_val < -20:

            # C4: RSI60 > 57
            if not np.isnan(rsi60_val) and rsi60_val > 57:

            # C5: Weekly VR2 ~150
            if not np.isnan(w_vr) and abs(w_vr - 150) < 50:
            # C6: Monthly VR2 ~150
            if not np.isnan(m_vr) and abs(m_vr - 150) < 50:
            # C7: Monthly +DI1>50 & RSI4>77
            if m_pdi1 > 50 and m_rsi4 > 77:

            # Buy: need C1-C3
            c1 = d4_latest >= 3
            c2 = adx300_up and adx_val > 20
            c3 = not np.isnan(wr_val) and wr_val < -20
            if c1 and c2 and c3:
                if bonus >= 1:

            # Sell: monthly RSI4 < 77
            if not np.isnan(m_rsi4) and m_rsi4 < 77:

        if buys or sells:

    elapsed = time.time() - t0

