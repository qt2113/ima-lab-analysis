import streamlit as st
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_TURNS = 20
SUMMARIZE_THRESHOLD = 20  # 累计 20 条用户消息后自动触发摘要


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
        st.session_state.chat_last_summarized_at = 0  # 上次摘要时的 history_count


def add_message(role: str, content: str):
    """添加消息，附带时间戳"""
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
    """构建发送给 AI 的消息列表，包含系统提示 + 摘要 + 最近对话"""
    # 复制系统消息，注入摘要
    system_msg = dict(st.session_state.chat_messages[0])
    summary = st.session_state.get("chat_summary", "")
    if summary:
        system_msg["content"] = (
            system_msg["content"]
            + f"\n\n## 对话历史摘要（之前的对话关键信息）\n{summary}"
        )

    user_assistant = [
        m for m in st.session_state.chat_messages[1:]
        if m["role"] in ("user", "assistant")
    ]
    # 只取最近 N 轮
    recent = user_assistant[-max_turns * 2:]

    # 清理 role/content 之外的时间戳字段（AI API 不需要）
    clean = []
    for m in [system_msg] + recent:
        clean.append({"role": m["role"], "content": m["content"]})

    return clean


def maybe_summarize():
    """
    当用户消息数超过阈值且距上次摘要已有新对话时，
    自动调用 AI 生成早期对话摘要，注入到 chat_summary。
    失败时静默跳过，不影响主流程。
    """
    count = st.session_state.chat_history_count
    last = st.session_state.get("chat_last_summarized_at", 0)

    if count < SUMMARIZE_THRESHOLD:
        return
    if count - last < 10:  # 每新增 10 条用户消息才重新摘要
        return

    all_msgs = [
        m for m in st.session_state.chat_messages[1:]
        if m["role"] in ("user", "assistant")
    ]
    if len(all_msgs) < 8:
        return

    # 取前 60% 的消息进行摘要
    split = max(4, int(len(all_msgs) * 0.6))
    old_msgs = all_msgs[:split]

    try:
        from ai.client import get_ai_client
        from config.settings import CLOUDFLARE_MODEL_CHAT

        client = get_ai_client()
        # 截断每条消息内容以节省 token
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
            # 累加到已有摘要
            prev = st.session_state.get("chat_summary", "")
            if prev:
                st.session_state.chat_summary = prev + "\n" + summary.strip()
            else:
                st.session_state.chat_summary = summary.strip()
            st.session_state.chat_last_summarized_at = count
            logger.info(f"Chat summarized at {count} messages, summary length: {len(st.session_state.chat_summary)}")
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
    """Inject current data context into the system prompt for better answers."""
    full_prompt = SYSTEM_PROMPT
    if data_context:
        full_prompt += f"\n\n## 当前数据库概况\n{data_context}"
    st.session_state.chat_messages[0] = {"role": "system", "content": full_prompt}
