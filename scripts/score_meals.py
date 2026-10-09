#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分时段餐品组合打分。

输入一组候选组合（价格 / 营养 / 咖啡因）+ 当前时段策略，
输出 0-100 的综合得分与分项明细。

时段策略由 meal_window.py 提供。不同时段会：
    - 调整理想热量区间（早餐放宽、深夜收紧）
    - 调整蛋白质目标与钠含量阈值
    - 重新分配五维权重（下午茶给提神加权、凌晨给热量加权）

用法（作为模块）：
    from meal_window import get_window
    from score_meals import rank_combos
    profile = get_window(now_dt)
    ranked = rank_combos(combos, budget, need_caffeine, profile)
"""

from __future__ import annotations

# 缺省参数（不传 profile 时使用），等价于「普遍场景」
DEFAULT_PROFILE = {
    "calorie_low": 400,
    "calorie_peak": 600,
    "calorie_high": 900,
    "protein_target": 30,
    "sodium_good": 900,
    "sodium_bad": 2000,
    "weights": {"budget": 0.30, "protein": 0.20, "calorie": 0.20, "sodium": 0.15, "caffeine": 0.15},
}

DIME_KEYS = ("budget", "protein", "calorie", "sodium", "caffeine")


def fmt_price(value) -> str:
    """价格格式化：整数不带小数点（24.0 → 24，31.5 → 31.5）。"""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{num:.0f}" if abs(num - round(num)) < 0.005 else f"{num:.1f}"


def _budget_score(price: float, budget: float) -> float:
    """预算利用率：用到预算的 85% 视为满分配置，超预算重罚。"""
    if budget <= 0:
        return 50.0
    ratio = price / budget
    if ratio <= 1.0:
        return round(min(ratio / 0.85, 1.0) * 100, 1)
    return round(max(0.0, 100 - (ratio - 1.0) * 500), 1)


def _protein_score(protein_g: float, target: float) -> float:
    return round(min(protein_g / max(target, 1), 1.0) * 100, 1)


def _calorie_score(calories: float, low: float, peak: float, high: float) -> float:
    """三角隶属函数：理想区间内满分，越偏离越低。"""
    if calories <= 0:
        return 0.0
    if low <= calories <= high:
        if calories <= peak:
            span = max(peak - low, 1)
            return round(60 + 40 * (calories - low) / span, 1)
        span = max(high - peak, 1)
        return round(100 - 40 * (calories - peak) / span, 1)
    if calories < low:
        return round(max(0.0, calories / low * 60), 1)
    return round(max(0.0, 60 - (calories - high) / 10), 1)


def _sodium_score(sodium_mg: float, good: float, bad: float) -> float:
    if sodium_mg <= good:
        return 100.0
    if sodium_mg >= bad:
        return 0.0
    span = max(bad - good, 1)
    return round(100 * (1 - (sodium_mg - good) / span), 1)


def _caffeine_score(caffeine_mg: float, need_caffeine: bool, penalty: float = 1.5) -> float:
    """需要提神时 30–120mg 最佳；不需要提神时 0mg 满分。

    penalty 是该时段对「不必要的咖啡因」的惩罚系数：越晚的时段惩罚越重，
    用于避免凌晨时段还推荐出含咖啡因的饮品。
    """
    if not need_caffeine:
        return 100.0 if caffeine_mg <= 20 else round(max(0.0, 100 - (caffeine_mg - 20) * penalty), 1)
    if caffeine_mg <= 0:
        return 20.0
    if 30 <= caffeine_mg <= 120:
        return 100.0
    if caffeine_mg < 30:
        return round(caffeine_mg / 30 * 80, 1)
    return round(max(0.0, 100 - (caffeine_mg - 120) * 0.6), 1)


def score_combo(
    combo: dict, budget: float, need_caffeine: bool = False, profile: dict | None = None
) -> dict:
    """对单个组合打分。

    Args:
        combo: name / price / calories / protein / sodium / caffeine_mg
        budget: 用户预算（元）
        need_caffeine: 是否希望提神
        profile: 时段策略（来自 meal_window.get_window），缺省使用 DEFAULT_PROFILE
    """
    p = {**DEFAULT_PROFILE, **(profile or {})}
    weights = p.get("weights", DEFAULT_PROFILE["weights"])

    detail = {
        "budget": _budget_score(float(combo.get("price", 0)), budget),
        "protein": _protein_score(float(combo.get("protein", 0)), p["protein_target"]),
        "calorie": _calorie_score(
            float(combo.get("calories", 0)),
            p["calorie_low"],
            p["calorie_peak"],
            p["calorie_high"],
        ),
        "sodium": _sodium_score(float(combo.get("sodium", 0)), p["sodium_good"], p["sodium_bad"]),
        "caffeine": _caffeine_score(
            float(combo.get("caffeine_mg", 0)),
            need_caffeine,
            float(p.get("caffeine_penalty", 1.5)),
        ),
    }
    total = round(sum(detail[k] * weights.get(k, 0) for k in DIME_KEYS), 1)
    return {"name": combo.get("name", "未命名组合"), "score": total, "detail": detail}


def rank_combos(
    combos: list[dict],
    budget: float,
    need_caffeine: bool = False,
    profile: dict | None = None,
) -> list[dict]:
    """对多个组合打分并降序排序。"""
    scored = [score_combo(c, budget, need_caffeine, profile) for c in combos]
    return sorted(scored, key=lambda x: x["score"], reverse=True)


def explain(combo: dict, detail: dict, profile: dict | None = None) -> str:
    """把打分明细翻译成一句人话，替代对用户毫无意义的「83.4 分」。"""
    p = {**DEFAULT_PROFILE, **(profile or {})}
    parts: list[str] = []

    if detail["budget"] >= 80:
        parts.append(f"券后 ¥{fmt_price(combo.get('price'))} 卡在预算内")
    elif detail["budget"] < 50:
        parts.append("价格稍超预算")

    if detail["protein"] >= 85:
        parts.append(f"{combo.get('protein')}g 蛋白质够扛")

    if detail["calorie"] >= 85:
        parts.append(f"{combo.get('calories')} kcal 正合这个时段")

    if detail["sodium"] >= 85:
        parts.append("钠不超标，不会半夜口渴")
    elif detail["sodium"] < 50:
        parts.append("但钠偏高，吃完多喝水")

    mg = float(combo.get("caffeine_mg", 0))
    if detail["caffeine"] >= 90 and mg > 0:
        parts.append(f"{int(mg)}mg 咖啡因刚好提神")
    elif mg <= 0:
        parts.append("不含咖啡因，不影响休息")

    if not parts:
        return p.get("tip", "综合各项指标比较均衡。")
    return "，".join(parts[:3]) + "。"


def diff_note(combo: dict, top_combo: dict) -> str:
    """给备选项生成一句与首选的差异说明。"""
    notes = []
    d_price = float(combo.get("price", 0)) - float(top_combo.get("price", 0))
    if d_price <= -3:
        notes.append(f"便宜 ¥{fmt_price(abs(d_price))}")
    elif d_price >= 3:
        notes.append(f"贵 ¥{fmt_price(d_price)}")

    d_cal = float(combo.get("calories", 0)) - float(top_combo.get("calories", 0))
    if d_cal <= -150:
        notes.append("更轻负担")
    elif d_cal >= 150:
        notes.append("更顶饱")

    d_na = float(combo.get("sodium", 0)) - float(top_combo.get("sodium", 0))
    if d_na >= 200:
        notes.append("钠略高")
    elif d_na <= -200:
        notes.append("更清淡")

    d_caf = float(combo.get("caffeine_mg", 0)) - float(top_combo.get("caffeine_mg", 0))
    if d_caf >= 40:
        notes.append("更提神")
    elif d_caf <= -40:
        notes.append("咖啡因更少")

    return "、".join(notes) if notes else "口味不同的替代"
