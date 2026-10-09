#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深夜餐品组合多目标打分。

输入一组候选组合（价格、营养、咖啡因），输出 0-100 的综合得分与分项明细，
用于在麦当劳 MCP 返回的菜单 + 营养数据中挑出最合适的一个。

打分维度与权重：
    预算匹配 0.30 | 蛋白质 0.20 | 热量适度 0.20 | 钠含量 0.15 | 提神需求 0.15
"""

from __future__ import annotations

WEIGHTS = {
    "budget": 0.30,
    "protein": 0.20,
    "calorie": 0.20,
    "sodium": 0.15,
    "caffeine": 0.15,
}

# 深夜场景的经验参数
IDEAL_CALORIE_LOW = 400
IDEAL_CALORIE_PEAK = 600
IDEAL_CALORIE_HIGH = 900
GOOD_SODIUM = 900      # mg，以下满分
BAD_SODIUM = 2000      # mg，以上零分
TARGET_PROTEIN = 35    # g，达到即满分


def _budget_score(price: float, budget: float) -> float:
    """预算利用率打分：接近但不超预算为最佳。"""
    if budget <= 0:
        return 50.0
    ratio = price / budget
    if ratio <= 1.0:
        # 使用到预算的 85% 即视为满分配置，再低则按比例递减
        return round(min(ratio / 0.85, 1.0) * 100, 1)
    # 超预算重罚
    return round(max(0.0, 100 - (ratio - 1.0) * 500), 1)


def _protein_score(protein_g: float) -> float:
    return round(min(protein_g / TARGET_PROTEIN, 1.0) * 100, 1)


def _calorie_score(calories: float) -> float:
    """三角隶属函数：理想区间内满分，越偏离越低。"""
    if calories <= 0:
        return 0.0
    if IDEAL_CALORIE_LOW <= calories <= IDEAL_CALORIE_HIGH:
        if calories <= IDEAL_CALORIE_PEAK:
            span = IDEAL_CALORIE_PEAK - IDEAL_CALORIE_LOW
            return round(60 + 40 * (calories - IDEAL_CALORIE_LOW) / span, 1)
        span = IDEAL_CALORIE_HIGH - IDEAL_CALORIE_PEAK
        return round(100 - 40 * (calories - IDEAL_CALORIE_PEAK) / span, 1)
    if calories < IDEAL_CALORIE_LOW:
        return round(max(0.0, calories / IDEAL_CALORIE_LOW * 60), 1)
    return round(max(0.0, 60 - (calories - IDEAL_CALORIE_HIGH) / 10), 1)


def _sodium_score(sodium_mg: float) -> float:
    if sodium_mg <= GOOD_SODIUM:
        return 100.0
    if sodium_mg >= BAD_SODIUM:
        return 0.0
    span = BAD_SODIUM - GOOD_SODIUM
    return round(100 * (1 - (sodium_mg - GOOD_SODIUM) / span), 1)


def _caffeine_score(caffeine_mg: float, need_caffeine: bool) -> float:
    """需要提神时，30-120mg 为最佳区间；不需要提神时，0mg 满分。"""
    if not need_caffeine:
        return 100.0 if caffeine_mg <= 20 else round(max(0.0, 100 - (caffeine_mg - 20) * 1.5), 1)
    if caffeine_mg <= 0:
        return 20.0
    if 30 <= caffeine_mg <= 120:
        return 100.0
    if caffeine_mg < 30:
        return round(caffeine_mg / 30 * 80, 1)
    return round(max(0.0, 100 - (caffeine_mg - 120) * 0.6), 1)


def score_combo(combo: dict, budget: float, need_caffeine: bool = False) -> dict:
    """对单个组合打分。

    Args:
        combo: 需包含 name / price / calories / protein / sodium / caffeine_mg。
        budget: 用户预算（元）。
        need_caffeine: 是否希望提神。

    Returns:
        dict: 综合得分与分项明细。
    """
    detail = {
        "budget": _budget_score(float(combo.get("price", 0)), budget),
        "protein": _protein_score(float(combo.get("protein", 0))),
        "calorie": _calorie_score(float(combo.get("calories", 0))),
        "sodium": _sodium_score(float(combo.get("sodium", 0))),
        "caffeine": _caffeine_score(float(combo.get("caffeine_mg", 0)), need_caffeine),
    }
    total = round(sum(detail[k] * WEIGHTS[k] for k in WEIGHTS), 1)
    return {"name": combo.get("name", "未命名组合"), "score": total, "detail": detail}


def rank_combos(combos: list[dict], budget: float, need_caffeine: bool = False) -> list[dict]:
    """对多个组合打分并降序排序。"""
    scored = [score_combo(c, budget, need_caffeine) for c in combos]
    return sorted(scored, key=lambda x: x["score"], reverse=True)
