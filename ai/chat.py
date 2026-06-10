import streamlit as st
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_TURNS = 20
SUMMARIZE_THRESHOLD = 20

# ── Intent → data queries ────────────────────────────────
# 根据用户问题的关键词匹配，决定查询哪些数据模块
INTENT_RULES = [
    # (关键词列表, 要查询的数据模块)
    (["无人使用", "闲置", "不用", "idle", "没借", "没被借", "长期不用",
      "很少用", "几乎不用", "未被借用", "长时间未用", "从未使用",
      "用的人少", "不常用", "冷门"], ["idle_items", "overview"]),
    (["采购", "购买", "买", "添置", "procurement", "建议买", "推荐买",
      "需要补充", "库存不足", "短缺"], ["procurement_advice", "top_items", "overview"]),
    (["最受欢迎", "热门", "最多", "popular", "高频", "经常借",
      "top", "排行", "排名", "借的最多", "最常"], ["top_items", "overview"]),
    (["异常", "长时", "超时", "没还", "anomaly", "超长",
      "不还", "逾期", "不正常", "可疑"], ["anomalies", "active_items"]),
    (["规律", "模式", "时间", "高峰", "pattern", "什么时候",
      "几点", "星期", "月份", "高峰月", "高峰时段"], ["temporal"]),
    (["类别", "分类", "category", "哪个类别", "哪种",
      "cable", "camera", "sensor", "battery"], ["overview"]),  # 类别问题先看 overview，AI 可根据热门类别回答
    (["在借", "当前借出", "正在借", "没还", "active",
      "借出去了", "谁借"], ["active_items"]),
    (["历史", "时间线", "timeline", "记录"], ["overview"]),
]


def _classify_intent(user_message: str) -> List[str]:
    """根据用户问题，返回需要查询的数据模块列表。"""
    msg_lower = user_message.lower()
    modules = set()

    for keywords, mods in INTENT_RULES:
        if any(kw in msg_lower for kw in keywords):
            modules.update(mods)

    # 始终包含 overview 作为基础上下文
    modules.add("overview")
    return list(modules)


def _query_module(module: str, user_message: str = "") -> dict:
    """查询单个数据模块，返回 {label: str, data: any} 格式。"""
    try:
        from analyzer import (
            overview, fleet_health, category_analysis, item_detail,
            temporal_patterns, get_categories, get_items,
        )
        import sqlite3
        import pandas as pd
        from config.settings import DATABASE_PATH

        if module == "overview":
            ov = json.loads(overview())
            kpi = ov.get("kpi", {})
            cats = ov.get("categories", [])
            monthly = ov.get("monthly", [])
            top_cats = sorted(cats, key=lambda c: c.get("count", 0), reverse=True)[:8]
            recent_m = monthly[-6:] if monthly else []
            return {
                "label": "总览",
                "data": {
                    "总记录": kpi.get("total", 0),
                    "当前在借": kpi.get("active_now", 0),
                    "平均持有时长_h": round(kpi.get("avg_hours", 0), 1),
                    "物品种类数": kpi.get("unique_items", 0),
                    "热门类别": [f"{c['Category']}({c['count']}次,中位{c['med_h']}h)" for c in top_cats],
                    "近6月趋势": [f"{m['month']}:{m['count']}" for m in recent_m],
                },
            }

        elif module == "top_items":
            fh = json.loads(fleet_health(top_n=25))
            bars = sorted(fh.get("bars", []), key=lambda b: -b.get("score", 0))
            items = []
            for i, b in enumerate(bars[:15]):
                items.append(f"{i+1}. {b['item']}（{b.get('category','?')}，借{b['count']}次，利用率{b['util']:.2f}，均时{b['avg_h']:.0f}h）")
            return {"label": "高需求设备 Top15", "data": {"items": items}}

        elif module == "idle_items":
            fh = json.loads(fleet_health())
            quad = fh.get("quadrant", [])
            # 低频低利用率
            low_use = sorted(
                [q for q in quad
                 if not q.get("active") and q.get("count", 0) <= 2 and q.get("util", 0) < 0.05],
                key=lambda q: (q.get("count", 0), q.get("util", 0))
            )[:20]
            # 中等频次但利用率极低（很久以前用过）
            stale = sorted(
                [q for q in quad
                 if not q.get("active") and 3 <= q.get("count", 0) <= 5 and q.get("util", 0) < 0.02],
                key=lambda q: q.get("util", 0)
            )[:10]
            # 仅借用 1 次
            single_use = []
            try:
                conn = sqlite3.connect(str(DATABASE_PATH))
                df1 = pd.read_sql(
                    "SELECT \"item name(with num)\" n, COUNT(*) c, MAX(\"Start\") last_dt "
                    "FROM unified_records WHERE n NOT LIKE '0 %' "
                    "GROUP BY n HAVING c = 1 ORDER BY last_dt ASC LIMIT 20",
                    conn
                )
                conn.close()
                single_use = [f"{r['n']}（仅1次，{r['last_dt'][:10]}）" for _, r in df1.iterrows()]
            except Exception:
                pass
            return {
                "label": "闲置/低使用率设备",
                "data": {
                    "低频低利用率(≤2次,利用率<5%)": [f"{q['item']}（{q.get('category','?')}，{q['count']}次，利用率{q['util']:.3f}）" for q in low_use],
                    "陈旧设备(3-5次,利用率<2%)": [f"{q['item']}（{q.get('category','?')}，{q['count']}次）" for q in stale],
                    "仅借用1次": single_use,
                },
            }

        elif module == "active_items":
            fh = json.loads(fleet_health())
            quad = fh.get("quadrant", [])
            active = sorted(
                [q for q in quad if q.get("active")],
                key=lambda q: -q.get("avg_h", 0)
            )
            items = [f"{a['item']}（{a.get('category','?')}，历史借{a['count']}次，均时{a['avg_h']:.0f}h）" for a in active[:25]]
            return {"label": f"当前在借（共{len(active)}件）", "data": {"items": items}}

        elif module == "anomalies":
            fh = json.loads(fleet_health())
            quad = fh.get("quadrant", [])
            ultra_long = sorted(
                [q for q in quad if q.get("active") and q.get("avg_h", 0) > 300],
                key=lambda q: -q.get("avg_h", 0)
            )[:10]
            high_freq_short = sorted(
                [q for q in quad if q.get("count", 0) > 20 and q.get("avg_h", 0) < 24],
                key=lambda q: -q.get("count", 0)
            )[:10]
            return {
                "label": "异常借用检测",
                "data": {
                    "超长借用(>300h,当前在借)": [f"{a['item']}（{a.get('category','?')}，{a['count']}次，均时{a['avg_h']:.0f}h）" for a in ultra_long],
                    "高频短时(>20次,<24h)": [f"{a['item']}（{a.get('category','?')}，{a['count']}次，均时{a['avg_h']:.0f}h）" for a in high_freq_short],
                },
            }

        elif module == "temporal":
            tp = json.loads(temporal_patterns())
            by_month = tp.get("by_month", [])
            by_weekday = tp.get("by_weekday", [])
            return {
                "label": "借用时间模式",
                "data": {
                    "月度分布": [f"{m['label']}:{m['count']}" for m in sorted(by_month, key=lambda x: -x["count"])],
                    "星期分布": [f"{w['label']}:{w['count']}" for w in sorted(by_weekday, key=lambda x: -x["count"])],
                },
            }

        elif module == "procurement_advice":
            fh = json.loads(fleet_health(top_n=30))
            ov = json.loads(overview())
            bars = sorted(fh.get("bars", []), key=lambda b: -b.get("score", 0))
            cats = ov.get("categories", [])
            top_cats = sorted(cats, key=lambda c: c.get("count", 0), reverse=True)[:8]
            return {
                "label": "采购建议数据",
                "data": {
                    "最高需求设备": [f"{b['item']}（{b.get('category','?')}，借{b['count']}次，利用率{b['util']:.2f}）" for b in bars[:12]],
                    "最热门类别": [f"{c['Category']}: {c['count']}次, 中位{c['med_h']}h" for c in top_cats],
                    "总记录数": ov.get("kpi", {}).get("total", 0),
                    "在借数": ov.get("kpi", {}).get("active_now", 0),
                },
            }

        elif module == "search_items":
            query = user_message
            # 尝试从用户消息中提取可能的关键词
            all_items = get_items()
            matches = [it for it in all_items if query.lower() in it.lower()]
            return {
                "label": f"搜索: {query[:30]}",
                "data": {"匹配数": len(matches), "结果": matches[:20]},
            }

        return {"label": module, "data": {}}

    except Exception as e:
        logger.error(f"Query module {module} failed: {e}")
        return {"label": module, "data": {"error": str(e)}}


def build_data_context(user_message: str) -> str:
    """根据用户问题，定向查询相关数据，拼接为 AI 可读的上下文。

    这是核心——意图分类 + 定向查询，只给 AI 它需要的数据。
    """
    modules = _classify_intent(user_message)
    logger.info(f"Intent → modules: {modules}")

    parts = []
    for mod in modules:
        result = _query_module(mod, user_message)
        label = result.get("label", mod)
        data = result.get("data", {})
        if data:
            parts.append(f"【{label}】{json.dumps(data, ensure_ascii=False, indent=2)}")

    # 如果没匹配到特殊模块，默认给 overview + top_items
    if len(modules) <= 1:  # only overview
        for mod in ["top_items", "idle_items"]:
            result = _query_module(mod, user_message)
            data = result.get("data", {})
            if data:
                parts.append(f"【{result['label']}】{json.dumps(data, ensure_ascii=False, indent=2)}")

    context = "\n\n".join(parts)
    return context


# ══════════════════════════════════════════════════════════
# Chat state management
# ══════════════════════════════════════════════════════════

def init_chat_state():
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    if "chat_history_count" not in st.session_state:
        st.session_state.chat_history_count = 0
    if "chat_summary" not in st.session_state:
        st.session_state.chat_summary = ""
    if "chat_last_summarized_at" not in st.session_state:
        st.session_state.chat_last_summarized_at = 0


def add_message(role: str, content: str):
    msg = {
        "role": role,
        "content": content,
        "time": datetime.now().strftime("%H:%M"),
    }
    if role == "user":
        st.session_state.chat_messages.append(msg)
        st.session_state.chat_history_count += 1
    elif role == "assistant":
        st.session_state.chat_messages.append(msg)


def get_conversation_history(max_turns: int = MAX_TURNS) -> List[Dict[str, str]]:
    summary = st.session_state.get("chat_summary", "")
    user_assistant = [
        m for m in st.session_state.chat_messages[1:]
        if m["role"] in ("user", "assistant")
    ]
    recent = user_assistant[-max_turns * 2:]

    clean = []
    for m in recent:
        clean.append({"role": m["role"], "content": m["content"]})

    if summary:
        clean.insert(0, {
            "role": "system",
            "content": f"## 对话历史摘要\n{summary}",
        })

    return clean


def maybe_summarize():
    count = st.session_state.chat_history_count
    last = st.session_state.get("chat_last_summarized_at", 0)

    if count < SUMMARIZE_THRESHOLD:
        return
    if count - last < 10:
        return

    all_msgs = [
        m for m in st.session_state.chat_messages[1:]
        if m["role"] in ("user", "assistant")
    ]
    if len(all_msgs) < 8:
        return

    split = max(4, int(len(all_msgs) * 0.6))
    old_msgs = all_msgs[:split]

    try:
        from ai.client import get_ai_client
        from config.settings import CLOUDFLARE_MODEL_CHAT

        client = get_ai_client()
        compact = [
            {"role": m["role"], "content": m["content"][:300]}
            for m in old_msgs
        ]
        summary_prompt = [
            {
                "role": "system",
                "content": (
                    "用简短中文总结以下对话的关键信息和结论（150字以内），"
                    "只输出摘要本身，不要前缀或解释。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(compact, ensure_ascii=False),
            },
        ]
        summary = client.chat(
            messages=summary_prompt,
            model=CLOUDFLARE_MODEL_CHAT,
            max_tokens=250,
        )
        if summary and len(summary.strip()) > 5:
            prev = st.session_state.get("chat_summary", "")
            if prev:
                st.session_state.chat_summary = prev + "\n" + summary.strip()
            else:
                st.session_state.chat_summary = summary.strip()
            st.session_state.chat_last_summarized_at = count
            logger.info(f"Chat summarized at {count} messages")
    except Exception as e:
        logger.warning(f"Chat summarization failed (non-fatal): {e}")


def update_chat_summary(summary: str):
    st.session_state.chat_summary = summary


def clear_chat_history():
    st.session_state.chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    st.session_state.chat_history_count = 0
    st.session_state.chat_summary = ""
    st.session_state.chat_last_summarized_at = 0


def get_history_count() -> int:
    return st.session_state.get("chat_history_count", 0)


def set_system_context(data_context: str):
    full_prompt = SYSTEM_PROMPT
    if data_context:
        full_prompt += f"\n\n## 当前数据库概况\n{data_context}"
    st.session_state.chat_messages[0] = {"role": "system", "content": full_prompt}
