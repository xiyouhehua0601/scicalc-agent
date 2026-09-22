"""LLM 客户端：一个最薄的 OpenAI 兼容接口封装。

默认走 DeepSeek，也可以换 Qwen / Kimi / OpenAI，只要改环境变量就行。
"""
import os

import requests


class LLMClient:
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = (
            base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
        ).rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "deepseek-chat")

    def chat(self, messages, temperature=0.0, max_tokens=2048):
        """返回 (文本, usage)。usage 是 dict 或 None，用来统计 token。"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        r = requests.post(url, headers=headers, json=body, timeout=120)
        r.raise_for_status()
        d = r.json()
        text = d["choices"][0]["message"]["content"]
        usage = d.get("usage")
        return text, usage
