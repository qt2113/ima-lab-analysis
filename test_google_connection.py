#!/usr/bin/env python3
"""
Google Sheets连接诊断工具
"""
import sys
import logging
import traceback
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

logger.info("=" * 70)
logger.info("Google Sheets connection diagnostic")
logger.info("=" * 70)

# 测试1: 检查secrets.toml是否存在
logger.info("Test 1/5: Checking config file")
secrets_file = Path('.streamlit/secrets.toml')
if secrets_file.exists():
    logger.info("secrets.toml exists")
else:
    logger.error("secrets.toml not found")
    logger.info("Run: cp .streamlit/secrets.toml.example .streamlit/secrets.toml")
    sys.exit(1)

# 测试2: 尝试读取配置
logger.info("Test 2/5: Reading Google credentials")
try:
    from config.auth import GoogleAuthConfig
    creds_info = GoogleAuthConfig.get_service_account_info()
    logger.info(f"Service account config loaded (project: {creds_info.get('project_id', 'N/A')})")
    logger.info(f"Client email: {creds_info.get('client_email', 'N/A')}")
except Exception as e:
    logger.error(f"Failed to read config: {e}")
    logger.info("Suggestions: check secrets.toml format, ensure \\n in private_key is preserved")
    sys.exit(1)

# 测试3: 检查必需字段
logger.info("Test 3/5: Validating required fields")
required_fields = ['type', 'project_id', 'private_key', 'client_email', 'client_id']
missing_fields = [f for f in required_fields if not creds_info.get(f)]
if missing_fields:
    logger.error(f"Missing required fields: {', '.join(missing_fields)}")
    sys.exit(1)
else:
    logger.info("All required fields present")

# 测试4: 尝试创建Google API凭据
logger.info("Test 4/5: Creating Google API credentials")
try:
    from google.oauth2.service_account import Credentials
    scopes = GoogleAuthConfig.get_scopes()
    credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
    logger.info("Google API credentials created")
except Exception as e:
    logger.error(f"Failed to create credentials: {e}")
    logger.info("Possible causes: incorrect private_key format (check \\n), invalid JSON")
    sys.exit(1)

# 测试5: 尝试连接Google Sheets
logger.info("Test 5/5: Connecting to Google Sheets")
try:
    import gspread
    client = gspread.authorize(credentials)
    logger.info("Connected to Google Sheets API")

    from config.settings import GOOGLE_SHEET_ID
    logger.info(f"Opening workbook: {GOOGLE_SHEET_ID}")

    workbook = client.open_by_key(GOOGLE_SHEET_ID)
    logger.info(f"Workbook opened: {workbook.title}")

    sheet_list = [(s.title, s.row_count, s.col_count) for s in workbook.worksheets()]
    logger.info(f"Available sheets: {sheet_list}")

    from config.settings import TARGET_SHEETS
    for target in TARGET_SHEETS:
        found = any(s.title == target for s in workbook.worksheets())
        if found:
            logger.info(f"Target sheet found: {target}")
        else:
            logger.warning(f"Target sheet NOT found: {target}")

except gspread.exceptions.APIError as e:
    logger.error(f"Google API error: {e}")
    logger.info(f"Possible causes: share sheet with {creds_info.get('client_email')}, enable Google Sheets API")
    sys.exit(1)
except gspread.exceptions.SpreadsheetNotFound:
    logger.error(f"Spreadsheet not found: {GOOGLE_SHEET_ID}")
    logger.info("Check GOOGLE_SHEET_ID in config/settings.py and sharing permissions")
    sys.exit(1)
except Exception as e:
    logger.error(f"Connection failed: {e} ({type(e).__name__})")
    traceback.print_exc()
    sys.exit(1)

logger.info("=" * 70)
logger.info("All tests passed! Google Sheets connection OK")
logger.info("=" * 70)
logger.info("Next: python init_data.py → streamlit run app/main.py")
