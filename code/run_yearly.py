import sys, os, json, time, random
from datetime import date, timedelta

from twse_crawler import (
    fetch_one_day, _sleep, _is_trading_day, _fmt_date,
    RAW_DIR, YEAR_SLEEP_MIN, YEAR_SLEEP_MAX,
    log,
)

YEAR_SLEEP = (YEAR_SLEEP_MIN, YEAR_SLEEP_MAX)  # 4~10 分

def run_all():
    start_year = 2004
    end_year = date.today().year  # 2026

    for year in range(start_year, end_year + 1):


        # 載入進度
        completed: set[str] = set()
        if os.path.exists(progress_file):
            with open(progress_file) as f:
                prog = json.load(f)

        start = date(year, 1, 1)
        end = date(year, 12, 31)
        if end > date.today():
            end = date.today()

        # 檢查是否已完整
        total_trading = sum(1 for i in range((end - start).days + 1)
                            if (start + timedelta(days=i)).weekday() < 5)
        if len(completed) >= total_trading:
            if year < end_year:
                _sleep(YEAR_SLEEP)
            continue

        year_dir = os.path.join(RAW_DIR, str(year))
        os.makedirs(year_dir, exist_ok=True)

        current = start
        day_count = 0
        total_rows = 0
        exdiv_count = 0

        while current <= end:
            ds = _fmt_date(current)
            if ds in completed:
                current += timedelta(days=1)
                continue
            if not _is_trading_day(current):
                current += timedelta(days=1)
                continue

            result = fetch_one_day(current, save=True)
                day_count += 1
                completed.add(ds)

                # 進度存檔
                    json.dump({
                    }, f, ensure_ascii=False, indent=2)

            # 跨日 sleep 2~5 分
            _sleep()
            current += timedelta(days=1)

        # 年度完成

        # 合併該年
        try:
            import subprocess
            subprocess.run([
        except Exception as e:

        # ── 年度後處理：還原權值 + 回測 ──

        # 還原權值 (掃描 Raw/ 輸出到 Adjusted/)
        if os.path.exists(adjuster_py):
            try:
                subprocess.run([
                    sys.executable, adjuster_py,
            except Exception as e:

        # 歷史回測 (全量上市股票)
        if os.path.exists(backtest_py):
            try:
                report_path = (
                )
                subprocess.run([
                    sys.executable, backtest_py,
            except Exception as e:

        # 跨年 sleep 4~10 分
        if year < end_year:
            mins = random.randint(YEAR_SLEEP[0] // 60, YEAR_SLEEP[1] // 60)
            _sleep(YEAR_SLEEP)

    # 全量合併
    try:
        import subprocess
        subprocess.run([
    except Exception as e:


    run_all()
