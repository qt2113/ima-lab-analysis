import sqlite3
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def main() -> None:
    item = "Sony A7 III With EF 24-105 017"
    conn = sqlite3.connect("item_analysis.db")
    try:
        logger.info("exact counts:")
        for src in ["historical", "realtime"]:
            c = conn.execute(
                'select count(*) from unified_records where source=? and "item name(with num)"=?',
                (src, item),
            ).fetchone()[0]
            logger.info(f"  {src}: {c}")

        logger.info("example rows (any source):")
        rows = conn.execute(
            'select "Start", "finished", source, "item name(with num)" '
            'from unified_records where "item name(with num)"=? order by "Start" limit 8',
            (item,),
        ).fetchall()
        for r in rows:
            logger.info(str(r))

        logger.info("LIKE candidates (sony a7):")
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
        logger.info(df.to_string(index=False))

        logger.info("Potential same-model variants (a7 + 24-105):")
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
        logger.info(df2.to_string(index=False))
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    main()
