import sqlite3
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def main() -> None:
    conn = sqlite3.connect("item_analysis.db")
    try:
        row = conn.execute("select min(Start), max(Start) from unified_records").fetchone()
        logger.info(f"sql min/max Start: {row}")

        df = pd.read_sql("select Start, source from unified_records", conn)
    finally:
        conn.close()

    s = (
        df["Start"]
        .astype(str)
        .replace({"None": pd.NA, "nan": pd.NA, "NaT": pd.NA, "nat": pd.NA})
    )
    df["Start_parsed"] = pd.to_datetime(s, format="mixed", errors="coerce")

    logger.info(f"parsed min/max: {df['Start_parsed'].min()} {df['Start_parsed'].max()}")
    logger.info("top 10 earliest parsed:")
    logger.info(
        df.sort_values("Start_parsed")
        .head(10)[["Start", "Start_parsed", "source"]]
        .to_string(index=False)
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    main()
