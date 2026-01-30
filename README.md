# 🔬 IMA Lab 物品借用分析平台

基于Streamlit的现代化数据分析工具，支持历史数据和实时数据的灵活分析。

---

## ✨ 功能特性

### 📊 三种分析模式
1. **单品分析** - 查看单个物品的借用时间线
2. **Top N分析** - 分析高频借用物品的趋势
3. **时间线分析** - 日粒度的物品状态追踪

### 🔄 灵活的数据模式
- **全部数据模式**：分析历史 + 实时数据
- **实时模式**：只分析当前学期数据（自动排除Inventory）

### 🔒 安全的数据管理
- Google Service Account认证（无需个人账号）
- 密钥通过环境变量管理，不泄露到代码
- 支持本地开发和云端部署

---

## 📁 项目结构

```
ima-lab-refactored/
├── app/
│   └── main.py              # Streamlit主应用
├── config/
│   ├── settings.py          # 项目配置
│   └── auth.py              # Google认证配置
├── data/
│   ├── database.py          # 数据库管理
│   ├── loaders/             # 数据加载器
│   │   ├── category_mapper.py
│   │   ├── historical_loader.py
│   │   └── realtime_loader.py
│   └── processors/          # 数据处理器
│       └── data_processor.py
├── analysis/
│   └── strategies/          # 分析策略
│       ├── base_strategy.py
│       ├── single_item_strategy.py
│       ├── topn_strategy.py
│       └── duration_strategy.py
├── .streamlit/
│   └── secrets.toml.example # 密钥配置示例
├── requirements.txt         # 依赖包
├── .gitignore              # Git排除文件
└── README.md               # 本文档
```

---

## 🚀 快速开始

### 1️⃣ 克隆项目

```bash
git clone https://github.com/yourusername/ima-lab-refactored.git
cd ima-lab-refactored
```

### 2️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

### 3️⃣ 配置Google Service Account

#### 创建Service Account
1. 访问 [Google Cloud Console](https://console.cloud.google.com)
2. 创建新项目或选择现有项目
3. 启用 **Google Sheets API** 和 **Google Drive API**
4. 创建凭据 → **Service Account**
5. 下载JSON密钥文件

#### 授权访问Sheet
1. 打开你的Google Sheet
2. 点击 "Share"
3. 将Service Account邮箱添加为查看者/编辑者
   ```
   例如：ima-lab-bot@your-project.iam.gserviceaccount.com
   ```

### 4️⃣ 配置密钥

```bash
# 复制配置示例
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# 编辑secrets.toml，填入你的Service Account信息
nano .streamlit/secrets.toml
```

**secrets.toml 示例:**
```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@project.iam.gserviceaccount.com"
# ... 其他字段
```

### 5️⃣ 准备数据文件

将以下文件放在项目根目录：
- `historical_raw_data.xlsx` - 历史借用记录
- `code_to_category_map.xlsx` - Code到Category的映射表

### 6️⃣ 运行应用

```bash
streamlit run app/main.py
```

应用将在浏览器中自动打开：`http://localhost:8501`

---

## 🌐 部署到Streamlit Cloud

### 1️⃣ 推送到GitHub

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

**⚠️ 确保敏感文件已排除：**
```bash
# 检查是否有敏感文件
git status

# 不应该看到：
# - secrets.toml
# - *.json (除了示例文件)
# - *.xlsx (数据文件)
```

### 2️⃣ 部署到Streamlit Cloud

1. 访问 [share.streamlit.io](https://share.streamlit.io)
2. 用GitHub账号登录
3. 点击 "New app"
4. 选择你的仓库 → `main` 分支 → `app/main.py`
5. 点击 "Deploy"

### 3️⃣ 配置Secrets

1. 打开应用设置 → **Secrets** 选项卡
2. 粘贴你的 `secrets.toml` 内容
3. 保存 → 应用自动重启

### 4️⃣ 分享应用

复制应用URL分享给团队：
```
https://your-app-name.streamlit.app
```

---

## 🔧 配置说明

### config/settings.py

核心配置文件，包含：
- Google Sheet ID
- 数据文件路径
- 类别列表
- 时间周期定义

**修改Google Sheet ID：**
```python
GOOGLE_SHEET_ID = "your-sheet-id"  # 从Sheet URL中获取
TARGET_SHEETS = ["Fall 2025", "Spring 2026"]  # 要抓取的Sheet名称
```

### 数据模式切换

在应用侧边栏选择：
- **📚 全部数据**：分析所有历史+实时记录
- **🔄 仅实时数据**：只分析当前学期（自动排除Inventory）

---

## 📊 使用指南

### 单品分析
1. 选择类别
2. 搜索或选择物品（带编号）
3. 可选：设置时间范围
4. 点击"运行分析"

**示例用途：**
- 查看某台相机的借用历史
- 确认设备是否可用

### Top N分析
1. 选择类别和Top N数量
2. 选择时间周期（日/周/月/年）
3. 可选：限定物品名称
4. 点击"运行分析"

**示例用途：**
- 发现最受欢迎的设备
- 分析借用趋势

### 时间线分析
1. 选择类别和物品
2. 设置分析时间范围
3. 点击"运行分析"

**示例用途：**
- 查看设备使用率
- 统计借出天数

---

## 🛠️ 开发指南

### 添加新的分析策略

1. 在 `analysis/strategies/` 创建新文件
2. 继承 `AnalysisStrategy` 基类
3. 实现 `analyze()` 和 `visualize()` 方法

**示例：**
```python
from analysis.strategies.base_strategy import AnalysisStrategy

class MyAnalysis(AnalysisStrategy):
    def analyze(self, **kwargs):
        df = self.load_data(...)
        # 你的分析逻辑
        return {'success': True, 'data': result}
    
    def visualize(self, result):
        # 创建Plotly图表
        return fig
```

### 修改数据加载逻辑

所有数据加载器位于 `data/loaders/`：
- `historical_loader.py` - 历史数据
- `realtime_loader.py` - Google Sheets实时数据
- `category_mapper.py` - 类别映射

---

## 🔍 故障排查

### 问题：无法连接Google Sheets

**解决方案：**
1. 检查Service Account邮箱是否添加到Sheet
2. 确认API已启用（Sheets + Drive）
3. 验证secrets.toml配置正确

### 问题：数据加载失败

**解决方案：**
1. 检查数据文件是否存在
2. 确认文件格式正确（Excel或Google Sheets）
3. 查看控制台错误信息

### 问题：部署后无法访问

**解决方案：**
1. 确认Secrets已配置
2. 检查requirements.txt包含所有依赖
3. 查看Streamlit Cloud日志

---

## 📝 更新日志

### v2.0.0 (2025-01-29)
- ✨ 完全重构，模块化设计
- ✨ 迁移到Streamlit（替代Tkinter）
- ✨ 添加实时数据模式
- ✨ 使用Service Account替代OAuth
- ✨ 优化数据加载和缓存
- ✨ 改进可视化效果

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

## 📧 联系方式

如有问题，请联系：your-email@example.com
