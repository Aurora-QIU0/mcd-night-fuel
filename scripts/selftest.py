#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多时段自测：验证「全天候」策略在每个时段都能给出合理推荐。

不依赖麦当劳 MCP，使用内置样例数据，可在任何环境直接运行。

用法：
    python scripts/selftest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from recommend import DEMO_COMBOS, DEMO_CONTEXT, build_recommendation  # noqa: E402

# (模拟时间, 期望时段标签, 期望咖啡因是否应被关闭)
CASES = [
    ("08:00", "早餐", False),
    ("12:00", "午市", False),
    ("15:30", "下午茶", False),
    ("19:00", "晚餐", False),
    ("23:40", "深夜", True),
    ("03:00", "凌晨", True),
]


def run() -> int:
    passed = 0
    failures: list[str] = []

    for clock, expect_label, expect_blocked in CASES:
        context = {**DEMO_CONTEXT, "now": clock}
        result = build_recommendation(context, DEMO_COMBOS)

        label = result["window"]["label"]
        blocked = result["caffeine_blocked_by_time"] or result["caffeine_blocked_by_policy"]

        checks = [
            ("时段判定", label == expect_label),
            ("有推荐结果", bool(result["recommendation"])),
            ("价格未严重超预算", result["price"] <= context["budget"] * 1.5),
            ("咖啡因策略", blocked == expect_blocked),
        ]
        ok = all(flag for _, flag in checks)
        status = "PASS" if ok else "FAIL"

        print(f"[{status}] {clock} → {label}")
        print(f"        推荐：{result['recommendation']}  ¥{result['price']}")
        print(f"        理由：{result['reason']}")
        print(f"        咖啡因：{result['caffeine']['advice']}")
        for name, flag in checks:
            if not flag:
                print(f"        ✗ 未通过：{name}")
        print()

        if ok:
            passed += 1
        else:
            failures.append(clock)

    print(f"==== 时段策略 通过 {passed}/{len(CASES)} ====")

    # 附加：咖啡因表的名称模糊匹配
    from caffeine_model import lookup_item

    lookup_cases = [
        ("可口可乐（中杯）", True),
        ("可口可乐(中杯)", True),
        ("麦咖啡美式（中杯）", True),
        ("麦咖啡美式", True),
        ("雪碧（中杯）", True),
        ("完全不存在的饮料XYZ", False),
    ]
    print("==== 咖啡因表模糊匹配 ====")
    lookup_pass = 0
    for name, should_hit in lookup_cases:
        hit = lookup_item(name) is not None
        ok = hit == should_hit
        print(f"[{'PASS' if ok else 'FAIL'}] {name} → {'命中' if hit else '未命中'}")
        if ok:
            lookup_pass += 1
        else:
            failures.append(f"lookup:{name}")
    print(f"==== 咖啡因表匹配 通过 {lookup_pass}/{len(lookup_cases)} ====")

    if failures:
        print("失败用例：" + "、".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
