"""
实时数据加载器 - 从Google Sheets拉取实时借用记录
"""
import pandas as pd
import re
import gspread
from google.oauth2.service_account import Credentials

from config.settings import GOOGLE_SHEET_ID, TARGET_SHEETS
from config.auth import GoogleAuthConfig
from data.loaders.category_mapper import mapper


class RealtimeDataLoader:
    """实时数据加载器"""
    
    @staticmethod
    def _strip_number(item_name: str) -> str:
        """去除物品名称末尾的编号"""
        if pd.isna(item_name):
            return ""
        return re.sub(r'\s+\d+$', '', str(item_name)).strip()
    
    def _connect_google_sheets(self) -> gspread.Client:
        """建立Google Sheets连接"""
        service_account_info = GoogleAuthConfig.get_service_account_info()
        scopes = GoogleAuthConfig.get_scopes()
        
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=scopes
        )
        
        return gspread.authorize(credentials)
    
    def _fetch_sheet_data(self, sheet_name: str) -> pd.DataFrame:
        """
        从指定Sheet拉取数据
        
        Args:
            sheet_name: Sheet名称
            
        Returns:
            原始数据DataFrame
        """
        try:
            client = self._connect_google_sheets()
            workbook = client.open_by_key(GOOGLE_SHEET_ID)
            
            # 查找目标Sheet
            target_sheet = None
            for sheet in workbook.worksheets():
                if sheet.title == sheet_name:
                    target_sheet = sheet
                    break
            
            if not target_sheet:
                print(f"⚠️ 未找到Sheet: {sheet_name}")
                return pd.DataFrame()
            
            # 获取数据
            data = target_sheet.get_all_records()
            df = pd.DataFrame(data)
            df['sheet_source'] = sheet_name
            
            print(f"✅ 从 {sheet_name} 拉取 {len(df)} 行原始数据")
            return df
            
        except Exception as e:
            print(f"❌ 拉取 {sheet_name} 失败: {e}")
            return pd.DataFrame()
    
    def _clean_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理和标准化列名"""
        # 清理列名
        df.columns = [str(col).strip() for col in df.columns]
        
        # 修复常见的列名问题
        column_fixes = {}
        
        # 修复第一列（通常是NetID）
        if len(df.columns) > 0 and ('Unnamed:' in df.columns[0] or df.columns[0] == ''):
            column_fixes[df.columns[0]] = 'NetID'
        
        # 修复Equipment Name列
        for col in df.columns:
            if 'Equipment Name' in col:
                column_fixes[col] = 'Equipment Name'
        
        if column_fixes:
            df = df.rename(columns=column_fixes)
        
        return df
    
    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证数据完整性"""
        required_cols = ['Time', 'NetID', 'Equipment Name', 'Code', 'Action']
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"缺少必要列: {missing_cols}")
        
        # 删除关键列为空的行
        df = df.dropna(subset=required_cols).copy()
        
        # 转换时间列
        df['Time'] = pd.to_datetime(
            df['Time'], 
            format='%m/%d/%Y %H:%M:%S', 
            errors='coerce'
        )
        
        return df
    
    def _map_category(self, row: pd.Series) -> str:
        """
        映射Category（先尝试Code，再尝试Name）
        
        Args:
            row: 数据行
            
        Returns:
            Category名称
        """
        code = str(row['Code']).strip()
        name_with_num = str(row['Equipment Name']).strip()
        name_stripped = self._strip_number(name_with_num)
        
        # 使用统一的mapper
        return mapper.get_category(code=code, name=name_stripped)
    
    def _process_borrow_records(self, group: pd.DataFrame) -> pd.DataFrame:
        """
        处理单个物品的借还记录
        
        Args:
            group: 单个物品的所有操作记录
            
        Returns:
            借用记录DataFrame
        """
        # 筛选有效操作
        valid_actions = group[
            group['Action'].isin(['Check Out', 'Check In'])
        ].sort_values('Time').reset_index(drop=True)
        
        if valid_actions.empty:
            return pd.DataFrame()
        
        records = []
        check_outs = valid_actions[valid_actions['Action'] == 'Check Out'].copy()
        check_ins = valid_actions[valid_actions['Action'] == 'Check In'].copy()
        
        # 匹配Check Out和Check In
        for _, co_row in check_outs.iterrows():
            # 查找对应的Check In
            potential_ci = check_ins[check_ins['Time'] > co_row['Time']]
            
            if not potential_ci.empty:
                ci_row = potential_ci.iloc[0]
                
                # 计算时长
                time_diff = ci_row['Time'] - co_row['Time']
                duration_hours = time_diff.total_seconds() / 3600
                
                records.append({
                    'Start': co_row['Time'],
                    'finished': ci_row['Time'],
                    'duration (hours)': round(duration_hours, 0),
                    'item name(with num)': co_row['Equipment Name'],
                    'Category': co_row['Category'],
                    'source': 'realtime',
                    'sheet_source': co_row['sheet_source']
                })
                
                # 移除已匹配的Check In
                check_ins = check_ins[check_ins['Time'] != ci_row['Time']]
            else:
                # 未归还的记录（当前借出状态）
                records.append({
                    'Start': co_row['Time'],
                    'finished': pd.NaT,
                    'duration (hours)': None,
                    'item name(with num)': co_row['Equipment Name'],
                    'Category': co_row['Category'],
                    'source': 'realtime',
                    'sheet_source': co_row['sheet_source']
                })
        
        return pd.DataFrame(records)
    
    def load(self, sheet_names: list = None) -> pd.DataFrame:
        """
        加载实时数据
        
        Args:
            sheet_names: 要拉取的Sheet名称列表，默认使用配置中的TARGET_SHEETS
            
        Returns:
            清洗后的DataFrame
        """
        if sheet_names is None:
            sheet_names = TARGET_SHEETS
        
        print(f"🌐 开始从Google Sheets拉取实时数据...")
        
        all_data = []
        
        # 拉取各个Sheet
        for sheet_name in sheet_names:
            df_sheet = self._fetch_sheet_data(sheet_name)
            if not df_sheet.empty:
                all_data.append(df_sheet)
        
        if not all_data:
            print("⚠️ 未拉取到任何数据")
            return pd.DataFrame()
        
        # 合并所有Sheet数据
        df_raw = pd.concat(all_data, ignore_index=True)
        print(f"📊 共拉取 {len(df_raw)} 行原始数据")
        
        # 清理和验证
        df_raw = self._clean_columns(df_raw)
        df_raw = self._validate_data(df_raw)
        
        # 映射Category
        df_raw['Category'] = df_raw.apply(self._map_category, axis=1)
        
        # 处理借用记录（按物品分组）
        df_unified = df_raw.groupby(
            ['NetID', 'Equipment Name'], 
            group_keys=False
        ).apply(self._process_borrow_records).reset_index(drop=True)
        
        if df_unified.empty:
            print("⚠️ 未生成有效的借用记录")
            return pd.DataFrame()
        
        # 生成不带编号的物品名称
        df_unified['item name'] = df_unified['item name(with num)'].apply(
            self._strip_number
        )
        
        # 四舍五入duration
        if 'duration (hours)' in df_unified.columns:
            df_unified['duration (hours)'] = (
                pd.to_numeric(df_unified['duration (hours)'], errors='coerce')
                .round(0)
                .astype('Int64')
            )
        
        print(f"✅ 成功处理 {len(df_unified)} 条借用记录")
        
        return df_unified


# 便捷函数
def load_realtime_data(sheet_names: list = None) -> pd.DataFrame:
    """加载实时数据的快捷函数"""
    loader = RealtimeDataLoader()
    return loader.load(sheet_names)
