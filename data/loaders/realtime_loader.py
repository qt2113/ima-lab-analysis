"""
Realtime data loader - fetches borrow records from Google Sheets.
"""
import pandas as pd
import re
import gspread
from google.oauth2.service_account import Credentials

from config.settings import GOOGLE_SHEET_ID, TARGET_SHEETS
from config.auth import GoogleAuthConfig
from data.loaders.category_mapper import mapper


class RealtimeDataLoader:
    """Realtime data loader."""

    @staticmethod
    def _strip_number(item_name: str) -> str:
        """Strip trailing number from item name."""
        if pd.isna(item_name):
            return ""
        return re.sub(r"\s+\d+$", "", str(item_name)).strip()

    def _connect_google_sheets(self) -> gspread.Client:
        """Create Google Sheets connection."""
        service_account_info = GoogleAuthConfig.get_service_account_info()
        scopes = GoogleAuthConfig.get_scopes()

        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=scopes
        )

        return gspread.authorize(credentials)

    def _fetch_sheet_data(self, sheet_name: str) -> pd.DataFrame:
        """Fetch one sheet as DataFrame."""
        try:
            client = self._connect_google_sheets()
            workbook = client.open_by_key(GOOGLE_SHEET_ID)

            target_sheet = None
            for sheet in workbook.worksheets():
                if sheet.title == sheet_name:
                    target_sheet = sheet
                    break

            if not target_sheet:
                print(f"[warn] Sheet not found: {sheet_name}")
                return pd.DataFrame()

            data = target_sheet.get_all_records()
            df = pd.DataFrame(data)
            df["sheet_source"] = sheet_name

            print(f"[ok] Fetched {len(df)} rows from {sheet_name}")
            return df
        except Exception as e:
            print(f"[error] Fetch {sheet_name} failed: {e}")
            return pd.DataFrame()

    def _clean_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names."""
        df.columns = [str(col).strip() for col in df.columns]

        column_fixes = {}
        if len(df.columns) > 0 and ("Unnamed:" in df.columns[0] or df.columns[0] == ""):
            column_fixes[df.columns[0]] = "NetID"

        for col in df.columns:
            if "Equipment Name" in col:
                column_fixes[col] = "Equipment Name"

        if column_fixes:
            df = df.rename(columns=column_fixes)

        return df

    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate required columns and parse time."""
        required_cols = ["Time", "NetID", "Equipment Name", "Code", "Action"]

        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        df = df.dropna(subset=required_cols).copy()

        df["Time"] = pd.to_datetime(
            df["Time"],
            format="%m/%d/%Y %H:%M:%S",
            errors="coerce"
        )

        return df

    def _map_category(self, row: pd.Series) -> str:
        """Map category using code and name."""
        code = str(row["Code"]).strip()
        name_with_num = str(row["Equipment Name"]).strip()
        name_stripped = self._strip_number(name_with_num)
        return mapper.get_category(code=code, name=name_stripped)

    def _process_borrow_records(self, group: pd.DataFrame) -> pd.DataFrame:
        """Build borrow/return records for a single item group."""
        valid_actions = group[group["Action"].isin(["Check Out", "Check In"])].sort_values("Time")
        valid_actions = valid_actions.reset_index(drop=True)

        if valid_actions.empty:
            return pd.DataFrame()

        records = []
        open_checkouts = []

        # FIFO match by time
        for _, row in valid_actions.iterrows():
            if row["Action"] == "Check Out":
                open_checkouts.append(row)
                continue

            if open_checkouts:
                co_row = open_checkouts.pop(0)
                time_diff = row["Time"] - co_row["Time"]
                duration_hours = time_diff.total_seconds() / 3600

                records.append({
                    "Start": co_row["Time"],
                    "finished": row["Time"],
                    "duration (hours)": round(duration_hours, 0),
                    "item name(with num)": co_row["Equipment Name"],
                    "Category": co_row["Category"],
                    "source": "realtime",
                    "sheet_source": co_row["sheet_source"]
                })
            else:
                # Extra Check In without matching Check Out
                continue

        # Remaining open checkouts
        for co_row in open_checkouts:
            records.append({
                "Start": co_row["Time"],
                "finished": pd.NaT,
                "duration (hours)": None,
                "item name(with num)": co_row["Equipment Name"],
                "Category": co_row["Category"],
                "source": "realtime",
                "sheet_source": co_row["sheet_source"]
            })

        return pd.DataFrame(records)

    def load(self, sheet_names: list = None) -> pd.DataFrame:
        """Load realtime data from Google Sheets."""
        if sheet_names is None:
            sheet_names = TARGET_SHEETS

        print("[info] Start fetching realtime data from Google Sheets...")

        all_data = []
        for sheet_name in sheet_names:
            df_sheet = self._fetch_sheet_data(sheet_name)
            if not df_sheet.empty:
                all_data.append(df_sheet)

        if not all_data:
            print("[warn] No data fetched from sheets")
            return pd.DataFrame()

        df_raw = pd.concat(all_data, ignore_index=True)
        print(f"[info] Total raw rows: {len(df_raw)}")

        df_raw = self._clean_columns(df_raw)
        df_raw = self._validate_data(df_raw)

        df_raw["Category"] = df_raw.apply(self._map_category, axis=1)

        df_unified = (
            df_raw.groupby(["NetID", "Equipment Name"], group_keys=False)
            .apply(self._process_borrow_records)
            .reset_index(drop=True)
        )

        if df_unified.empty:
            print("[warn] No valid borrow records produced")
            return pd.DataFrame()

        df_unified["item name"] = df_unified["item name(with num)"].apply(self._strip_number)

        if "duration (hours)" in df_unified.columns:
            df_unified["duration (hours)"] = (
                pd.to_numeric(df_unified["duration (hours)"], errors="coerce")
                .round(0)
                .astype("Int64")
            )

        print(f"[ok] Unified borrow records: {len(df_unified)}")
        return df_unified


def load_realtime_data(sheet_names: list = None) -> pd.DataFrame:
    """Convenience wrapper to load realtime data."""
    loader = RealtimeDataLoader()
    return loader.load(sheet_names)
