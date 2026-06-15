from __future__ import annotations
import asyncio
import time
from typing import List, Dict, Any, Tuple
from tavily import TavilyClient
from bs4 import BeautifulSoup
import requests
from ..config import settings
from ..utils.logger import get_logger
from ..utils.helpers import clamp
from .semantic_kernel_service import KernelService

logger = get_logger(__name__)

ALLOWED_URLS = [
    "https://qatar.websummit.com/startups/featured-startups/filters/eyJjb3VudHJ5IjoiUWF0YXIifQ==/",
    "https://qatar.websummit.com/startups/featured-startups/filters/eyJjb3VudHJ5IjoiUWF0YXIifQ==/page/2/",
    "https://qatar.websummit.com/startups/featured-startups/filters/eyJjb3VudHJ5IjoiUWF0YXIifQ==/page/3/",
]


class TavilyService:
    """Searches curated Qatar startup sources and ranks opportunities."""

    def __init__(self) -> None:
        self.client = TavilyClient(api_key=settings.tavily_api_key)
        self.kernel = KernelService()
        self._cache: Dict[Tuple[str], Tuple[float, List[Dict[str, Any]]]] = {}
        self._rate_lock = asyncio.Lock()
        self._last_call = 0.0

    async def search_qatar_opportunities(self, sector: str) -> List[Dict[str, Any]]:
        # Rate limit: ensure at least 0.5s between calls
        async with self._rate_lock:
            delta = time.time() - self._last_call
            if delta < 0.5:
                await asyncio.sleep(0.5 - delta)
            self._last_call = time.time()

        # Cache
        key = (sector.strip().lower(),)
        cached = self._cache.get(key)
        if cached and (time.time() - cached[0] < 300):
            return cached[1]

        # Strictly use allowed URLs for startup names
        pages = await asyncio.gather(*[self._fetch(url) for url in ALLOWED_URLS])
        items: List[Dict[str, Any]] = []
        for url, html in pages:
            if not html:
                continue
            items.extend(self._extract_candidates(url, html))

        # Analyze and rank with LLM for selected sector; return top 5 only
        ranked = await self._rank_with_ai(items, sector)
        self._cache[key] = (time.time(), ranked)
        return ranked

    async def _fetch(self, url: str) -> tuple[str, str | None]:
        def _sync() -> str | None:
            try:
                r = requests.get(url, timeout=30)
                if r.ok:
                    return r.text
                return None
            except Exception:
                return None
        html = await asyncio.to_thread(_sync)
        return url, html

    def _extract_candidates(self, url: str, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        items: List[Dict[str, Any]] = []
        # WebSummit Qatar listing: capture candidate names/links
        for a in soup.select("a[href]"):
            text = a.get_text(strip=True)
            href = a.get("href") or ""
            if not text:
                continue
            full = href if href.startswith("http") else (f"https://qatar.websummit.com{href}" if href.startswith("/") else url)
            items.append({"name": text, "url": full})
        # Deduplicate by name
        seen = set()
        uniq: List[Dict[str, Any]] = []
        for it in items:
            key = it["name"].lower()
            if key in seen:
                continue
            seen.add(key)
            uniq.append(it)
        return uniq

    async def _rank_with_ai(self, items: List[Dict[str, Any]], sector: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        async def web_context(name: str) -> str:
            # Use Tavily to gather compact web signals for the startup
            def _sync_search() -> str:
                try:
                    res = self.client.search(query=f"{name} Qatar startup", max_results=5, include_answer=True)
                    parts = []
                    if isinstance(res, dict):
                        if res.get("answer"):
                            parts.append(res["answer"])
                        for r in res.get("results", [])[:5]:
                            if r.get("content"):
                                parts.append(r["content"])
                    return "\n".join(parts)[:4000]
                except Exception:
                    return ""
            return await asyncio.to_thread(_sync_search)

        async def score_item(it: Dict[str, Any]) -> None:
            name = it.get("name", "")
            ctx = await web_context(name)
            prompt = (
                f"Sector: {sector}. You are ranking Qatar startups by sector-specific metrics.\n"
                "Return JSON: {\n  'scores': { 'TAM':0-100,'CAC_LTV':0-100,'MRR_Growth':0-100,'Burn_Runway':0-100,'Churn_Retention':0-100,\n              'Team_Execution':0-100,'Scalability_Tech':0-100,'Regulatory_Partnerships':0-100,'Impact_Value':0-100,'Early_Stage_Indicators':0-100 },\n  'final_score':0-100, 'explanation':'text', 'confidence':0-1\n}.\n"
                f"Startup: {name}\nURL: {it.get('url')}\nContext:\n{ctx}\n"
            )
            out = await self.kernel._chat(
                "Score startups by sector-specific metrics based on reliable web signals; be concise but informative.", prompt
            )
            parsed = self.kernel._safe_json(out)
            fs = clamp(float(parsed.get("final_score", 0)), 0, 100)
            results.append({
                "name": name,
                "url": it.get("url"),
                "scores": parsed.get("scores", {}),
                "final_score": fs,
                "explanation": parsed.get("explanation", ""),
                "confidence": parsed.get("confidence", 0.5),
            })

        await asyncio.gather(*[score_item(it) for it in items[:50]])
        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        return results[:5]
