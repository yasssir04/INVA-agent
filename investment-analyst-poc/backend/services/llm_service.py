from __future__ import annotations
from typing import Dict, Any
from openai import AsyncAzureOpenAI
from ..config import settings


class LLMService:
    """Lightweight LLM wrapper for Azure OpenAI chat and JSON safety."""

    def __init__(self) -> None:
        self._client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )

    async def chat(self, system: str, user: str, temperature: float = 0.2) -> str:
        resp = await self._client.chat.completions.create(
            model=settings.azure_openai_deployment_gpt4o,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""

    def safe_json(self, s: str) -> Dict[str, Any]:
        import json
        try:
            return json.loads(s)
        except Exception:
            return {"text": s}
