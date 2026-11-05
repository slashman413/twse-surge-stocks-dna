"""Tests for ci_update_signals.py. Run: python -m unittest discover -s tests   (no network needed)"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import ci_update_signals as ci  # noqa: E402

RWD_CSV = (
    "日期,證券代號,證券名稱,成交股數,成交金額,開盤價,最高價,最低價,收盤價,漲跌價差,成交筆數\n"
    '"1151105","1506","正道","160000","1494330","9.41","9.42","9.29","9.29","-0.1400","52"\n'
)


class FetchPrices(unittest.TestCase):
    def test_date_comes_from_the_rwd_file(self):
        with mock.patch.object(ci, "fetch_text", return_value=RWD_CSV):
            self.assertEqual(ci.fetch_prices(), ("2026-11-05", {"1506": 9.29}))

    def test_openapi_fallback_keeps_its_own_date(self):
        q = {"close": 9.43}
        with mock.patch.object(ci, "fetch_text", side_effect=OSError("down")), \
                mock.patch.object(ci, "stock_day_all", return_value=("1151104", {"1506": q})):
            self.assertEqual(ci.fetch_prices(), ("2026-11-04", {"1506": 9.43}))


class Main(unittest.TestCase):
    def run_main(self, session, prices, kline, date="2026-11-04"):
        sig = {"ticker": "1506", "date": date, "close": 9.0, "dist_ma20": 1.5, "rsi14": 55.0}
        with tempfile.TemporaryDirectory() as tmp:
            sig_file, kline_file = Path(tmp, "signals.json"), Path(tmp, "kline.json")
            sig_file.write_text(json.dumps({"date": date, "signals": [sig]}))
            kline_file.write_text(json.dumps(kline))
            with mock.patch.object(ci, "fetch_prices", return_value=(session, prices)), \
                    mock.patch.object(ci, "SIGNALS_FILE", sig_file), \
                    mock.patch.object(ci, "LIVE_KLINE", kline_file), \
                    mock.patch.object(ci.yf, "download", return_value=pd.DataFrame()):
                try:
                    ci.main()
                except SystemExit:
                    pass
            return json.loads(sig_file.read_text())

    def test_no_kline_keeps_indicators_and_signal(self):
        out = self.run_main("2026-11-05", {"1506": 30.0}, {})
        self.assertEqual(out["date"], "2026-11-05")
        self.assertEqual(out["signals"], [{"ticker": "1506", "date": "2026-11-05", "close": 30.0,
                                           "dist_ma20": 1.5, "rsi14": 55.0}])

    def test_session_bar_in_kline_is_not_counted_twice(self):
        rows = [{"d": f"2026-10-{i:02d}", "c": 10.0} for i in range(1, 30)]
        kline = {"1506": {"kline": rows + [{"d": "2026-11-05", "c": 99.0}]}}
        out = self.run_main("2026-11-05", {"1506": 10.0}, kline)
        self.assertEqual(out["signals"][0]["dist_ma20"], 0.0)

    def test_older_session_changes_nothing(self):
        out = self.run_main("2026-11-03", {"1506": 30.0}, {})
        self.assertEqual(out["date"], "2026-11-04")
        self.assertEqual(out["signals"][0]["close"], 9.0)


if __name__ == "__main__":
    unittest.main()
