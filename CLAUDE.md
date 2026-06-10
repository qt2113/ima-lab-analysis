
# CLAUDE.md — IMA Lab Equipment Borrowing Intelligence Platform

## 项目定位

IMA 实验室设备借用分析平台：从 Google Sheets / Excel 拉取设备借用记录，存入 SQLite，通过分析引擎生成指标，最终以交互式 D3.js 图表在 Streamlit 中呈现。

## 架构分层

```
config/       — 配置：Google Sheet ID、数据库路径、sheet 管理
data/         — 数据层：DatabaseManager（单例）、loader、processor
analysis/     — 分析层：analyzer.py 是唯一分析入口
ai/           — AI 聊天模块（prompts / client / chat）
app/          — 表现层：Streamlit 页面，D3.js 图表渲染
```

## 关键约定

- **D3.js (v7 CDN) 是唯一的图表方案** — 所有可视化通过 D3.js 内联渲染，不要引入 Plotly 或其他图表库。
- **`analyzer.py` 是唯一的分析入口** — 所有指标计算、聚合、统计逻辑集中在这里，不要新建 strategy 类或在页面中散布分析逻辑。
- **不要再使用 `analysis/strategies/` 下的旧 Plotly strategy 类** — 这些是待清理的遗留代码，新功能一律走 analyzer.py。
- **DatabaseManager 是单例** — 通过 `data.database` 中的全局 `db` 实例访问，不要新建连接。

## 常用命令

```bash
streamlit run app/main.py          # 启动开发服务器
python init_data.py                 # 初始化数据库（从 Excel 导入）
python update_realtime.py           # 从 Google Sheets 更新实时数据
python test_google_connection.py    # 测试 Google Sheets 连接
```

## 数据流

```
Excel (.xlsx) ──→ init_data.py ──→ item_analysis.db (SQLite)
Google Sheets ──→ update_realtime.py ──→ item_analysis.db (SQLite)
                                                 │
                              analyzer.py ←──────┘
                                    │
                              app/main.py (Streamlit)
                                    │
                              D3.js 图表 (浏览器)
```

## 部署

部署在 Streamlit Cloud，配置通过 `.streamlit/secrets.toml` 和 `.streamlit/user_settings.json` 管理。Google 服务账号密钥放在 `.streamlit/service-account-key.json`。

## AI 聊天架构

```
用户提问 ──→ ai/chat.py:_classify_intent() ──→ 意图 → 数据模块
                                                    │
                   ai/chat.py:_query_module() ←─────┘
                          │
                   analyzer.py (overview / fleet_health / temporal_patterns / ...)
                          │
                   格式化数据注入 system prompt ──→ Cloudflare 70B 模型 ──→ 回答
```

### AI 聊天关键设计

- **意图分类 + 定向查询**（不是 AI 自主 tool calling，也不是预计算全量 dump）
  - `ai/chat.py:_classify_intent()` — 关键词匹配用户问题，决定查哪些数据模块
  - `ai/chat.py:_query_module()` — 调用 analyzer 执行查询，返回结构化数据
  - `ai/chat.py:build_data_context()` — 将查询结果拼成 AI 可读的 JSON 上下文
- **聊天模型**: `CLOUDFLARE_MODEL_ANALYSIS` (@cf/meta/llama-3.3-70b-instruct-fp8-fast)，不要用 1B 小模型做聊天，它无法正确理解数据
- **摘要模型**: `CLOUDFLARE_MODEL_CHAT` (@cf/meta/llama-3.2-1b-instruct)，用于定期压缩对话历史
- 数据上下文**每轮动态查询**注入，不是会话启动时的一次性注入
- AI Insight 按钮（`app/main.py:ai_button()`）**不走** `build_data_context`，它的数据在调用处直接拼进 prompt

### 已知待改进

1. `category_stats` / `item_detail` / `search_items` 查询模块已实现，但未挂载到意图规则
2. 同一轮 `build_data_context` 内多次调用 `fleet_health()` / `overview()`，无模块间缓存
3. 追问上下文丢失 — 无法理解"那 Cameras 呢？"是在追问上一个话题
4. `ai/__init__.py` 导出列表过时，缺少 `build_data_context`
5. 对话历史中残留历史轮次的过期 JSON 数据，浪费 token

## 注意事项

- **DatabaseManager 是单例**，跨模块共享，不要在函数内重复实例化。
- **Streamlit Cloud 文件系统只读** — 数据库文件默认放在项目目录，对于只读文件系统需回退到 `/tmp/` 路径。数据库路径在 `config/settings.py` 中可配置。
- `service-account-key.json` 包含 Google API 凭证，已在 `.gitignore` 中排除。
- 启动 Streamlit 时用 `python -B` 避免 pyc 缓存导致的 import 错误。
