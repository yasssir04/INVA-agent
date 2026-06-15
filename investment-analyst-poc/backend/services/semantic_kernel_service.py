from __future__ import annotations
import asyncio
from typing import Dict, Any, List
from ..utils.logger import get_logger
from .sk_wrapper import SKWrapper
from .grounding_service import GroundingService

logger = get_logger(__name__)


ANALYSIS_SECTIONS: List[str] = [
    "company_overview",
    "traction_growth",
    "team_analysis",
    "financial_metrics",
    "value_creation",
    "red_flags",
    "uvp",
    "market_trends",
    "market_opportunities",
    "funding_details",
    "competitive_landscape",
    "emerging_tech",
    "regional_comparison",
]


class KernelService:
    """Orchestrates analysis using Semantic Kernel (Azure OpenAI) with retrieval and scoring."""

    def __init__(self) -> None:
        self._sk = SKWrapper()
        self.grounding = GroundingService()

    async def _chat(self, system: str, user: str) -> str:
        return await self._sk.chat(system, user)

    async def analyze_session(self, session_id: str) -> Dict[str, Any]:
        results: Dict[str, Any] = {
            "grounding": {
                "mode": self.grounding.mode,
                "session_id": session_id,
            }
        }

        async def analyze_section(section: str) -> None:
            evidence = await self.grounding.search_evidence(session_id, query=section.replace("_", " "))
            context_parts: List[str] = []
            citations: List[Dict[str, Any]] = []
            for idx, item in enumerate(evidence[:5], start=1):
                source_name = item.get("source_name") or item.get("doc_path") or f"Source {idx}"
                source_uri = item.get("source_uri") or item.get("doc_path", "")
                excerpt = item.get("text", "")
                context_parts.append(
                    f"[{idx}] Source: {source_name}\nURI: {source_uri}\nExcerpt:\n{excerpt}"
                )
                citations.append(
                    {
                        "citation_id": item.get("citation_id") or item.get("id") or f"{section}-{idx}",
                        "document_id": item.get("document_id", ""),
                        "source_name": source_name,
                        "source_uri": source_uri,
                        "excerpt": excerpt[:500],
                    }
                )
            context = "\n\n".join(context_parts)
            system = (
                "You are an AI investment analyst. Provide concise, factual analysis for professional investors. "
                "Respond in plain text only, with short headings and bullet points. Ground claims in the provided evidence when available. "
                "End with 'Score: X/10; Confidence: Y%'."
            )
            user = (
                f"Section: {section}\n\nGrounded context:\n{context}\n\n"
                "Write a crisp analysis in plain text. Do not return JSON. End with 'Score: X/10; Confidence: Y%'."
            )
            out = await self._chat(system, user)
            section_result = self._extract_text_and_score(out)
            if citations:
                section_result["citations"] = citations
            results[section] = section_result

        # Run sections in parallel
        await asyncio.gather(*[analyze_section(s) for s in ANALYSIS_SECTIONS])

        # Compute key metrics (0-100) and weighted final score with robust parsing
        weights = {
            "Innovation and Patent Ownership": 0.20,
            "Team Diversity and Complementarity": 0.20,
            "Financial Strength": 0.10,
            "Product Differentiation": 0.20,
            "Startup Visibility in online channels": 0.10,
            "Marketing Potential": 0.10,
            "Political and economics": 0.05,
            "Social Impact": 0.05,
        }
        metric_keys = list(weights.keys())
        context_all = "\n".join([results.get(s, {}).get("text", "") for s in ANALYSIS_SECTIONS])
        base_prompt = (
            "Given the document context, return STRICT JSON with no prose: "
            "{\n  'scores': {\n    'Innovation and Patent Ownership': 0-100,\n    'Team Diversity and Complementarity': 0-100,\n    'Financial Strength': 0-100,\n    'Product Differentiation': 0-100,\n    'Startup Visibility in online channels': 0-100,\n    'Marketing Potential': 0-100,\n    'Political and economics': 0-100,\n    'Social Impact': 0-100\n  },\n  'confidence': 0-1,\n  'opinion': 'Good'|'Bad',\n  'justification': 'short text'\n}. "
            "Use only the exact keys shown above. Use your best estimate if information is partial."
        )
        raw = await self._chat("Only output valid JSON matching the schema.", f"Context:\n{context_all}\n{base_prompt}")
        parsed = self._safe_json(raw)
        scores = parsed.get("scores", {}) or {}
        # Retry once if missing keys or zeros everywhere
        def _all_zero(d: Dict[str, Any]) -> bool:
            try:
                return all(float(d.get(k, 0) or 0) == 0 for k in metric_keys)
            except Exception:
                return True
        if set(scores.keys()) != set(metric_keys) or _all_zero(scores):
            raw2 = await self._chat(
                "Return ONLY valid JSON with the exact keys. No commentary.",
                f"Context:\n{context_all}\n{base_prompt}"
            )
            parsed2 = self._safe_json(raw2)
            if isinstance(parsed2.get("scores"), dict):
                scores = parsed2.get("scores")
        # Coerce and clamp
        clean_scores: Dict[str, float] = {}
        for k in metric_keys:
            try:
                clean_scores[k] = max(0.0, min(100.0, float(scores.get(k, 0) or 0)))
            except Exception:
                clean_scores[k] = 0.0
        confidence = float(parsed.get("confidence", 0.6))
        opinion = parsed.get("opinion", "Unknown")
        justification = parsed.get("justification", "")

        final_score = 0.0
        for k, w in weights.items():
            final_score += clean_scores.get(k, 0.0) * w
        results["key_metrics"] = {
            "scores": clean_scores,
            "final_score": round(final_score, 1),
            "confidence": round(confidence, 2),
            "opinion": opinion,
            "justification": justification,
        }

        # Extract company name for display/exports
        name_raw = await self._chat(
            "Extract the primary company/startup name from context. Respond with name only.",
            f"Context:\n{context_all}"
        )
        results["company_name"] = (name_raw or "Company").strip().splitlines()[0][:80]

        # Generate memo
        memo_prompt = (
            "Create a professional investment memo including executive summary, key metrics, "
            "market outlook, risks, and recommendation. Use the prior sections as context."
        )
        memo_ctx = "\n".join([results.get(s, {}).get("text", "") for s in ANALYSIS_SECTIONS])
        memo = await self._chat(
            "You write crisp investment memos with headings and bullet points. Respond in plain text only.",
            f"Context:\n{memo_ctx}\n{memo_prompt}"
        )
        results["investment_memo"] = {"text": memo}
        return results

    def _safe_json(self, s: str) -> Dict[str, Any]:
        import json
        try:
            return json.loads(s)
        except Exception:
            return {"text": s}

    def _extract_text_and_score(self, s: str) -> Dict[str, Any]:
        import re
        m = re.search(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", s, re.IGNORECASE)
        c = re.search(r"Confidence:\s*(\d+(?:\.\d+)?)%", s, re.IGNORECASE)
        score = 0.0
        conf = None
        if m:
            try:
                score = float(m.group(1))
            except Exception:
                score = 0.0
        if c:
            try:
                conf = float(c.group(1)) / 100.0
            except Exception:
                conf = None
        out: Dict[str, Any] = {"text": s, "score": max(0.0, min(score, 10.0))}
        if conf is not None:
            out["confidence"] = max(0.0, min(conf, 1.0))
        return out
