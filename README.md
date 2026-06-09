# 大飆股DNA — TWSE 多週期量化交易篩選系統

## 📈 專案概述
基於 TWSE 歷史資料，實作九步量化策略的台股篩選系統。

## 🏗️ 系統架構
```
code/
├── data_loader.py     # Phase 1: 資料讀取與還原權值
├── indicators.py      # Phase 2: 技術指標庫 (MACD, DMI, RSI, VR, N2, 6K/9K)
├── strategy.py        # Phase 3: 九步策略引擎 (大盤/類股/買進/賣出/切入/危機)
├── main.py            # Phase 4: 每日掃描 CLI
└── tests/             # 單元測試 (95 tests)

docs/
├── dashboard.html     # GitHub Pages 回測儀表板
└── backtest_data.json # 回測資料 (自動產生)
```

## 🚀 使用方式
```bash
# 每日掃描
python main.py --watchlist 2330,2454,2317

# 全市場掃描
python main.py --all

# 歷史回測
python backtest.py --ticker 2330 --start 2004 --end 2026
```

## 📊 回測儀表板
https://slashman413.github.io/twse-surge-stocks-dna/dashboard.html

## 🛠️ 技術棧
- Python 3.11+, pandas, numpy
- yfinance (資料補償)
- Chart.js (Dashboard 圖表)
- GitHub Pages (佈署)
