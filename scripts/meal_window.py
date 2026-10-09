#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全天候时段判定与分时段策略。

把一天划分为 6 个用餐时段，每个时段给出独立的打分参数：
    理想热量区间 / 蛋白质目标 / 钠含量阈值 / 咖啡因策略 / 五维权重

这是「全天候」能力的核心：同一份菜单，在不同时段会被打出不同的分。

用法：
    python scripts/meal_window.py --now 23:40
    python scripts/meal_window.py --now 15:20 --json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime

# 策略轴以 06:00 为一天起点，方便处理跨零点时段
AXIS_START_MIN = 6 * 60

WINDOWS = [
    {
        "key": "breakfast",
        "label": "早餐",
        "start": 6 * 60,
        "end": 10 * 60 + 30,
        "desc": "一天第一顿，重点是扛到午饭",
        "emoji": "🌅",
    },
    {
        "key": "lunch",
        "label": "午市",
        "start": 10 * 60 + 30,
        "end": 14 * 60,
        "desc": "正餐档，但要给下午留精神",
        "emoji": "🍱",
    },
    {
        "key": "afternoon",
        "label": "下午茶",
        "start": 14 * 60,
        "end": 17 * 60,
        "desc": "提神为主，别吃太饱",
        "emoji": "☕",
    },
    {
        "key": "dinner",
        "label": "晚餐",
        "start": 17 * 60,
        "end": 21 * 60,
        "desc": "正餐，为睡眠留余量",
        "emoji": "🌆",
    },
    {
        "key": "latenight",
        "label": "深夜",
        "start": 21 * 60,
        "end": 25 * 60,
        "desc": "轻负担，别让胃撑到失眠",
        "emoji": "🌙",
    },
    {
        "key": "dawn",
        "label": "凌晨",
        "start": 25 * 60,
        "end": 30 * 60,
        "desc": "只垫肚子，尽快休息",
        "emoji": "🌃",
    },
]

# 各时段的打分参数与权重
PROFILES = {
    "breakfast": {
        "calorie_low": 400,
        "calorie_peak": 600,
        "calorie_high": 800,
        "protein_target": 25,
        "sodium_good": 1000,
        "sodium_bad": 1900,
        "caffeine_policy": "open",
        "caffeine_note": "早上这杯可以放心喝，午前基本代谢得掉。",
        "weights": {"budget": 0.30, "protein": 0.25, "calorie": 0.20, "sodium": 0.10, "caffeine": 0.15},
        "tip": "挑一份主食配蛋白质，撑到午饭不犯饿。",
    },
    "lunch": {
        "calorie_low": 600,
        "calorie_peak": 800,
        "calorie_high": 1000,
        "protein_target": 32,
        "sodium_good": 1100,
        "sodium_bad": 2000,
        "caffeine_policy": "open",
        "caffeine_note": "饭后可以来一杯，但尽量别晚过下午 3 点。",
        "weights": {"budget": 0.30, "protein": 0.25, "calorie": 0.20, "sodium": 0.15, "caffeine": 0.10},
        "tip": "正餐吃饱，但主食别过量，免得下午犯困。",
    },
    "afternoon": {
        "calorie_low": 200,
        "calorie_peak": 350,
        "calorie_high": 550,
        "protein_target": 15,
        "sodium_good": 700,
        "sodium_bad": 1500,
        "caffeine_policy": "open",
        "caffeine_note": "下午 2–4 点是咖啡因黄金窗口：提神最好，且不影响夜间睡眠。",
        "weights": {"budget": 0.25, "protein": 0.15, "calorie": 0.25, "sodium": 0.10, "caffeine": 0.25},
        "tip": "轻食加一杯咖啡，撑到下班刚好。",
    },
    "dinner": {
        "calorie_low": 500,
        "calorie_peak": 700,
        "calorie_high": 900,
        "protein_target": 30,
        "sodium_good": 1000,
        "sodium_bad": 1900,
        "caffeine_policy": "cautious",
        "caffeine_note": "这个点要留意咖啡因，睡前 3 小时内摄入很可能影响入睡。",
        "weights": {"budget": 0.30, "protein": 0.25, "calorie": 0.20, "sodium": 0.15, "caffeine": 0.10},
        "tip": "正常吃，但给睡眠留点余地。",
    },
    "latenight": {
        "calorie_low": 350,
        "calorie_peak": 500,
        "calorie_high": 700,
        "protein_target": 25,
        "sodium_good": 800,
        "sodium_bad": 1600,
        "caffeine_policy": "cutoff",
        "caffeine_note": "过了咖啡因截止点就别灌了，睡眠比这半小时的清醒值钱。",
        "weights": {"budget": 0.25, "protein": 0.25, "calorie": 0.25, "sodium": 0.20, "caffeine": 0.05},
        "tip": "以轻负担为主，别让胃撑着睡不着。",
    },
    "dawn": {
        "calorie_low": 200,
        "calorie_peak": 350,
        "calorie_high": 550,
        "protein_target": 20,
        "sodium_good": 600,
        "sodium_bad": 1400,
        "caffeine_policy": "off",
        "caffeine_note": "这个点绝对别碰咖啡因——天亮还要不要睡了？",
        "weights": {"budget": 0.20, "protein": 0.20, "calorie": 0.25, "sodium": 0.15, "caffeine": 0.20},
        "tip": "只垫一下肚子，赶紧去睡。",
    },
}


# 各时段对「不必要的咖啡因」的惩罚系数：越晚越重，凌晨最严
CAFFEINE_PENALTY = {
    "breakfast": 1.5,
    "lunch": 1.5,
    "afternoon": 1.5,
    "dinner": 3.0,
    "latenight": 6.0,
    "dawn": 10.0,
}


def to_axis_minutes(dt: datetime) -> int:
    """把时间映射到「以 06:00 为起点」的策略轴分钟数（可超过 1440）。"""
    minutes = dt.hour * 60 + dt.minute
    if minutes < AXIS_START_MIN:
        minutes += 24 * 60
    return minutes


def get_window(dt: datetime) -> dict:
    """判定给定时间所属的用餐时段，返回该时段的完整策略。"""
    axis = to_axis_minutes(dt)
    for win in WINDOWS:
        if win["start"] <= axis < win["end"]:
            return {
                **win,
                **PROFILES[win["key"]],
                "caffeine_penalty": CAFFEINE_PENALTY[win["key"]],
            }
    # 理论上不会走到这里，兜底返回深夜策略
    fallback = WINDOWS[4]
    return {
        **fallback,
        **PROFILES[fallback["key"]],
        "caffeine_penalty": CAFFEINE_PENALTY[fallback["key"]],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="时段判定与分时段策略")
    parser.add_argument("--now", help="时间，格式 HH:MM，默认当前时间")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = parser.parse_args()

    if args.now:
        hour, minute = (int(x) for x in args.now.strip().split(":"))
        now_dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    else:
        now_dt = datetime.now()

    window = get_window(now_dt)

    if args.json:
        print(json.dumps(window, ensure_ascii=False, indent=2))
    else:
        print(f"{window['emoji']} {window['label']}（{window['desc']}）")
        print(f"建议：{window['tip']}")
        print(f"咖啡因：{window['caffeine_note']}")


if __name__ == "__main__":
    main()
