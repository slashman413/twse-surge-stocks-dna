"""Tests for the TWSE MI_INDEX backfill in code/ci_scan.py.

Run: python -m unittest discover -s tests   (no network needed)
"""
import copy
import json
import os
import sys
import unittest
import unittest.mock
from datetime import date

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "code"))
import ci_scan  # noqa: E402

with open(os.path.join(HERE, "fixtures", "mi_index_20261012.json"), encoding="utf-8") as f:
    FIXTURE = json.load(f)


def frame(days):
    idx = pd.DatetimeIndex(pd.to_datetime(days), name="Date")
    n = len(idx)
    return pd.DataFrame({"Close": [1.0] * n, "High": [1.0] * n, "Low": [1.0] * n,
                         "Open": [1.0] * n, "Volume": [1.0] * n}, index=idx)


TWII_DAYS = ["2026-10-06", "2026-10-07", "2026-10-08", "2026-10-12", "2026-10-13"]
YAHOO_DAYS = ["2026-10-06", "2026-10-07", "2026-10-08", "2026-10-13"]   # 10-12 hole


class ParseMiIndex(unittest.TestCase):
    def test_parses_ohlcv(self):
        rows = ci_scan.parse_mi_index(FIXTURE)
        self.assertEqual(rows["2330"], {"Open": 2510.0, "High": 2550.0, "Low": 2510.0,
                                        "Close": 2540.0, "Volume": 23555768.0})
        self.assertEqual(rows["2009"]["Close"], 40.55)

    def test_skips_untraded_rows(self):
        payload = copy.deepcopy(FIXTURE)
        table = next(t for t in payload["tables"] if "證券代號" in (t["fields"] or []))
        row = list(table["data"][0])
        row[0] = "9999"
        for i in range(5, 9):
            row[i] = "--"
        table["data"].append(row)
        self.assertNotIn("9999", ci_scan.parse_mi_index(payload))

    def test_no_data_stat(self):
        self.assertEqual(ci_scan.parse_mi_index({"stat": "很抱歉，沒有符合條件的資料!"}), {})


class FetchStockData(unittest.TestCase):
    def test_drops_rows_with_an_empty_close(self):
        raw = frame(TWII_DAYS)
        raw.loc["2026-10-13", "Close"] = float("nan")
        with unittest.mock.patch.object(ci_scan.yf, "download", return_value=raw):
            df = ci_scan.fetch_stock_data("2330")
        self.assertEqual(df.index[-1], pd.Timestamp("2026-10-12"))


class DropHolidayRows(unittest.TestCase):
    def test_drops_only_zero_volume_rows_on_non_trading_days(self):
        df = frame(TWII_DAYS + ["2026-10-14", "2026-10-15"])
        df.loc["2026-10-08", "Volume"] = 0.0   # untraded on a real session: kept
        df.loc["2026-10-14", "Volume"] = 0.0   # holiday placeholder: dropped
        out = ci_scan.drop_holiday_rows(df, pd.DatetimeIndex(TWII_DAYS))
        self.assertEqual(list(out.index.strftime("%Y-%m-%d")), TWII_DAYS + ["2026-10-15"])


class BackfillMissingDays(unittest.TestCase):
    def test_fills_hole_from_twse(self):
        calls = []

        def fake_fetch(d):
            calls.append(d)
            return ci_scan.parse_mi_index(FIXTURE)

        data = {"2330": frame(YAHOO_DAYS), "2009": frame(YAHOO_DAYS)}
        added = ci_scan.backfill_missing_days(data, pd.DatetimeIndex(TWII_DAYS), fetch=fake_fetch)
        self.assertEqual(added, 2)
        self.assertEqual(calls, [date(2026, 10, 12)])          # one call per date
        df = data["2330"]
        self.assertTrue(df.index.is_monotonic_increasing)
        self.assertEqual(df.loc["2026-10-12", "Close"], 2540.0)
        self.assertEqual(list(df.columns), ["Close", "High", "Low", "Open", "Volume"])

    def test_no_holes_no_calls(self):
        data = {"2330": frame(TWII_DAYS)}
        added = ci_scan.backfill_missing_days(
            data, pd.DatetimeIndex(TWII_DAYS), fetch=lambda d: self.fail("fetched"))
        self.assertEqual(added, 0)

    def test_window_limits_lookback(self):
        data = {"2330": frame(["2026-10-01"] + YAHOO_DAYS)}
        twii = pd.DatetimeIndex(["2026-10-01", "2026-10-02"] + TWII_DAYS)   # 10-02 + 10-12 holes
        calls = []
        ci_scan.backfill_missing_days(data, twii, window=3, fetch=lambda d: calls.append(d) or {})
        self.assertEqual(calls, [date(2026, 10, 12)])

    def test_twse_failure_leaves_hole_and_never_raises(self):
        data = {"2330": frame(YAHOO_DAYS)}
        added = ci_scan.backfill_missing_days(data, pd.DatetimeIndex(TWII_DAYS), fetch=lambda d: None)
        self.assertEqual(added, 0)
        self.assertEqual(len(data["2330"]), len(YAHOO_DAYS))

        def boom(d):
            raise RuntimeError("network down")
        self.assertEqual(ci_scan.backfill_missing_days(data, pd.DatetimeIndex(TWII_DAYS), fetch=boom), 0)


if __name__ == "__main__":
    unittest.main()
