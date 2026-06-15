from __future__ import annotations
from typing import List
from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class SKWrapper:
    """Semantic Kernel wrapper for chat and embeddings with Azure OpenAI fallback."""

    def __init__(self) -> None:
        self._mode = "sk"
        try:
            import semantic_kernel as sk
            from semantic_kernel.connectors.ai.open_ai import (
                AzureChatCompletion,
                AzureTextEmbedding,
            )
            self._sk = sk.Kernel()
            self._sk.add_service(
                AzureChatCompletion(
                    service_id="chat",
                    deployment_name=settings.azure_openai_deployment_gpt4o,
                    endpoint=settings.azure_openai_endpoint,
                    api_key=settings.azure_openai_api_key,
                    api_version=settings.azure_openai_api_version,
                )
            )
            self._sk.add_service(
                AzureTextEmbedding(
                    service_id="emb",
                    deployment_name=settings.azure_openai_deployment_embedding,
                    endpoint=settings.azure_openai_endpoint,
                    api_key=settings.azure_openai_api_key,
                    api_version=settings.azure_openai_api_version,
                )
            )
            self._sk_fn_cache = {}
        except Exception:
            self._mode = "aoai"
            from openai import AsyncAzureOpenAI
            self._client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
            )

    async def chat(self, system: str, user: str) -> str:
        if self._mode == "sk":
            # Use a dynamic semantic function for this chat turn
            prompt = f"""<message role=system>
{system}
</message>
<message role=user>
{user}
</message>"""
            try:
                # Create a temporary function and invoke
                if prompt not in getattr(self, "_sk_fn_cache", {}):
                    fn = self._sk.add_function(
                        plugin_name="chat_plugin",
                        function_name=f"chat_{len(self._sk_fn_cache)}",
                        prompt=prompt,
                        description="Generic chat function",
                        temperature=0.2,
                        top_p=1.0,
                        max_tokens=1200,
                        service_id="chat",
                    )
                    self._sk_fn_cache[prompt] = fn
                fn = self._sk_fn_cache[prompt]
                result = await self._sk.invoke(fn)
                return str(result)
            except Exception:
                logger.exception("SK chat failed, falling back to AOAI")
                self._mode = "aoai"
        # Fallback to Azure OpenAI
        resp = await self._client.chat.completions.create(
            model=settings.azure_openai_deployment_gpt4o,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if self._mode == "sk":
            try:
                # SK embeddings via the service
                svc = self._sk.get_service("emb")
                res = await svc.embed_documents_async(texts)
                return res
            except Exception:
                logger.exception("SK embed failed, falling back to AOAI")
                self._mode = "aoai"
        # Fallback AOAI
        res = await self._client.embeddings.create(
            model=settings.azure_openai_deployment_embedding,
            input=texts,
        )
        return [d.embedding for d in res.data]
