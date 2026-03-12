import sqlite3

import pandas as pd


def main() -> None:
    item = "Sony A7 III With EF 24-105 017"
    conn = sqlite3.connect("item_analysis.db")
    try:
        print("exact counts:")
        for src in ["historical", "realtime"]:
            c = conn.execute(
                'select count(*) from unified_records where source=? and "item name(with num)"=?',
                (src, item),
            ).fetchone()[0]
            print(src, c)

        print("\nexample rows (any source):")
        rows = conn.execute(
            'select "Start", "finished", source, "item name(with num)" '
            'from unified_records where "item name(with num)"=? order by "Start" limit 8',
            (item,),
        ).fetchall()
        for r in rows:
            print(r)

        print("\nLIKE candidates (sony a7):")
        df = pd.read_sql(
            "select \"item name(with num)\" as n, source, count(*) c, "
            "min(\"Start\") mn, max(\"Start\") mx "
            "from unified_records "
            "where lower(\"item name(with num)\") like '%sony%' "
            "  and lower(\"item name(with num)\") like '%a7%' "
            "group by n, source "
            "order by c desc "
            "limit 30",
            conn,
        )
        print(df.to_string(index=False))

        print("\nPotential same-model variants (a7 + 24-105):")
        df2 = pd.read_sql(
            "select \"item name(with num)\" as n, source, count(*) c, "
            "min(\"Start\") mn, max(\"Start\") mx "
            "from unified_records "
            "where lower(\"item name(with num)\") like '%a7%' "
            "  and (lower(\"item name(with num)\") like '%24-105%' or lower(\"item name(with num)\") like '%24105%') "
            "group by n, source "
            "order by c desc "
            "limit 30",
            conn,
        )
        print(df2.to_string(index=False))
    finally:
        conn.close()


if __name__ == "__main__":
    main()

