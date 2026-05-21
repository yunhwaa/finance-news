"""
scheduler.py — 매일 자동 실행
"""

import schedule
import time
from datetime import datetime
import config
from collector import run


def job():
    print(f"\n⏰ 스케줄 실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    run()


if __name__ == "__main__":
    print("=" * 50)
    print("  📡 금융 리스크 자동 수집 스케줄러")
    print(f"  ⏰ 매일 {config.SCHEDULE_TIME} 자동 실행")
    print("  Ctrl+C 로 중지")
    print("=" * 50)

    schedule.every().day.at(config.SCHEDULE_TIME).do(job)

    answer = input("\n지금 바로 한 번 실행할까요? (y/n): ").strip().lower()
    if answer == "y":
        run()

    print(f"\n✅ 대기 중... 매일 {config.SCHEDULE_TIME}에 자동 실행됩니다.\n")

    while True:
        schedule.run_pending()
        time.sleep(30)