# 🚀 IMA Lab 部署指南

完整的部署说明，从零开始到在线访问。

---

## 📋 前置准备清单

在开始之前，请确保你有：

- [ ] Python 3.8+ 已安装
- [ ] pip 已安装
- [ ] Google账号（用于创建Service Account）
- [ ] GitHub账号（用于部署）
- [ ] 历史数据Excel文件
- [ ] Code映射Excel文件

---

## 🔧 本地开发环境配置

### 步骤1: 克隆项目

```bash
# 如果从GitHub克隆
git clone https://github.com/yourusername/ima-lab-refactored.git
cd ima-lab-refactored

# 或者如果是本地项目
cd ima-lab-refactored
```

### 步骤2: 创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 步骤3: 安装依赖

```bash
pip install -r requirements.txt
```

### 步骤4: 配置Google Service Account

#### 4.1 创建Service Account

1. 访问 [Google Cloud Console](https://console.cloud.google.com)
2. 创建新项目：
   - 点击顶部项目选择器
   - 点击"新建项目"
   - 项目名称：`IMA Lab Analysis`
   - 点击"创建"

3. 启用API：
   - 在左侧菜单选择"API和服务" → "库"
   - 搜索并启用 **Google Sheets API**
   - 搜索并启用 **Google Drive API**

4. 创建Service Account：
   - 左侧菜单："API和服务" → "凭据"
   - 点击"创建凭据" → "Service Account"
   - Service Account名称：`ima-lab-bot`
   - 角色：无需选择（只需读取Sheet）
   - 点击"完成"

5. 生成密钥：
   - 在Service Accounts列表中找到刚创建的账号
   - 点击账号 → "密钥"选项卡
   - "添加密钥" → "创建新密钥"
   - 类型：JSON
   - 点击"创建"
   - **保存下载的JSON文件**

#### 4.2 授权访问Google Sheet

1. 打开JSON文件，找到 `client_email` 字段：
   ```
   ima-lab-bot@your-project.iam.gserviceaccount.com
   ```

2. 打开你的Google Sheet
3. 点击右上角"分享"按钮
4. 将上述邮箱地址添加为**查看者**或**编辑者**
5. 点击"发送"

#### 4.3 配置本地密钥

```bash
# 创建.streamlit目录
mkdir -p .streamlit

# 复制配置模板
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

编辑 `.streamlit/secrets.toml`，填入JSON文件内容：

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"                    # 从JSON复制
private_key_id = "your-key-id"                   # 从JSON复制
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"  # 从JSON复制（保持换行符）
client_email = "ima-lab-bot@your-project.iam.gserviceaccount.com"  # 从JSON复制
client_id = "123456789"                          # 从JSON复制
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."  # 从JSON复制
```

⚠️ **重要**: 确保 `private_key` 的换行符 `\n` 保留！

### 步骤5: 配置项目

编辑 `config/settings.py`，修改Google Sheet ID：

```python
GOOGLE_SHEET_ID = "1gMibpWSaxtfPyTq4FJ8wqdpE0ZMrWgEhmP-ReApwg-4"  # 替换为你的Sheet ID
```

**如何获取Sheet ID?**
从Google Sheet URL中提取：
```
https://docs.google.com/spreadsheets/d/[这里是Sheet ID]/edit
```

### 步骤6: 准备数据文件

将以下文件放在项目根目录：
```
ima-lab-refactored/
├── historical_raw_data.xlsx        # 历史数据
└── code_to_category_map.xlsx      # 映射表
```

### 步骤7: 初始化数据库

```bash
python init_data.py
```

预期输出：
```
============================================================
IMA Lab 数据初始化
============================================================

[1/2] 正在加载历史数据...
✅ 历史数据加载成功：1234 条记录

[2/2] 正在从Google Sheets拉取实时数据...
✅ 实时数据加载成功：56 条记录

============================================================
数据库统计
============================================================
总记录数: 1290
...
```

### 步骤8: 运行应用

```bash
streamlit run app/main.py
```

应用将在浏览器自动打开：`http://localhost:8501`

---

## 🌐 部署到Streamlit Cloud

### 步骤1: 准备GitHub仓库

```bash
# 初始化Git（如果还没有）
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: IMA Lab Analysis Platform"

# 创建GitHub仓库后，推送
git remote add origin https://github.com/yourusername/ima-lab.git
git branch -M main
git push -u origin main
```

⚠️ **检查敏感文件是否排除：**
```bash
git status

# 不应该看到：
# - .streamlit/secrets.toml
# - *.json
# - *.xlsx
# - *.db
```

### 步骤2: 部署到Streamlit Cloud

1. 访问 [share.streamlit.io](https://share.streamlit.io)
2. 用GitHub账号登录
3. 点击 **"New app"**
4. 配置：
   - Repository: `yourusername/ima-lab`
   - Branch: `main`
   - Main file path: `app/main.py`
5. 点击 **"Deploy"**

### 步骤3: 配置Secrets

⚠️ **这是最关键的步骤！**

1. 等待应用部署完成（约2-3分钟）
2. 点击右下角 **"Settings"** → **"Secrets"**
3. 粘贴你本地的 `.streamlit/secrets.toml` 内容
4. 点击 **"Save"**
5. 应用会自动重启

**示例格式：**
```toml
[gcp_service_account]
type = "service_account"
project_id = "ima-lab-123456"
private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqh...\n-----END PRIVATE KEY-----\n"
client_email = "ima-lab-bot@ima-lab-123456.iam.gserviceaccount.com"
...
```

### 步骤4: 验证部署

1. 应用重启后，访问你的应用URL：
   ```
   https://yourusername-ima-lab-main-appmain-abc123.streamlit.app
   ```

2. 点击侧边栏的 **"刷新数据"** 按钮

3. 如果看到 "✅ 数据更新成功"，说明部署成功！

---

## 🔐 安全最佳实践

### 1. 保护敏感文件

确保 `.gitignore` 包含：
```gitignore
.streamlit/secrets.toml
*.json
*.db
*.xlsx
```

### 2. 定期轮换密钥

每6个月重新生成Service Account密钥：
1. 在Google Cloud Console删除旧密钥
2. 生成新密钥
3. 更新Streamlit Cloud Secrets

### 3. 最小权限原则

Service Account只需要：
- Google Sheets **只读权限**
- 只分享必要的Sheet

### 4. 添加访问密码（可选）

在 `secrets.toml` 添加：
```toml
[app]
password = "your-secret-password"
```

在 `app/main.py` 开头添加密码验证：
```python
import streamlit as st

def check_password():
    if 'app' in st.secrets and 'password' in st.secrets['app']:
        password = st.text_input("🔒 请输入密码", type="password")
        if password != st.secrets['app']['password']:
            st.error("密码错误")
            st.stop()

check_password()
```

---

## 🔧 维护和更新

### 更新实时数据

应用会在启动时自动更新，也可以手动运行：
```bash
python update_realtime.py
```

### 添加新的Sheet

编辑 `config/settings.py`：
```python
TARGET_SHEETS = ["Fall 2025", "Spring 2026", "Summer 2026"]  # 添加新学期
```

### 更新代码

```bash
git pull origin main
streamlit run app/main.py
```

Streamlit Cloud会自动检测GitHub更新并重新部署。

---

## 🐛 常见问题

### Q1: 运行init_data.py时报错 "未找到Google凭据"

**原因**: secrets.toml配置不正确

**解决**:
1. 确认 `.streamlit/secrets.toml` 存在
2. 检查格式是否正确（尤其是private_key的换行符）
3. 确认所有必需字段都已填写

### Q2: Streamlit Cloud部署后无法访问Google Sheets

**原因**: Secrets未配置或Service Account未授权

**解决**:
1. 确认Streamlit Cloud Secrets已配置
2. 检查Service Account邮箱是否添加到Sheet
3. 查看应用日志（Settings → Logs）

### Q3: 数据加载慢

**原因**: 数据量大或网络问题

**解决**:
1. 使用"仅实时数据"模式
2. 缩小时间范围
3. 考虑添加数据库索引

### Q4: 图表显示不正常

**原因**: 数据格式问题

**解决**:
1. 检查日期列格式
2. 确认duration (hours)为数字
3. 查看控制台错误信息

---

## 📧 获取帮助

如遇到问题：
1. 查看应用日志
2. 检查本指南的故障排查部分
3. 提交GitHub Issue
4. 联系：your-email@example.com

---

## ✅ 部署检查清单

部署前请确认：

- [ ] Python依赖已安装
- [ ] Google Service Account已创建并配置
- [ ] Service Account已添加到Google Sheet
- [ ] secrets.toml已配置（本地）
- [ ] 数据文件已准备
- [ ] 敏感文件已添加到.gitignore
- [ ] 代码已推送到GitHub
- [ ] Streamlit Cloud Secrets已配置
- [ ] 应用可以正常访问
- [ ] 数据刷新功能正常

---

祝你部署顺利！🎉
