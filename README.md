<div align="center">

# 🍟 麦麦加班能量局 · MCD Night Fuel

**凌晨还在肝代码，我到底该点麦当劳的什么？**

一句话输入，30 秒给你答案：不饿着、不撑到失眠、咖啡因不顶到天亮。

[![MCP](https://img.shields.io/badge/MCP-mcp.mcd.cn-DA291C)](https://open.mcd.cn/mcp)
[![License](https://img.shields.io/badge/License-MIT-FFC72C)](#-license)
[![Built with WorkBuddy](https://img.shields.io/badge/Built%20with-WorkBuddy-4B8BBE)](https://www.workbuddy.cn)

**⭐ 如果这个项目帮到你，点个 Star 支持我参加麦当劳程序员节创意开发大赛 —— 谢谢麦门！**

</div>

---

## 😵 它解决什么问题

深夜点麦当劳的困境从来不是"吃什么"，而是这几个：

| 真实困境 | 麦麦加班能量局的答案 |
|---|---|
| 凌晨 1 点，吃了怕睡不着 | 按你计划入睡的时间，反推**该吃多少、几点前吃完** |
| 想提神，又怕咖啡因顶到天亮 | 算出**咖啡因最晚饮用时间**（半衰期模型） |
| 预算有限还想吃饱吃好 | 自动找券 + 算到手价，给**最优组合** |
| 翻菜单翻 10 分钟选择困难 | 一句话输入，直接给**一个推荐 + 理由** |

> 已有的点餐助手大多在解决"推荐好吃的"，但它不解决**深夜场景下的时间约束**——
> 麦当劳 MCP 的官方工具里没有任何咖啡因/代谢相关能力。这正是本项目的切入点。

---

## ✨ 效果演示

### 场景 A：傍晚开工，还想提神 → 允许咖啡因

**你输入：**

> 现在 20:00，预算 35，要写代码到凌晨 2 点，想提神

**它输出（得分 84.2 / 100）：**

| 项目 | 结果 |
|---|---|
| 🍔 推荐组合 | 麦辣鸡腿堡 + 中薯条 + 无糖可乐（中杯） |
| 💰 用券后价 | **¥31.5**（原价 ¥39，省 ¥7.5） |
| 🔥 营养 | 热量 780 kcal ｜ 蛋白质 32 g ｜ 钠 1580 mg |
| ☕ 咖啡因策略 | ✅ 现在可以喝，**最晚 23:00 前喝完**（距入睡 6h，留足 3h 代谢余量） |
| ⏰ 时间建议 | 计划 02:00 入睡，23:00 后不再摄入咖啡因 |
| ▶️ 下一步 | 需要我直接下单吗？（调用 `create-order`） |

### 场景 B：深夜已过截止点 → 自动改推荐无咖啡因

**你输入：**

> 现在 23:40，预算 35，还要写 2 小时，想提神但不想失眠

**它输出（得分 83.4 / 100）：**

| 项目 | 结果 |
|---|---|
| 🍔 推荐组合 | 双层吉士堡 + 雪碧（中杯） |
| 💰 用券后价 | **¥24.0** |
| 🔥 营养 | 热量 560 kcal ｜ 蛋白质 27 g ｜ 钠 1240 mg |
| ☕ 咖啡因策略 | ⚠️ **已过咖啡因最晚饮用时间（23:00）**，提神需求自动让位于睡眠质量 |
| ⏰ 时间建议 | 计划 02:00 入睡，此时段建议无咖啡因 |
| ▶️ 下一步 | 需要我直接下单吗？（调用 `create-order`） |

> 💡 **场景 B 是这个小工具最"反直觉"也最有价值的地方。** 你深夜还想灌咖啡时，
> 它会直接劝你"别喝了"，并给出一套无咖啡因但仍能扛饿的组合——
> 把「睡眠质量」排在「当下提神」之上，这是普通点餐助手不会做的事。

---

## 🚀 快速开始

### 1. 申请麦当劳 MCP Token

1. 打开 <https://open.mcd.cn/mcp>
2. 右上角【登录】→ 手机号验证登录
3. 右上角【控制台】→ 点击【激活】申请 Token
4. 同意服务协议 → 复制 Token（**请妥善保管，不要提交到任何公开仓库**）

### 2. 配置 MCP 客户端

把下面的配置粘贴到你的 MCP 客户端（WorkBuddy / Cherry Studio / Cursor / Trae / VSCode），
**把 `${MCD_MCP_TOKEN}` 换成你的真实 Token**：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer ${MCD_MCP_TOKEN}"
      }
    }
  }
}
```

完整脱敏示例见 [`mcp-config.example.json`](./mcp-config.example.json)。

### 3. 使用

配置好之后，直接对 AI 说：

```text
现在 23:40，预算 35，还要写 2 小时代码，想提神但不想失眠，帮我推荐麦当劳
```

Skill 会按 [`SKILL.md`](./SKILL.md) 定义的流程自动编排 MCP 工具调用并输出方案。

### 4. （可选）本地跑算法自测

```bash
# 内置示例数据
python scripts/recommend.py --demo

# 自定义输入（格式见 scripts/sample-input.json）
python scripts/recommend.py --stdin < scripts/sample-input.json
```

不依赖 MCP 即可验证推荐打分与咖啡因模型逻辑。

---

## 🧠 它是怎么想的

```text
解析输入（时间 / 预算 / 工作时长 / 提神需求 / 忌口）
        │
        ├─► now-time-info          拿到当前精确时间
        ├─► query-nearby-stores    定位可用门店
        ├─► query-meals            拉取在售餐品
        ├─► list-nutrition-foods   拿到热量 / 蛋白 / 钠
        ├─► query-store-coupons + available-coupons   找券
        ├─► calculate-price        算到手价
        │
        ▼
   scripts/score_meals.py   多目标打分（预算 / 蛋白 / 热量 / 钠 / 提神）
        │
        ▼
   scripts/caffeine_model.py   咖啡因最晚饮用时间 = 入睡时间 − 3h
        │
        ▼
   输出「一个推荐 + 券后价 + 营养 + 咖啡因策略」
        │
        └─► （用户确认后）create-order 下单
```

**打分权重**（可在 `scripts/score_meals.py` 调整）：

| 因子 | 权重 | 说明 |
|---|---:|---|
| 预算匹配 | 0.30 | 券后价越贴近预算越好，超出则重罚 |
| 蛋白质供给 | 0.20 | 深夜抗饿关键 |
| 热量适度 | 0.20 | 深夜忌过高热量 |
| 钠含量 | 0.15 | 过高影响睡眠与次日状态 |
| 提神需求 | 0.15 | 有咖啡因需求时加成 |

---

## 🔌 用到的麦当劳 MCP 能力

| Tool | 用途 | 必需 |
|---|---|:--:|
| `now-time-info` | 获取当前完整时间 | ✅ |
| `query-nearby-stores` | 查询附近可用门店 | ✅ |
| `query-meals` | 查询门店在售餐品菜单 | ✅ |
| `query-meal-detail` | 查询套餐组成与可替换项 | ✅ |
| `list-nutrition-foods` | 餐品营养数据（能量/蛋白/脂肪/碳水/钠/钙） | ✅ |
| `query-store-coupons` | 当前门店可用优惠券 | ✅ |
| `available-coupons` | 可领取的麦麦省券列表 | ✅ |
| `auto-bind-coupons` | 一键领取可用券 | 建议 |
| `calculate-price` | 计算金额、配送费、优惠与应付总价 | ✅ |
| `create-order` | 创建订单（**仅在用户确认后调用**） | ✅ |
| `query-my-account` | 查询积分（可选，积分抵扣场景） | 可选 |

详细的调用流程与业务价值论证见 [`MCP_INTEGRATION.md`](./MCP_INTEGRATION.md)。

---

## 📁 项目结构

```text
mcd-night-fuel/
├── README.md                  # 项目介绍、安装、使用示例、目标用户
├── CONTEST_DECLARATION.md     # 参赛声明（官方模板，内容不可修改）
├── MCP_INTEGRATION.md         # MCP Server / Tool / 调用流程 / 业务价值
├── mcp-config.example.json    # 脱敏后的 MCP 配置示例
├── SKILL.md                   # Skill 定义（触发词、编排流程、输出规范）
├── workbuddy.md               # WorkBuddy 开发对话上下文
├── LICENSE
├── data/
│   └── caffeine_table.json    # 咖啡因含量与代谢参数（公开资料估算）
└── scripts/
    ├── caffeine_model.py      # 咖啡因最晚饮用时间计算
    ├── score_meals.py         # 餐品组合多目标打分
    └── recommend.py           # 主流程 CLI（可离线自测）
```

---

## 🎯 目标用户

- **加班/赶 ddl 的程序员**：深夜既要提神又要保证睡眠质量
- **赶作业、通宵复习的学生**：预算敏感 + 时间约束
- **健身人群**：深夜想吃又不想破坏当日热量目标
- **所有选择困难症**：一句话搞定，不用翻十分钟菜单

---

## 🗺️ 路线图

- [x] `v0.1` MVP：时间约束 + 营养 + 用券 + 咖啡因截止时间
- [ ] `v0.2` 多人加班拼单：AA 分摊 + 拆单最优解
- [ ] `v0.3` 定时播报：结合活动日历与券到期提醒
- [ ] `v0.4` 个人偏好记忆：口味/忌口持久化

---

## ⚠️ 免责声明

- 本项目为**麦当劳程序员节创意开发大赛参赛作品**，由参赛者独立开发，**非麦当劳官方产品**。
- 营养与咖啡因数据为公开资料估算值，**仅供参考**，不构成医疗、营养或其他专业建议。
- 餐品信息、价格及供应状态**以麦当劳官方渠道实时结果为准**。
- 本项目不包含任何真实 Token、密钥或他人个人信息。

---

## 📄 License

[MIT](./LICENSE) © 2026 Aurora-QIU0
