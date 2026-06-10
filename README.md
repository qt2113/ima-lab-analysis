# IMA Lab 物品借用分析平台

基于 Streamlit 的实验室设备借用数据分析工具，支持历史数据（Excel）和实时数据（Google Sheets），使用 D3.js 渲染交互式图表。

## 项目架构

```
config/          # 配置层：settings.py(核心配置)、auth.py(Google认证)、sheet_config.py
data/            # 数据层：database.py(SQLite单例)、loaders/(历史/实时加载器)、processors/(清洗)
analyzer.py      # 分析层：所有分析函数的唯一入口（概览/舰队健康/类别/单品/模式）
ai/              # AI层：client.py(Cloudflare+Groq)、chat.py(会话状态)、prompts.py
app/main.py      # 表现层：Streamlit UI + 内联 D3.js 图表
```

**关键约定：**
- **D3.js 是唯一图表方案**，不要引入 Plotly 或其他图表库
- **analyzer.py 是唯一分析入口**，不要再创建新的 strategy 类
- **analysis/strategies/ 目录已废弃**，不要再引用或恢复
- **DatabaseManager 是单例**，通过 `DatabaseManager()` 获取，不要直接 new
- **Streamlit Cloud 部署**，文件系统只读，写入路径用 `/tmp/` 回退

## 数据流

```
Excel (历史) ──→ SQLite ←── Google Sheets (实时)
                    ↓
              analyzer.py
                    ↓
            D3.js 图表 (内联 HTML)
```

## 快速开始

```bash
pip install -r requirements.txt
streamlit run app/main.py
```

## 五个分析标签页

| Tab | 功能 |
|-----|------|
| Overview | KPI 概览、月度借用趋势、类别 treemap |
| Fleet Health | 物品利用率排行、需求×持有时长象限图 |
| Category | 单类别深度分析（频次/时长/月趋势） |
| Single Item | 单品甘特图/日历热力图/月度统计 |
| Patterns | 借用时间热力图（星期×小时）、分布图 |

## 配置

- Google Sheet ID 在 [config/settings.py](config/settings.py) 的 `GOOGLE_SHEET_ID`
- 用户自定义 Sheet 通过侧边栏 UI 配置，持久化到 `/tmp/ima_lab_sheet_config.toml`
- AI 默认使用 Cloudflare Workers AI，Groq 为 fallback（见 [ai/client.py](ai/client.py)）
- 敏感凭证：`.streamlit/secrets.toml`（gitignored），模板见 `.streamlit/secrets.toml.example`

## 部署

Streamlit Cloud：仓库 → main 分支 → `app/main.py`，Secrets 在应用设置中配置。
