import re
import textwrap

import streamlit as st
from pipeline import (
    extract_contractor_fields,
    score_contractor,
    generate_explanation,
    generate_scorecard_pdf
)


def _clean_html(s: str) -> str:
    """Strip leading indentation so Streamlit's markdown parser does not
    treat indented HTML as a code block (which would escape the tags)."""
    s = textwrap.dedent(s)
    return re.sub(r"\n\s+", "\n", s).strip()

# ── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title="CanQualify Intelligence Platform",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════
#  CanQualify design system  (CSS)
# ══════════════════════════════════════════════════════════
CQ_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root{
  --cq-green:#2E9E5B;  --cq-green-dk:#1E7A43;  --cq-green-bg:#E7F5EC;
  --cq-blue:#2563EB;   --cq-blue-dk:#1D4FD7;
  --cq-navy:#1B3A6B;
  --cq-amber:#B26B00;  --cq-amber-bg:#FFF3D6;  --cq-amber-bd:#E7B53B;
  --cq-red:#D12B36;    --cq-red-bg:#FCE8EA;     --cq-red-bd:#E48089;
  --cq-ink:#1A2B45;    --cq-muted:#667085;
  --cq-bg:#F4F7FB;     --cq-card:#FFFFFF;       --cq-border:#E4E9F2;
}

html, body, [class*="css"], .stMarkdown, .stApp, input, button, textarea{
  font-family:'Plus Jakarta Sans', -apple-system, sans-serif;
}
.stApp{ background:var(--cq-bg); }

/* hide default Streamlit chrome */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"]{ display:none !important; }
header[data-testid="stHeader"]{ background:transparent; height:0; }
.block-container{ padding-top:1.1rem; padding-bottom:3rem; max-width:1180px; }

/* ── top header bar ───────────────────────────────────── */
.cq-topbar{
  display:flex; align-items:center; justify-content:space-between;
  background:var(--cq-card); border:1px solid var(--cq-border);
  border-radius:14px; padding:14px 22px; margin-bottom:18px;
  box-shadow:0 1px 2px rgba(16,30,54,.04);
}
.cq-brand{ display:flex; align-items:center; gap:13px; }
.cq-word{ font-size:23px; font-weight:800; letter-spacing:-.5px; line-height:1; }
.cq-word .can{ color:var(--cq-green); }
.cq-word .qual{ color:var(--cq-navy); }
.cq-sep{ width:1px; height:26px; background:var(--cq-border); margin:0 4px; }
.cq-eyebrow{ color:var(--cq-muted); font-size:13.5px; font-weight:600; }
.cq-user{ display:flex; align-items:center; gap:14px; }
.cq-pilltag{ background:var(--cq-green-bg); color:var(--cq-green-dk);
  font-size:11px; font-weight:700; padding:5px 11px; border-radius:20px;
  letter-spacing:.4px; text-transform:uppercase; }
.cq-avatar{ width:36px; height:36px; border-radius:50%; background:var(--cq-navy);
  color:#fff; display:flex; align-items:center; justify-content:center;
  font-size:13px; font-weight:700; }

/* page intro */
.cq-h1{ font-size:26px; font-weight:800; color:var(--cq-navy); margin:6px 0 2px; }
.cq-sub{ color:var(--cq-muted); font-size:15px; margin-bottom:6px; }

/* ── verdict banner ───────────────────────────────────── */
.cq-verdict{ display:flex; justify-content:space-between; align-items:center;
  background:var(--cq-card); border:1px solid var(--cq-border);
  border-left:6px solid var(--cq-muted); border-radius:14px;
  padding:20px 24px; margin:6px 0 16px;
  box-shadow:0 1px 3px rgba(16,30,54,.05);
  animation:cqUp .45s ease both; }
.cq-v-approved{ border-left-color:var(--cq-green); }
.cq-v-conditional{ border-left-color:var(--cq-amber-bd); }
.cq-v-disqualified{ border-left-color:var(--cq-red); }
.cq-status-pill{ display:inline-block; font-size:12px; font-weight:800;
  letter-spacing:.6px; padding:6px 13px; border-radius:8px; margin-bottom:9px; }
.cq-sp-approved{ background:var(--cq-green-bg); color:var(--cq-green-dk); }
.cq-sp-conditional{ background:var(--cq-amber-bg); color:var(--cq-amber); }
.cq-sp-disqualified{ background:var(--cq-red-bg); color:var(--cq-red); }
.cq-company{ font-size:21px; font-weight:800; color:var(--cq-ink); line-height:1.15; }
.cq-meta{ color:var(--cq-muted); font-size:13px; margin-top:7px; }
.cq-meta b{ color:var(--cq-ink); font-weight:600; }

/* compliance ring */
.cq-ring{ width:104px; height:104px; border-radius:50%; flex:0 0 auto;
  display:flex; align-items:center; justify-content:center;
  background:conic-gradient(var(--rc) calc(var(--pct)*1%), #E8ECF3 0); }
.cq-ring-in{ width:80px; height:80px; border-radius:50%; background:var(--cq-card);
  display:flex; flex-direction:column; align-items:center; justify-content:center; }
.cq-ring-pct{ font-size:23px; font-weight:800; color:var(--cq-ink); line-height:1; }
.cq-ring-lbl{ font-size:10px; font-weight:600; color:var(--cq-muted);
  text-transform:uppercase; letter-spacing:.4px; margin-top:3px; }

/* ── score cards grid (the "-Qual" cards) ─────────────── */
.cq-section{ font-size:15px; font-weight:700; color:var(--cq-navy);
  margin:18px 0 10px; }
.cq-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }
.cq-card{ background:var(--cq-card); border:1px solid var(--cq-border);
  border-left:5px solid var(--cq-muted); border-radius:12px; padding:15px 16px;
  box-shadow:0 1px 2px rgba(16,30,54,.04);
  animation:cqUp .5s ease both; transition:transform .15s ease, box-shadow .15s ease; }
.cq-card:hover{ transform:translateY(-2px); box-shadow:0 6px 16px rgba(16,30,54,.09); }
.cq-c-green{ border-left-color:var(--cq-green); }
.cq-c-amber{ border-left-color:var(--cq-amber-bd); }
.cq-c-red{ border-left-color:var(--cq-red); }
.cq-card-top{ display:flex; justify-content:space-between; align-items:center; }
.cq-tag{ font-size:10.5px; font-weight:700; padding:4px 10px; border-radius:20px;
  letter-spacing:.3px; }
.cq-tag-green{ background:var(--cq-green-bg); color:var(--cq-green-dk); }
.cq-tag-amber{ background:var(--cq-amber-bg); color:var(--cq-amber); }
.cq-tag-red{ background:var(--cq-red-bg); color:var(--cq-red); }
.cq-ico{ width:24px; height:24px; border-radius:50%; display:flex;
  align-items:center; justify-content:center; font-size:13px; font-weight:800; color:#fff; }
.cq-ico-green{ background:var(--cq-green); }
.cq-ico-amber{ background:var(--cq-amber-bd); }
.cq-ico-red{ background:var(--cq-red); }
.cq-card-title{ font-size:15px; font-weight:700; color:var(--cq-ink); margin:11px 0 3px; }
.cq-card-score{ font-size:18px; font-weight:800; color:var(--cq-ink); }
.cq-card-score .pct{ font-size:13px; font-weight:600; color:var(--cq-muted); }
.cq-card-stat{ font-size:12.5px; font-weight:700; margin-top:5px; }
.cq-t-green{ color:var(--cq-green-dk); }
.cq-t-amber{ color:var(--cq-amber); }
.cq-t-red{ color:var(--cq-red); }

/* flags / info / ai cards */
.cq-block{ background:var(--cq-card); border:1px solid var(--cq-border);
  border-radius:12px; padding:15px 18px; margin-top:14px; }
.cq-flag{ display:flex; align-items:center; gap:9px; background:var(--cq-red-bg);
  color:var(--cq-red); border:1px solid var(--cq-red-bd); border-radius:9px;
  padding:9px 13px; font-size:13.5px; font-weight:600; margin-top:8px; }
.cq-clear{ display:flex; align-items:center; gap:9px; background:var(--cq-green-bg);
  color:var(--cq-green-dk); border:1px solid #BFE3CC; border-radius:9px;
  padding:11px 14px; font-size:14px; font-weight:600; }
.cq-ai{ border-left:5px solid var(--cq-blue); }
.cq-ai p{ color:#33415C; font-size:14px; line-height:1.6; margin:0; }

/* ── comparison table ─────────────────────────────────── */
.cq-table{ width:100%; border-collapse:separate; border-spacing:0; font-size:13.5px;
  background:var(--cq-card); border:1px solid var(--cq-border);
  border-radius:12px; overflow:hidden; }
.cq-table th{ background:var(--cq-navy); color:#fff; font-weight:700;
  padding:11px 14px; text-align:center; }
.cq-table th:first-child{ text-align:left; }
.cq-table td{ padding:11px 14px; text-align:center; border-top:1px solid var(--cq-border); }
.cq-table td:first-child{ text-align:left; font-weight:700; color:var(--cq-ink); }
.cq-tbl-pill{ font-size:11.5px; font-weight:800; padding:4px 10px; border-radius:7px; }

/* ── Streamlit widget skinning ────────────────────────── */
[data-testid="stSidebar"]{ background:var(--cq-card); border-right:1px solid var(--cq-border); }
[data-testid="stSidebar"] .cq-side-logo{ font-size:19px; font-weight:800;
  letter-spacing:-.4px; margin:4px 0 2px; }
[data-testid="stSidebar"] h3{ color:var(--cq-navy); font-size:13px;
  text-transform:uppercase; letter-spacing:.5px; }
.stButton>button, .stDownloadButton>button{
  background:var(--cq-blue); color:#fff; border:none; border-radius:9px;
  font-weight:700; padding:9px 16px; transition:background .15s ease; }
.stButton>button:hover, .stDownloadButton>button:hover{ background:var(--cq-blue-dk); color:#fff; }
[data-testid="stSidebar"] .stDownloadButton>button{
  background:#fff; color:var(--cq-ink); border:1px solid var(--cq-border);
  width:100%; font-weight:600; text-align:left; }
[data-testid="stSidebar"] .stDownloadButton>button:hover{
  border-color:var(--cq-blue); color:var(--cq-blue); background:#F7FAFF; }
[data-testid="stFileUploaderDropzone"]{ background:#F7FAFF;
  border:1.5px dashed #B9CBEB; border-radius:12px; }
@keyframes cqUp{ from{ opacity:0; transform:translateY(8px); } to{ opacity:1; transform:none; } }
.cq-card:nth-child(2){ animation-delay:.05s; } .cq-card:nth-child(3){ animation-delay:.10s; }
.cq-card:nth-child(4){ animation-delay:.15s; } .cq-card:nth-child(5){ animation-delay:.20s; }
.cq-card:nth-child(6){ animation-delay:.25s; }
"""
st.markdown(f"<style>{CQ_CSS}</style>", unsafe_allow_html=True)

# CanQualify mark (original green roundel + check)
LOGO_MARK = """
<svg width="34" height="34" viewBox="0 0 34 34" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="17" cy="17" r="15.5" stroke="#2E9E5B" stroke-width="3"/>
  <path d="M10.5 17.5l4.2 4.2L23.5 12.8" stroke="#2E9E5B" stroke-width="3.2"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

# ── Top header ────────────────────────────────────────────
st.markdown(_clean_html(f"""
<div class="cq-topbar">
  <div class="cq-brand">
    {LOGO_MARK}
    <span class="cq-word"><span class="can">Can</span><span class="qual">Qualify</span></span>
    <span class="cq-sep"></span>
    <span class="cq-eyebrow">Intelligence Platform</span>
  </div>
  <div class="cq-user">
    <span class="cq-pilltag">AI Prequalification</span>
    <div class="cq-avatar">UT</div>
  </div>
</div>
"""), unsafe_allow_html=True)

st.markdown(
    '<div class="cq-h1">Contractor Qualification</div>'
    '<div class="cq-sub">Upload contractor pre-qualification packages to generate '
    'automated scorecards with AI-backed reasoning.</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════
#  Lookup tables for rendering
# ══════════════════════════════════════════════════════════
STATUS_CLASS = {
    "APPROVED": "approved", "CONDITIONAL": "conditional", "DISQUALIFIED": "disqualified",
}
RING_COLOR = {
    "APPROVED": "#2E9E5B", "CONDITIONAL": "#E7B53B", "DISQUALIFIED": "#D12B36",
}
RAG_CLASS = {"GREEN": "green", "AMBER": "amber", "RED": "red"}
RAG_ICON  = {"GREEN": "✓", "AMBER": "!", "RED": "✕"}
RAG_TEXT  = {"GREEN": "PASS", "AMBER": "REVIEW", "RED": "FAIL"}
# category -> (display label, key, CanQualify "-Qual" module, max pts)
SCORE_ROWS = [
    ("EMR Rate",            "emr",       "SafetyQual",   15),
    ("Safety Stats / TRIR", "trir",      "SafetyQual",   20),
    ("Fatality History",    "fatality",  "SafetyQual",   10),
    ("Citation History",    "citations", "AuditQual",    15),
    ("Insurance COI",       "insurance", "InsureQual",   10),
    ("Training Records",    "training",  "EmployeeQual", 10),
]


def render_verdict(company, scoring, data):
    status = scoring["final_status"]
    sc = STATUS_CLASS[status]
    pct = int((scoring["total"] / scoring["max_score"]) * 100)
    auto = " · AUTO-DQ" if scoring["auto_dq"] else ""
    meta_bits = [
        ("HQ", data.get("headquarters")),
        ("Employees", data.get("field_employees")),
        ("Revenue", data.get("annual_revenue")),
        ("Manhours", data.get("annual_manhours")),
    ]
    meta = "&nbsp;&nbsp;·&nbsp;&nbsp;".join(
        f"<b>{lbl}:</b> {val}" for lbl, val in meta_bits if val and val != "Unknown"
    ) or "<b>Company details not extracted</b>"
    return _clean_html(f"""
    <div class="cq-verdict cq-v-{sc}">
      <div>
        <span class="cq-status-pill cq-sp-{sc}">{status}{auto}</span>
        <div class="cq-company">{company}</div>
        <div class="cq-meta">{meta}</div>
      </div>
      <div class="cq-ring" style="--pct:{pct}; --rc:{RING_COLOR[status]}">
        <div class="cq-ring-in">
          <span class="cq-ring-pct">{pct}%</span>
          <span class="cq-ring-lbl">{scoring['total']}/{scoring['max_score']}</span>
        </div>
      </div>
    </div>
    """)


def render_score_grid(scoring):
    cards = ""
    for label, key, module, max_pts in SCORE_ROWS:
        rag = scoring["rag"][key]
        score = scoring["scores"][key]
        pct = int((score / max_pts) * 100)
        c = RAG_CLASS[rag]
        cards += f"""
        <div class="cq-card cq-c-{c}">
          <div class="cq-card-top">
            <span class="cq-tag cq-tag-{c}">{module}</span>
            <span class="cq-ico cq-ico-{c}">{RAG_ICON[rag]}</span>
          </div>
          <div class="cq-card-title">{label}</div>
          <div class="cq-card-score">{score} / {max_pts} <span class="pct">({pct}%)</span></div>
          <div class="cq-card-stat cq-t-{c}">{RAG_TEXT[rag]}</div>
        </div>
        """
    return _clean_html(f'<div class="cq-grid">{cards}</div>')


def render_flags(data):
    if data["red_flags"]:
        items = "".join(
            f'<div class="cq-flag"><span>&#9888;</span><span>{f}</span></div>'
            for f in data["red_flags"]
        )
        return _clean_html(f'<div class="cq-section">Risk Flags</div>{items}')
    return _clean_html('<div class="cq-clear"><span>&#10003;</span><span>No critical risk flags identified.</span></div>')


# ══════════════════════════════════════════════════════════
#  Sidebar
# ══════════════════════════════════════════════════════════
st.sidebar.markdown(_clean_html(
    f'<div style="display:flex;align-items:center;gap:9px;margin-bottom:6px">'
    f'{LOGO_MARK}<span class="cq-side-logo">'
    f'<span style="color:#2E9E5B">Can</span><span style="color:#1B3A6B">Qualify</span>'
    f'</span></div>'), unsafe_allow_html=True)

api_key = st.secrets.get("ANTHROPIC_API_KEY", "") or st.sidebar.text_input(
    "Anthropic API Key",
    type="password",
    help="Required for AI-generated explanations",
)

st.sidebar.divider()
st.sidebar.markdown("### About")
st.sidebar.markdown(
    "Automates contractor pre-qualification review using AI-powered "
    "document extraction, scoring, and analysis. Built by UT (Ultra Tendency)."
)

st.sidebar.divider()
st.sidebar.markdown("### Sample Documents")
st.sidebar.caption("Don't have a PDF handy? Download a sample:")

with open("samples/apex_industrial_prequalification.pdf", "rb") as f:
    st.sidebar.download_button(
        "Apex Industrial  ·  APPROVED",
        f, "apex_industrial_prequalification.pdf", mime="application/pdf")
with open("samples/redline_mechanical_prequalification.pdf", "rb") as f:
    st.sidebar.download_button(
        "Redline Mechanical  ·  CONDITIONAL",
        f, "redline_mechanical_prequalification.pdf", mime="application/pdf")
with open("samples/gulf_south_prequalification.pdf", "rb") as f:
    st.sidebar.download_button(
        "Gulf South Pipeline  ·  DISQUALIFIED",
        f, "gulf_south_prequalification.pdf", mime="application/pdf")

# ══════════════════════════════════════════════════════════
#  File upload
# ══════════════════════════════════════════════════════════
uploaded_files = st.file_uploader(
    "Upload contractor PDF packages",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded_files:
    all_results = []
    for uploaded_file in uploaded_files:
        with st.spinner(f"Processing {uploaded_file.name}..."):
            data = extract_contractor_fields(uploaded_file)
            if "error" in data:
                st.error(f"Failed to process {uploaded_file.name}: {data['error']}")
                continue
            scoring = score_contractor(data)
            all_results.append({
                "filename": uploaded_file.name,
                "data": data,
                "scoring": scoring,
            })

    # ── Comparison table (multi-file) ─────────────────────
    if len(all_results) > 1:
        st.markdown('<div class="cq-section">Contractor Comparison</div>',
                    unsafe_allow_html=True)
        PILL = {
            "APPROVED":     ("var(--cq-green-dk)", "var(--cq-green-bg)"),
            "CONDITIONAL":  ("var(--cq-amber)",    "var(--cq-amber-bg)"),
            "DISQUALIFIED": ("var(--cq-red)",      "var(--cq-red-bg)"),
        }
        all_results.sort(key=lambda x: x["scoring"]["total"], reverse=True)
        rows = ""
        for r in all_results:
            d, sc = r["data"], r["scoring"]
            status = sc["final_status"]
            fg, bg = PILL[status]
            emr_val = f"{d['emr_history'][0]['emr']:.2f}" if d["emr_history"] else "N/A"
            trir_val = f"{d['osha_stats'][0]['trir']}" if d["osha_stats"] else "N/A"
            rows += f"""
            <tr>
              <td>{d['company_name']}</td>
              <td><span class="cq-tbl-pill" style="color:{fg};background:{bg}">{status}</span></td>
              <td>{sc['total']}/{sc['max_score']}</td>
              <td>{emr_val}</td>
              <td>{trir_val}</td>
              <td>{d['red_flag_count']}</td>
            </tr>"""
        st.markdown(_clean_html(f"""
        <table class="cq-table">
          <thead><tr>
            <th>Contractor</th><th>Status</th><th>Score</th>
            <th>EMR</th><th>TRIR</th><th>Risk Flags</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>"""), unsafe_allow_html=True)

    # ── Individual scorecards ─────────────────────────────
    for idx, r in enumerate(all_results):
        data, scoring = r["data"], r["scoring"]
        company = data["company_name"]

        st.markdown(render_verdict(company, scoring, data), unsafe_allow_html=True)
        st.markdown('<div class="cq-section">Qualification Scores</div>',
                    unsafe_allow_html=True)
        st.markdown(render_score_grid(scoring), unsafe_allow_html=True)
        st.markdown(render_flags(data), unsafe_allow_html=True)

        # Extraction warnings
        missing = [k for k, v in {
            "Company Name": data.get("company_name"),
            "Headquarters": data.get("headquarters"),
            "EMR History":  data.get("emr_history"),
            "OSHA Stats":   data.get("osha_stats"),
        }.items() if not v or v == "Unknown"]
        if missing:
            st.warning(
                "Extraction warnings — these fields could not be read and may "
                f"affect scoring accuracy: {', '.join(missing)}")

        # AI Analysis
        explanation = None
        if api_key:
            with st.spinner("Generating AI analysis..."):
                explanation = generate_explanation(company, scoring, data, api_key)
            st.markdown(_clean_html(
                f'<div class="cq-block cq-ai"><div class="cq-section" '
                f'style="margin-top:0">AI Analysis</div><p>{explanation}</p></div>'),
                unsafe_allow_html=True)
        else:
            st.info("Add your Anthropic API key in the sidebar for AI-generated analysis.")

        # PDF download
        with st.spinner("Generating PDF scorecard..."):
            pdf_bytes = generate_scorecard_pdf(company, data, scoring, explanation)
        safe_name = (company.lower().replace(" ", "_")
                     .replace(",", "").replace(".", "")) or "contractor"
        st.download_button(
            label="⬇  Download Scorecard PDF",
            data=pdf_bytes,
            file_name=f"scorecard_{safe_name}.pdf",
            mime="application/pdf",
            key=f"download_{idx}_{safe_name}",
        )
        st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
else:
    st.info("Upload one or more contractor PDF packages above to get started.")