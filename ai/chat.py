import streamlit as st
from typing import List, Dict, Optional
from .prompts import SYSTEM_PROMPT


def init_chat_state():
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    if "chat_history_count" not in st.session_state:
        st.session_state.chat_history_count = 0


def add_message(role: str, content: str):
    if role == "user":
        st.session_state.chat_messages.append({"role": "user", "content": content})
        st.session_state.chat_history_count += 1
    elif role == "assistant":
        st.session_state.chat_messages.append({"role": "assistant", "content": content})


def get_conversation_history(max_turns: int = 10) -> List[Dict[str, str]]:
    messages = [st.session_state.chat_messages[0]]
    user_assistant = [m for m in st.session_state.chat_messages[1:] 
                      if m["role"] in ("user", "assistant")]
    
    recent = user_assistant[-max_turns * 2:]
    messages.extend(recent)
    return messages


def clear_chat_history():
    st.session_state.chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    st.session_state.chat_history_count = 0


def get_history_count() -> int:
    return st.session_state.get("chat_history_count", 0)
