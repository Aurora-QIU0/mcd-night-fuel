#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""咖啡因最晚饮用时间计算。

核心模型：
    最晚饮用时间 = 计划入睡时间 - sleep_buffer_hours
    睡前残留量   = 摄入量 * 0.5 ** (间隔小时 / 半衰期)

麦当劳 MCP 不提供任何咖啡因/代谢相关能力，本模块是项目自建的决策层，
用于回答「现在这杯咖啡还能不能喝」。

用法：
    python scripts/caffeine_model.py --now 23:40 --sleep 02:00 --mg 150
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_HALF_LIFE_HOURS = 5.0
DEFAULT_SLEEP_BUFFER_HOURS = 3.0
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "caffeine_table.json"


def load_table(path: Path = DATA_FILE) -> dict:
    """读取咖啡因数据表；文件缺失时回退到内置默认参数。"""
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {
            "model": {
                "half_life_hours": DEFAULT_HALF_LIFE_HOURS,
                "sleep_buffer_hours": DEFAULT_SLEEP_BUFFER_HOURS,
            },
            "items": [],
        }


def parse_clock(value: str, base: datetime | None = None) -> datetime:
    """解析 "HH:MM" 为 datetime。

    若时间早于基准时间，视为「次日」（适配跨零点场景，如 23:40 -> 02:00）。
    """
    base = base or datetime.now()
    hour, minute = (int(x) for x in value.strip().split(":"))
    dt = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if base and dt < base:
        dt += timedelta(days=1)
    return dt


def latest_intake_time(sleep_dt: datetime, buffer_hours: float = DEFAULT_SLEEP_BUFFER_HOURS) -> datetime:
    """计算最晚饮用时间。"""
    return sleep_dt - timedelta(hours=buffer_hours)


def residual_mg(intake_mg: float, hours_elapsed: float, half_life: float = DEFAULT_HALF_LIFE_HOURS) -> float:
    """计算经过 hours_elapsed 小时后体内残留的咖啡因（毫克）。"""
    if hours_elapsed <= 0:
        return float(intake_mg)
    return round(intake_mg * (0.5 ** (hours_elapsed / half_life)), 2)


def advise(
    now_dt: datetime,
    sleep_dt: datetime,
    intake_mg: float = 0.0,
    half_life: float = DEFAULT_HALF_LIFE_HOURS,
    buffer_hours: float = DEFAULT_SLEEP_BUFFER_HOURS,
) -> dict:
    """给出咖啡因摄入建议。

    Returns:
        dict: 包含最晚饮用时间、是否可饮、睡前残留量、建议文案。
    """
    latest = latest_intake_time(sleep_dt, buffer_hours)
    ok = now_dt <= latest
    hours_to_sleep = (sleep_dt - now_dt).total_seconds() / 3600.0
    residual = residual_mg(intake_mg, hours_to_sleep, half_life)

    if intake_mg <= 0:
        advice = "所选饮品不含咖啡因，不影响入睡。"
    elif ok:
        advice = (
            f"现在可以喝，但请在最晚 {latest:%H:%M} 前喝完"
            f"（距现在还有 {(latest - now_dt).total_seconds() / 3600.0:.1f} 小时）。"
        )
    else:
        advice = (
            f"已超过最晚饮用时间 {latest:%H:%M}，建议改选无咖啡因饮品（如雪碧/橙汁/牛奶）。"
        )

    return {
        "now": now_dt.strftime("%Y-%m-%d %H:%M"),
        "planned_sleep": sleep_dt.strftime("%Y-%m-%d %H:%M"),
        "latest_intake": latest.strftime("%Y-%m-%d %H:%M"),
        "can_drink_now": ok,
        "intake_mg": intake_mg,
        "hours_until_sleep": round(hours_to_sleep, 2),
        "residual_mg_at_sleep": residual,
        "advice": advice,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="计算咖啡因最晚饮用时间")
    parser.add_argument("--now", help="当前时间，格式 HH:MM，默认现在")
    parser.add_argument("--sleep", required=True, help="计划入睡时间，格式 HH:MM")
    parser.add_argument("--mg", type=float, default=0.0, help="计划摄入的咖啡因毫克数")
    parser.add_argument("--half-life", type=float, default=DEFAULT_HALF_LIFE_HOURS, help="咖啡因半衰期（小时）")
    parser.add_argument("--buffer", type=float, default=DEFAULT_SLEEP_BUFFER_HOURS, help="睡前缓冲（小时）")
    args = parser.parse_args()

    now_dt = datetime.now()
    if args.now:
        now_dt = parse_clock(args.now, now_dt)

    sleep_dt = parse_clock(args.sleep, now_dt)

    result = advise(
        now_dt=now_dt,
        sleep_dt=sleep_dt,
        intake_mg=args.mg,
        half_life=args.half_life,
        buffer_hours=args.buffer,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
