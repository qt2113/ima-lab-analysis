import os
import json
from typing import Optional, List, Dict, Any

try:
    import groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


def _get_secret(key: str, default: str = "") -> str:
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
        if "custom_sheet" in st.secrets and key in st.secrets["custom_sheet"]:
            return st.secrets["custom_sheet"][key]
    except Exception:
        pass
    return default


class CloudflareClient:
    def __init__(
        self,
        account_id: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.account_id = account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        self.api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN", "")
        
        if not self.account_id:
            self.account_id = _get_secret("cloudflare_account_id")
        
        if not self.api_token:
            self.api_token = _get_secret("cloudflare_api_token")
        
        if not self.account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID not found. Set it in Streamlit secrets or environment.")
        if not self.api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN not found. Set it in Streamlit secrets or environment.")
        
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai"
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "@cf/meta/llama-3.2-1b-instruct",
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        import requests
        
        url = f"{self.base_url}/run/{model}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        
        data = response.json()
        if "result" in data and "response" in data["result"]:
            return data["result"]["response"]
        elif "result" in data and isinstance(data["result"], dict):
            return data["result"].get("response", str(data["result"]))
        else:
            return str(data)


class GroqClient:
    def __init__(self, api_key: Optional[str] = None):
        if not GROQ_AVAILABLE:
            raise ImportError("groq package not installed. Run: pip install groq")
        
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        if not self.api_key:
            self.api_key = _get_secret("groq_api_key")
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found. Set it in environment or Streamlit secrets.")
        
        self.client = groq.Groq(api_key=self.api_key)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content


_ai_client: Optional[Any] = None
_provider: str = "cloudflare"


def init_ai_client(provider: str = "cloudflare"):
    global _ai_client, _provider
    _provider = provider
    
    if provider == "cloudflare":
        _ai_client = CloudflareClient()
    elif provider == "groq":
        _ai_client = GroqClient()
    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_ai_client() -> Any:
    global _ai_client, _provider
    
    if _ai_client is None:
        provider = os.environ.get("AI_PROVIDER", _get_secret("ai_provider", "cloudflare"))
        init_ai_client(provider)
    
    return _ai_client


def reset_ai_client():
    global _ai_client
    _ai_client = None


def get_groq_client() -> GroqClient:
    return get_ai_client()


def get_cloudflare_client() -> CloudflareClient:
    return get_ai_client()
