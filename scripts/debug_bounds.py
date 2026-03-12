import sqlite3

import pandas as pd


def main() -> None:
    conn = sqlite3.connect("item_analysis.db")
    try:
        row = conn.execute("select min(Start), max(Start) from unified_records").fetchone()
        print("sql min/max Start:", row)

        df = pd.read_sql("select Start, source from unified_records", conn)
    finally:
        conn.close()

    s = (
        df["Start"]
        .astype(str)
        .replace({"None": pd.NA, "nan": pd.NA, "NaT": pd.NA, "nat": pd.NA})
    )
    df["Start_parsed"] = pd.to_datetime(s, format="mixed", errors="coerce")

    print("parsed min/max:", df["Start_parsed"].min(), df["Start_parsed"].max())
    print("top 10 earliest parsed:")
    print(
        df.sort_values("Start_parsed")
        .head(10)[["Start", "Start_parsed", "source"]]
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()

