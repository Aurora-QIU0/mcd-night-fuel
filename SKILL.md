---
name: mcd-night-fuel
description: 麦麦加班能量局 —— 深夜/加班场景下的麦当劳点餐决策助手。当用户提到「加班」「熬夜」「通宵」「深夜吃什么」「现在还能不能喝咖啡」「想提神又怕失眠」「预算有限想吃麦当劳」等诉求，并希望得到麦当劳点餐建议时使用本 Skill。
---

# 麦麦加班能量局 · Skill 定义

## 1. 适用场景

用户在**深夜或高强度工作场景**下需要麦当劳点餐建议，且存在以下约束中的至少一个：

- 时间约束（还要工作多久、几点睡）
- 提神需求（要不要咖啡因、能不能喝咖啡）
- 预算约束（多少钱）
- 负担约束（吃太撑/太咸会不会影响睡眠）

## 2. 触发词

`加班吃什么` · `熬夜点麦当劳` · `深夜麦当劳` · `现在还能喝咖啡吗` · `想提神但不想失眠` · `预算XX吃麦当劳` · `写代码到几点该点什么`

## 3. 输入解析

从用户自然语言中抽取以下字段（缺失的用合理默认值，并向用户确认关键项）：

| 字段 | 说明 | 默认 |
|---|---|---|
| `now` | 当前时间 | 调用 `now-time-info` |
| `work_hours` | 还要工作多久 | 2 小时 |
| `sleep` | 计划入睡时间 | `now + work_hours + 0.5h` |
| `budget` | 预算（元） | 35 |
| `need_caffeine` | 是否需要提神 | 依据用户表述判断 |
| `taboo` | 忌口/偏好 | 无 |

## 4. 执行流程

```text
[1] now-time-info               获取当前时间
[2] query-nearby-stores         定位附近可用门店
[3] query-meals                 拉取门店在售餐品
[4] query-meal-detail           补充套餐组成（必要时）
[5] list-nutrition-foods        匹配营养数据
[6] query-store-coupons
    available-coupons           汇总可用券
[7] calculate-price             对候选组合计算到手价
[8] scripts/score_meals.py      多目标打分，选出 Top1
[9] scripts/caffeine_model.py   计算咖啡因最晚饮用时间
[10] 输出推荐方案
[11] 用户确认后 → create-order  下单
```

**重要：** 步骤 [11] `create-order` 属于**资金相关操作**，必须显式获得用户确认后才能调用。

## 5. 输出模板

```markdown
| 项目 | 结果 |
|---|---|
| 🍔 推荐组合 | {餐品组合} |
| 💰 用券后价 | ¥{price}（原价 ¥{original}，省 ¥{saved}） |
| 🔥 营养 | 热量 {kcal} kcal ｜ 蛋白质 {protein} g ｜ 钠 {sodium} mg |
| ☕ 咖啡因策略 | {advice} |
| ⏰ 时间建议 | {timing} |
| ▶️ 下一步 | 需要我直接下单吗？ |
```

## 6. 约束与红线

- **不虚构数据**：所有餐品、价格、营养均来自麦当劳 MCP 实时返回，不得凭记忆编造。
- **营养/咖啡因不构成医疗建议**：输出须附免责提示。
- **下单需确认**：`create-order` 前必须用户明确同意。
- **不处理支付**：仅返回官方支付链接，不代收任何款项。
- **限流意识**：单 Token 600 次/分钟，合并重复请求，缓存菜单与营养数据。

## 7. 本地脚本接口

| 脚本 | 作用 | 调用方式 |
|---|---|---|
| `scripts/recommend.py` | 主流程（打分 + 咖啡因策略） | `python scripts/recommend.py --stdin` |
| `scripts/score_meals.py` | 组合多目标打分 | 作为模块 import |
| `scripts/caffeine_model.py` | 咖啡因最晚饮用时间 | `python scripts/caffeine_model.py --now 23:40 --sleep 02:00 --mg 150` |

`recommend.py --stdin` 的输入格式：

```json
{
  "context": { "now": "23:40", "sleep": "02:00", "budget": 35, "need_caffeine": true },
  "combos": [
    { "name": "麦辣鸡腿堡套餐", "price": 31.5, "calories": 780, "protein": 32, "sodium": 1580, "caffeine_mg": 50 }
  ]
}
```
