#!/usr/bin/env python3
"""
Google Sheets连接诊断工具
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("Google Sheets 连接诊断工具")
print("=" * 70)

# 测试1: 检查secrets.toml是否存在
print("\n[测试 1/5] 检查配置文件...")
secrets_file = Path('.streamlit/secrets.toml')
if secrets_file.exists():
    print("✅ secrets.toml 文件存在")
else:
    print("❌ secrets.toml 文件不存在！")
    print("   请先创建: cp .streamlit/secrets.toml.example .streamlit/secrets.toml")
    sys.exit(1)

# 测试2: 尝试读取配置
print("\n[测试 2/5] 读取Google凭据...")
try:
    from config.auth import GoogleAuthConfig
    creds_info = GoogleAuthConfig.get_service_account_info()
    print("✅ 成功读取Service Account配置")
    print(f"   项目ID: {creds_info.get('project_id', 'N/A')}")
    print(f"   客户端邮箱: {creds_info.get('client_email', 'N/A')}")
except Exception as e:
    print(f"❌ 读取配置失败: {e}")
    print("\n建议检查:")
    print("1. secrets.toml 格式是否正确")
    print("2. private_key 中的 \\n 是否保留")
    sys.exit(1)

# 测试3: 检查必需字段
print("\n[测试 3/5] 验证必需字段...")
required_fields = ['type', 'project_id', 'private_key', 'client_email', 'client_id']
missing_fields = [f for f in required_fields if not creds_info.get(f)]
if missing_fields:
    print(f"❌ 缺少必需字段: {', '.join(missing_fields)}")
    sys.exit(1)
else:
    print("✅ 所有必需字段都存在")

# 测试4: 尝试创建Google API凭据
print("\n[测试 4/5] 创建Google API凭据...")
try:
    from google.oauth2.service_account import Credentials
    scopes = GoogleAuthConfig.get_scopes()
    credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
    print("✅ 成功创建Google API凭据")
except Exception as e:
    print(f"❌ 创建凭据失败: {e}")
    print("\n可能的原因:")
    print("1. private_key 格式不正确（检查换行符 \\n）")
    print("2. JSON格式有误")
    sys.exit(1)

# 测试5: 尝试连接Google Sheets
print("\n[测试 5/5] 连接Google Sheets...")
try:
    import gspread
    client = gspread.authorize(credentials)
    print("✅ 成功连接到Google Sheets API")
    
    # 尝试打开特定的Sheet
    print("\n正在尝试打开目标Sheet...")
    from config.settings import GOOGLE_SHEET_ID
    print(f"   Sheet ID: {GOOGLE_SHEET_ID}")
    
    workbook = client.open_by_key(GOOGLE_SHEET_ID)
    print(f"✅ 成功打开工作簿: {workbook.title}")
    
    # 列出所有工作表
    print(f"\n   可用的工作表:")
    for sheet in workbook.worksheets():
        print(f"   - {sheet.title} ({sheet.row_count} 行 x {sheet.col_count} 列)")
    
    # 检查目标Sheet是否存在
    from config.settings import TARGET_SHEETS
    print(f"\n   目标工作表: {TARGET_SHEETS}")
    for target in TARGET_SHEETS:
        found = any(s.title == target for s in workbook.worksheets())
        if found:
            print(f"   ✅ 找到: {target}")
        else:
            print(f"   ❌ 未找到: {target}")
    
except gspread.exceptions.APIError as e:
    print(f"❌ Google API错误: {e}")
    print("\n可能的原因:")
    print("1. Service Account邮箱未添加到Google Sheet")
    print(f"   请将以下邮箱添加到Sheet的共享列表:")
    print(f"   {creds_info.get('client_email')}")
    print("2. Google Sheets API 未启用")
    print("   在Google Cloud Console启用: Google Sheets API")
    sys.exit(1)
except gspread.exceptions.SpreadsheetNotFound:
    print(f"❌ 找不到指定的Sheet")
    print(f"   Sheet ID: {GOOGLE_SHEET_ID}")
    print("\n建议:")
    print("1. 检查 config/settings.py 中的 GOOGLE_SHEET_ID 是否正确")
    print("2. 确认该Sheet已分享给Service Account")
    sys.exit(1)
except Exception as e:
    print(f"❌ 连接失败: {e}")
    print(f"   错误类型: {type(e).__name__}")
    import traceback
    print("\n详细错误:")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ 所有测试通过！Google Sheets连接正常")
print("=" * 70)
print("\n下一步:")
print("1. 运行 python init_data.py 初始化数据")
print("2. 运行 streamlit run app/main.py 启动应用")
