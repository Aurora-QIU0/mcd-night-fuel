#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦麦加班能量局 · 主流程 CLI。

既可作为离线自测工具（--demo），也可被 Skill 编排调用：
从标准输入读取 {context, combos}，输出最优推荐 + 咖啡因策略。

用法：
    python scripts/recommend.py --demo
    echo '{"budget":35,...}' | python scripts/recommend.py --stdin
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from caffeine_model import advise, latest_intake_time, parse_clock  # noqa: E402
from score_meals import rank_combos  # noqa: E402

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


def build_recommendation(context: dict, combos: list[dict]) -> dict:
    """根据上下文与候选组合生成最终推荐。"""
    now_dt = parse_clock(context.get("now", datetime.now().strftime("%H:%M")))
    sleep_dt = parse_clock(context.get("sleep", "02:00"), now_dt)
    budget = float(context.get("budget", 35))
    need_caffeine = bool(context.get("need_caffeine", False))

    # 时间约束优先：若此刻已过咖啡因最晚饮用时间，则不再推荐含咖啡因饮品
    latest = latest_intake_time(sleep_dt)
    caffeine_blocked = need_caffeine and now_dt > latest
    if caffeine_blocked:
        need_caffeine = False

    ranked = rank_combos(combos, budget, need_caffeine)
    top = ranked[0]
    top_combo = next(c for c in combos if c["name"] == top["name"])

    caffeine = advise(
        now_dt=now_dt,
        sleep_dt=sleep_dt,
        intake_mg=float(top_combo.get("caffeine_mg", 0)),
    )

    return {
        "recommendation": top_combo["name"],
        "score": top["score"],
        "score_detail": top["detail"],
        "price": top_combo["price"],
        "calories": top_combo["calories"],
        "protein": top_combo["protein"],
        "sodium": top_combo["sodium"],
        "caffeine": caffeine,
        "caffeine_blocked_by_time": caffeine_blocked,
        "latest_intake": latest.strftime("%H:%M"),
        "alternatives": [
            {"name": r["name"], "score": r["score"]} for r in ranked[1:3]
        ],
    }


def render(result: dict) -> str:
    """把结果渲染成适合直接发给用户的文本。"""
    lines = [
        f"推荐组合：{result['recommendation']}",
        f"综合得分：{result['score']} / 100",
        f"价格：¥{result['price']}",
        f"营养：热量 {result['calories']} kcal ｜ 蛋白质 {result['protein']} g ｜ 钠 {result['sodium']} mg",
        f"咖啡因：{result['caffeine']['advice']}",
    ]
    if result.get("caffeine_blocked_by_time"):
        lines.append(
            f"⚠️ 已过咖啡因最晚饮用时间 {result['latest_intake']}，提神需求已自动让位于睡眠质量。"
        )
    if result.get("alternatives"):
        alts = "、".join(f"{a['name']}（{a['score']}）" for a in result["alternatives"])
        lines.append(f"备选：{alts}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="麦麦加班能量局 · 推荐主流程")
    parser.add_argument("--demo", action="store_true", help="使用内置示例数据运行")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读取 JSON")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args()

    if args.stdin:
        payload = json.load(sys.stdin)
        context = payload.get("context", {})
        combos = payload.get("combos", [])
    else:
        context, combos = DEMO_CONTEXT, DEMO_COMBOS

    result = build_recommendation(context, combos)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render(result))


if __name__ == "__main__":
    main()
