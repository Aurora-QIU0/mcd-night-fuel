#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦麦加班能量局 · 全天候主流程。

既可作为离线自测工具，也可被 Skill 编排调用：
从标准输入读取 {context, combos}，按当前时段策略输出最优推荐 +
咖啡因建议 + 备选方案。

时段策略由 meal_window.py 提供（早餐/午市/下午茶/晚餐/深夜/凌晨），
同一份菜单在不同时段会得到不同推荐。

用法：
    python scripts/recommend.py --demo
    python scripts/recommend.py --demo --at 15:30     # 模拟下午茶时段
    python scripts/recommend.py --demo --at 03:00     # 模拟凌晨时段
    python scripts/recommend.py --stdin < scripts/sample-input.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from caffeine_model import advise, latest_intake_time, parse_clock  # noqa: E402
from meal_window import get_window  # noqa: E402
from score_meals import diff_note, explain, fmt_price, rank_combos  # noqa: E402

DEMO_CONTEXT = {
    "now": "23:40",
    "sleep": "02:00",
    "budget": 35,
    "work_hours": 2,
    "need_caffeine": True,
}

DEMO_COMBOS = [
    {
        "name": "麦辣鸡腿堡 + 中薯条 + 无糖可乐（中杯）",
        "price": 31.5,
        "original_price": 39.0,
        "calories": 780,
        "protein": 32,
        "sodium": 1580,
        "caffeine_mg": 50,
    },
    {
        "name": "板烧鸡腿堡 + 无糖可乐（小杯）",
        "price": 18.0,
        "calories": 420,
        "protein": 24,
        "sodium": 980,
        "caffeine_mg": 34,
    },
    {
        "name": "巨无霸 + 中薯条 + 麦咖啡美式（中杯）",
        "price": 42.0,
        "calories": 1020,
        "protein": 36,
        "sodium": 1900,
        "caffeine_mg": 150,
    },
    {
        "name": "双层吉士堡 + 雪碧（中杯）",
        "price": 24.0,
        "calories": 560,
        "protein": 27,
        "sodium": 1240,
        "caffeine_mg": 0,
    },
]

# 用 --window 模拟某时段时，使用该时段的代表性时间
WINDOW_CLOCK = {
    "breakfast": "08:00",
    "lunch": "12:00",
    "afternoon": "15:30",
    "dinner": "19:00",
    "latenight": "23:00",
    "dawn": "03:00",
}


def _to_yuan(value, price_unit: str) -> float:
    """价格单位归一化。

    麦当劳 `calculate-price` 返回的金额单位可能是「分」，
    此处统一换算成「元」，避免后续计算放大 100 倍。
    """
    v = float(value or 0)
    return round(v / 100, 2) if str(price_unit).lower() == "cent" else v


def build_recommendation(context: dict, combos: list[dict]) -> dict:
    """根据上下文与候选组合生成最终推荐。"""
    now_dt = parse_clock(context.get("now") or datetime.now().strftime("%H:%M"))
    sleep_dt = parse_clock(context.get("sleep", "02:00"), now_dt)
    budget = float(context.get("budget", 35))
    need_caffeine = bool(context.get("need_caffeine", False))
    price_unit = str(context.get("price_unit", "yuan"))

    # 价格单位统一（分 → 元）
    normalized = []
    for c in combos:
        c2 = dict(c)
        c2["price"] = _to_yuan(c.get("price"), price_unit)
        if c.get("original_price") is not None:
            c2["original_price"] = _to_yuan(c.get("original_price"), price_unit)
        normalized.append(c2)
    combos = normalized

    # 时段策略
    window = get_window(now_dt)

    # 咖啡因约束：时段策略（凌晨直接关闭）优先于用户意愿，其次是时间截止点
    latest = latest_intake_time(sleep_dt)
    policy = window.get("caffeine_policy", "open")
    blocked_by_policy = policy == "off"
    caffeine_blocked = blocked_by_policy or (need_caffeine and now_dt > latest)
    eff_need = False if caffeine_blocked else need_caffeine

    ranked = rank_combos(combos, budget, eff_need, window)
    if not ranked:
        raise ValueError("候选组合为空，无法推荐")

    top = ranked[0]
    top_combo = next(c for c in combos if c["name"] == top["name"])

    caffeine = advise(
        now_dt=now_dt,
        sleep_dt=sleep_dt,
        intake_mg=float(top_combo.get("caffeine_mg", 0)),
    )
    if blocked_by_policy:
        caffeine = {
            **caffeine,
            "can_drink_now": False,
            "advice": f"{window['caffeine_note']}（当前时段不建议摄入任何咖啡因）",
        }

    saved = None
    if top_combo.get("original_price"):
        saved = round(float(top_combo["original_price"]) - float(top_combo["price"]), 1)

    alternatives = []
    for r in ranked[1:3]:
        c = next(x for x in combos if x["name"] == r["name"])
        alternatives.append({"name": c["name"], "price": c["price"], "note": diff_note(c, top_combo)})

    return {
        "window": {
            "key": window["key"],
            "label": window["label"],
            "emoji": window["emoji"],
            "desc": window["desc"],
            "tip": window["tip"],
        },
        "recommendation": top_combo["name"],
        "score": top["score"],  # 仅保留在 JSON 输出中，不展示给用户
        "score_detail": top["detail"],
        "price": top_combo["price"],
        "saved": saved,
        "calories": top_combo["calories"],
        "protein": top_combo["protein"],
        "sodium": top_combo["sodium"],
        "reason": explain(top_combo, top["detail"], window),
        "caffeine": caffeine,
        "caffeine_blocked_by_time": caffeine_blocked,
        "caffeine_blocked_by_policy": blocked_by_policy,
        "latest_intake": latest.strftime("%H:%M"),
        "alternatives": alternatives,
        "is_late": window["key"] in ("latenight", "dawn"),
    }


def render(result: dict) -> str:
    """渲染成适合直接发给用户的文本（面向体验，不暴露内部得分）。"""
    w = result["window"]
    lines = [f"{w['emoji']} {w['label']}", ""]

    price_line = f"¥{fmt_price(result['price'])}"
    if result.get("saved"):
        price_line += f"（用券后，省 ¥{fmt_price(result['saved'])}）"

    lines.append(f"推荐：{result['recommendation']}")
    lines.append(f"{price_line} ｜ 热量 {result['calories']} kcal ｜ 蛋白 {result['protein']} g ｜ 钠 {result['sodium']} mg")
    lines.append("")
    lines.append(f"为什么是它：{result['reason']}")
    lines.append(f"☕ 咖啡因：{result['caffeine']['advice']}")
    lines.append(f"⏰ 时段建议：{w['tip']}")

    if result.get("caffeine_blocked_by_policy"):
        lines.append("⚠️ 当前时段不建议摄入咖啡因，提神需求已让位于休息质量。")
    elif result.get("caffeine_blocked_by_time"):
        lines.append(f"⚠️ 已过咖啡因最晚饮用时间 {result['latest_intake']}，提神需求已让位于睡眠质量。")

    if result["alternatives"]:
        lines.append("")
        lines.append("备选：")
        for a in result["alternatives"]:
            lines.append(f"· {a['name']} ¥{fmt_price(a['price'])} —— {a['note']}")

    lines.append("")
    lines.append("要下单吗？走的是麦当劳官方支付链接，钱直接付给麦当劳，我不接触你的支付信息。")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="麦麦加班能量局 · 全天候推荐主流程")
    parser.add_argument("--demo", action="store_true", help="使用内置示例数据运行")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读取 JSON")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出（含打分明细）")
    parser.add_argument("--at", help="模拟当前时间 HH:MM（用于测试不同时段）")
    parser.add_argument("--window", choices=list(WINDOW_CLOCK), help="直接指定时段进行测试")
    args = parser.parse_args()

    if args.stdin:
        payload = json.load(sys.stdin)
        context = dict(payload.get("context", {}))
        combos = payload.get("combos", [])
    else:
        context, combos = dict(DEMO_CONTEXT), DEMO_COMBOS

    if args.at:
        context["now"] = args.at
    elif args.window:
        context["now"] = WINDOW_CLOCK[args.window]

    result = build_recommendation(context, combos)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render(result))


if __name__ == "__main__":
    main()
