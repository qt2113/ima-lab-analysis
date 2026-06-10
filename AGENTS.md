
# AGENTS.md — IMA Lab Equipment Borrowing Intelligence Platform

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

## 注意事项

- **DatabaseManager 是单例**，跨模块共享，不要在函数内重复实例化。
- **Streamlit Cloud 文件系统只读** — 数据库文件默认放在项目目录，对于只读文件系统需回退到 `/tmp/` 路径。数据库路径在 `config/settings.py` 中可配置。
- `service-account-key.json` 包含 Google API 凭证，已在 `.gitignore` 中排除。
