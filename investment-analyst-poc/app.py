import os
import streamlit as st
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")

st.set_page_config(page_title="AI Investment Analyst", layout="wide")


def _request_json(method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        resp = requests.request(method, f"{API_BASE}{path}", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except Exception as e:
        st.error(f"Request failed: {e}")
        return {"error": str(e)}


def _post_json(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _request_json("POST", path, payload)


def _delete_json(path: str) -> Dict[str, Any]:
    return _request_json("DELETE", path)


def _upload_files(files: List[Any], replace_session_id: Optional[str] = None) -> Dict[str, Any]:
    url = f"{API_BASE}/documents/upload"
    files_payload = [("files", (f.name, f.getvalue(), f.type)) for f in files]
    data: Dict[str, str] = {}
    if replace_session_id:
        data["replace_session_id"] = replace_session_id
    try:
        resp = requests.post(url, files=files_payload, data=data, timeout=180)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return {"error": str(e)}


def _clear_document_state() -> None:
    st.session_state.session_id = None
    st.session_state.analysis_results = None
    st.session_state.pdf_bytes = None
    st.session_state.docx_bytes = None


def _score_badge(val: float) -> str:
    color = "#2ecc71" if val >= 7 else ("#f1c40f" if val >= 4 else "#e74c3c")
    return f"<span style='background:{color};color:white;padding:4px 8px;border-radius:6px;'>Score: {val:.1f}/10</span>"


def _render_citations(item: Dict[str, Any]) -> None:
    citations = item.get("citations") or []
    if not citations:
        return
    with st.expander("Sources", expanded=False):
        for citation in citations:
            st.markdown(f"**{citation.get('source_name', 'Source')}**")
            if citation.get("source_uri"):
                st.caption(citation["source_uri"])
            if citation.get("excerpt"):
                st.write(citation["excerpt"])


def _render_analysis_results(analysis_res: Dict[str, Any]) -> None:
    tab_labels = [
        "Dashboard",
        "Overview", "Traction & Growth", "Team", "Financials", "Value Creation",
        "Red Flags", "UVP", "Market", "Opportunities", "Funding & Cap Table",
        "Competition", "Tech", "Regional", "Memo"
    ]
    section_keys = [
        "company_overview", "traction_growth", "team_analysis", "financial_metrics",
        "value_creation", "red_flags", "uvp", "market_trends", "market_opportunities",
        "funding_details", "competitive_landscape", "emerging_tech", "regional_comparison"
    ]
    weights = {
        "Innovation and Patent Ownership": 20,
        "Team Diversity and Complementarity": 20,
        "Financial Strength": 10,
        "Product Differentiation": 20,
        "Startup Visibility in online channels": 10,
        "Marketing Potential": 10,
        "Political and economics": 5,
        "Social Impact": 5,
    }
    tabs = st.tabs(tab_labels)
    results = analysis_res.get("results", {})
    grounding = results.get("grounding", {})

    with tabs[0]:
        km = results.get("key_metrics", {})
        scores = km.get("scores", {}) or {}
        final_score = float(km.get("final_score", 0))
        conf_overall = float(km.get("confidence", 0))
        colA, colB = st.columns([1, 2])
        with colA:
            badge_color = "#2ecc71" if final_score >= 70 else ("#f1c40f" if final_score >= 40 else "#e74c3c")
            st.markdown(
                f"<div style='font-size:22px;margin-bottom:8px;'>Weighted Final Score</div>"
                f"<div style='background:{badge_color};color:white;padding:10px 12px;border-radius:8px;display:inline-block;'>{final_score:.1f} / 100</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='margin-top:6px;'><span style='background:#34495e;color:white;padding:2px 6px;border-radius:6px;'>Confidence: {conf_overall*100:.0f}%</span></div>",
                unsafe_allow_html=True,
            )
            if grounding.get("mode"):
                st.caption(f"Grounding mode: {grounding.get('mode')}")
            with st.expander("Scoring weights", expanded=True):
                for k, w in weights.items():
                    st.write(f"- {k}: {w}%")
        with colB:
            st.subheader("Key Metrics (0-100)")
            if scores:
                for name, weight in weights.items():
                    vv = float(scores.get(name, 0) or 0)
                    row = st.columns([1.5, 6, 1.2])
                    with row[0]:
                        st.caption(name)
                    with row[1]:
                        st.progress(int(max(0, min(100, vv))))
                    with row[2]:
                        st.caption(f"{vv:.0f}/100 | {int(weight)}%")
            else:
                st.info("No metrics returned.")

        dl1, dl2 = st.columns(2)
        with dl1:
            if st.button("Generate PDF Report"):
                r = requests.get(
                    f"{API_BASE}/reports/export/pdf",
                    params={"session_id": st.session_state.session_id},
                    timeout=180,
                )
                if r.ok:
                    st.session_state.pdf_bytes = r.content
            if st.session_state.pdf_bytes:
                st.download_button(
                    "Download PDF",
                    data=st.session_state.pdf_bytes,
                    file_name="analysis_report.pdf",
                    mime="application/pdf",
                )
        with dl2:
            if st.button("Generate Word Report (.docx)"):
                r = requests.get(
                    f"{API_BASE}/reports/export/docx",
                    params={"session_id": st.session_state.session_id},
                    timeout=180,
                )
                if r.ok:
                    st.session_state.docx_bytes = r.content
            if st.session_state.docx_bytes:
                st.download_button(
                    "Download DOCX",
                    data=st.session_state.docx_bytes,
                    file_name="analysis_report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )

    for i, tab in enumerate(tabs[1:-1]):
        key = section_keys[i]
        with tab:
            item = results.get(key, {})
            st.write(item.get("text", ""))
            if isinstance(item.get("score"), (int, float)):
                st.markdown(_score_badge(float(item["score"])), unsafe_allow_html=True)
            if isinstance(item.get("confidence"), (int, float)):
                conf_pct = float(item["confidence"]) * 100
                st.markdown(
                    f"<span style='background:#34495e;color:white;padding:2px 6px;border-radius:6px;'>Confidence: {conf_pct:.0f}%</span>",
                    unsafe_allow_html=True,
                )
            _render_citations(item)

    with tabs[-1]:
        memo = results.get("investment_memo", {}).get("text", "")
        st.write(memo)
st.title("AI Investment Analyst POC")
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
if "docx_bytes" not in st.session_state:
    st.session_state.docx_bytes = None

section = st.sidebar.radio("Sections", ["Document Analysis", "Investment Opportunities"]) 

if section == "Document Analysis":
    st.header("Document Analysis")
    if st.session_state.session_id:
        st.caption(f"Active session: {st.session_state.session_id}")
        action_cols = st.columns(2)
        with action_cols[0]:
            if st.button("Reset Session"):
                res = _post_json("/sessions/reset", {"session_id": st.session_state.session_id})
                if res and not res.get("error"):
                    _clear_document_state()
                    st.success("Session reset. Upload new documents to start fresh.")
        with action_cols[1]:
            if st.button("Delete Session"):
                res = _delete_json(f"/sessions/{st.session_state.session_id}")
                if res and not res.get("error"):
                    _clear_document_state()
                    st.success("Session deleted.")
        st.caption("Uploading a new batch will delete the current session data and create a fresh session.")
    uploaded = st.file_uploader("Upload up to 4 PDF/DOCX files", type=["pdf", "docx"], accept_multiple_files=True)
    if uploaded:
        if len(uploaded) > 4:
            st.warning("Max 4 files per session.")
        else:
            if st.button("Process Documents"):
                with st.spinner("Uploading and analyzing..."):
                    up_res = _upload_files(uploaded, replace_session_id=st.session_state.session_id)
                    if up_res and not up_res.get("error"):
                        # Run analysis and store results
                        analysis_res = _post_json("/documents/analyze", {"session_id": up_res.get("session_id")})
                        if analysis_res and not analysis_res.get("error"):
                            st.session_state.session_id = up_res.get("session_id")
                            st.session_state.analysis_results = analysis_res
                            st.session_state.pdf_bytes = None
                            st.session_state.docx_bytes = None
                            st.success("Analysis complete")
                    # End analysis flow

    if st.session_state.analysis_results:
        _render_analysis_results(st.session_state.analysis_results)

    # Show downloads for last run (if any)
    if st.session_state.analysis_results and st.session_state.session_id:
        st.divider()
        st.subheader("Download last analysis")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Generate PDF Report (last)"):
                resp = requests.get(
                    f"{API_BASE}/reports/export/pdf",
                    params={"session_id": st.session_state.session_id},
                    timeout=180,
                )
                if resp.ok:
                    st.session_state.pdf_bytes = resp.content
            if st.session_state.pdf_bytes:
                st.download_button(
                    "Download PDF",
                    data=st.session_state.pdf_bytes,
                    file_name="analysis_report.pdf",
                    mime="application/pdf",
                )
        with col2:
            if st.button("Generate Word Report (.docx) (last)"):
                resp = requests.get(
                    f"{API_BASE}/reports/export/docx",
                    params={"session_id": st.session_state.session_id},
                    timeout=180,
                )
                if resp.ok:
                    st.session_state.docx_bytes = resp.content
            if st.session_state.docx_bytes:
                st.download_button(
                    "Download DOCX",
                    data=st.session_state.docx_bytes,
                    file_name="analysis_report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )

elif section == "Investment Opportunities":
    st.header("Investment Opportunities in Qatar")
    sector = st.selectbox(
        "Select sector",
        ["FinTech", "EduTech", "HealthTech", "E-Commerce", "AI", "Climate/Greentech"],
    )
    if st.button("Search Opportunities"):
        with st.spinner("Searching and analyzing opportunities..."):
            res = _post_json("/opportunities/search", {"sector": sector})
            if res and not res.get("error"):
                items = res.get("opportunities", [])
                for i, item in enumerate(items, start=1):
                    st.subheader(f"{i}. {item.get('name','Unknown')}")
                    if item.get("explanation"):
                        st.write(item.get("explanation"))
                    fs = float(item.get("final_score", 0))
                    color = "#2ecc71" if fs >= 70 else ("#f1c40f" if fs >= 40 else "#e74c3c")
                    st.markdown(
                        f"<span style='background:{color};color:white;padding:4px 8px;border-radius:6px;'>Final Score: {fs:.0f}</span>",
                        unsafe_allow_html=True,
                    )
                    subs = item.get("scores") or {}
                    if isinstance(subs, dict) and subs:
                        with st.expander("Show metric breakdown"):
                            for k, v in list(subs.items())[:8]:
                                row = st.columns([2, 6, 1])
                                with row[0]:
                                    st.caption(k)
                                with row[1]:
                                    try:
                                        vv = float(v)
                                    except Exception:
                                        vv = 0.0
                                    st.progress(int(max(0, min(100, vv))))
                                with row[2]:
                                    st.caption(f"{vv:.0f}/100")
                    if isinstance(item.get("confidence"), (int, float)):
                        st.markdown(
                            f"<span style='background:#34495e;color:white;padding:2px 6px;border-radius:6px;'>Confidence: {float(item['confidence'])*100:.0f}%</span>",
                            unsafe_allow_html=True,
                        )
                    if item.get("url"):
                        st.write(item["url"]) 
            else:
                st.error("Opportunity search failed. Ensure sector is provided and try again.")
