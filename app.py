import streamlit as st
from pipeline import (
    extract_contractor_fields,
    score_contractor,
    generate_explanation,
    generate_scorecard_pdf
)

# ── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title="CanQualify Intelligence Platform",
    page_icon="📋",
    layout="centered"
)

# ── Header ────────────────────────────────────────────────
st.title("CanQualify Intelligence Platform")
st.markdown("Upload contractor pre-qualification packages to generate automated scorecards.")
st.divider()

# ── Sidebar ───────────────────────────────────────────────
api_key = st.secrets.get("ANTHROPIC_API_KEY", "") or st.sidebar.text_input(
    "Anthropic API Key",
    type="password",
    help="Required for AI-generated explanations"
)

st.sidebar.divider()
st.sidebar.markdown("### About")
st.sidebar.markdown(
    "This platform automates contractor pre-qualification "
    "review using AI-powered document extraction, scoring, "
    "and analysis. Built by UT (Ultra Tendency)."
)

# ── Sample documents ──────────────────────────────────────
st.sidebar.divider()
st.sidebar.markdown("### Sample Documents")
st.sidebar.markdown("Don't have a PDF handy? Download a sample:")

with open("samples/apex_industrial_prequalification.pdf", "rb") as f:
    st.sidebar.download_button(
        "Apex Industrial (APPROVED)",
        f, "apex_industrial_prequalification.pdf",
        mime="application/pdf"
    )
with open("samples/redline_mechanical_prequalification.pdf", "rb") as f:
    st.sidebar.download_button(
        "Redline Mechanical (CONDITIONAL)",
        f, "redline_mechanical_prequalification.pdf",
        mime="application/pdf"
    )
with open("samples/gulf_south_prequalification.pdf", "rb") as f:
    st.sidebar.download_button(
        "Gulf South Pipeline (DISQUALIFIED)",
        f, "gulf_south_prequalification.pdf",
        mime="application/pdf"
    )

# ── File Upload ───────────────────────────────────────────
uploaded_files = st.file_uploader(
    "Upload contractor PDF packages",
    type=["pdf"],
    accept_multiple_files=True
)

# ── Process all files first ───────────────────────────────
if uploaded_files:

    all_results = []

    for uploaded_file in uploaded_files:
        with st.spinner(f"Processing {uploaded_file.name}..."):
            data    = extract_contractor_fields(uploaded_file)
            if "error" in data:
                st.error(f"Failed to process {uploaded_file.name}: {data['error']}")
                continue
            scoring = score_contractor(data)
            all_results.append({
                "filename": uploaded_file.name,
                "data":     data,
                "scoring":  scoring
            })

    # ── Comparison table ──────────────────────────────────
    if len(all_results) > 1:
        st.markdown("## Contractor Comparison")

        STATUS_COLORS_HTML = {
            "APPROVED":     ("#375623", "#E2EFDA"),
            "CONDITIONAL":  ("#7F6000", "#FFF2CC"),
            "DISQUALIFIED": ("#C00000", "#FFE0E0"),
        }
        RAG_ICONS = {
            "GREEN": "✅", "AMBER": "⚠️", "RED": "❌"
        }

        # Sort by total score descending
        all_results.sort(
            key=lambda x: x["scoring"]["total"], reverse=True)

        # Build HTML table
        rows = ""
        for r in all_results:
            d  = r["data"]
            sc = r["scoring"]
            status = sc["final_status"]
            fg, bg = STATUS_COLORS_HTML[status]
            emr_val  = (f"{d['emr_history'][0]['emr']:.2f}"
                        if d["emr_history"] else "N/A")
            trir_val = (f"{d['osha_stats'][0]['trir']}"
                        if d["osha_stats"] else "N/A")
            rows += f"""
            <tr>
                <td><b>{d['company_name']}</b></td>
                <td style="background:{bg}; color:{fg}; 
                           font-weight:bold; text-align:center">
                    {status}
                </td>
                <td style="text-align:center">
                    {sc['total']}/{sc['max_score']}
                </td>
                <td style="text-align:center">{emr_val}</td>
                <td style="text-align:center">{trir_val}</td>
                <td style="text-align:center">{d['red_flag_count']}</td>
            </tr>
            """

        table_html = f"""
        <table style="width:100%; border-collapse:collapse; 
                      font-family:sans-serif; font-size:14px">
            <thead>
                <tr style="background:#1F4E79; color:white">
                    <th style="padding:8px; text-align:left">Contractor</th>
                    <th style="padding:8px; text-align:center">Status</th>
                    <th style="padding:8px; text-align:center">Score</th>
                    <th style="padding:8px; text-align:center">EMR</th>
                    <th style="padding:8px; text-align:center">TRIR</th>
                    <th style="padding:8px; text-align:center">Red Flags</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        """
        st.html(table_html)
        st.divider()

    # ── Individual scorecards ─────────────────────────────
    for r in all_results:
        data    = r["data"]
        scoring = r["scoring"]
        company = data["company_name"]

        st.markdown(f"## {company}")

        # Status and score
        status = scoring["final_status"]
        color  = {"APPROVED": "green",
                  "CONDITIONAL": "orange",
                  "DISQUALIFIED": "red"}[status]
        auto_note = " (AUTO-DISQUALIFIED)" if scoring["auto_dq"] else ""
        st.markdown(
            f"**Status:** :{color}[{status}{auto_note}]  |  "
            f"**Score:** {scoring['total']} / {scoring['max_score']}"
        )

        # Company info
        with st.expander("Company Information"):
            col1, col2 = st.columns(2)
            col1.metric("Headquarters",
                        data.get("headquarters") or "N/A")
            col1.metric("Employees",
                        data.get("field_employees") or "N/A")
            col2.metric("Revenue",
                        data.get("annual_revenue") or "N/A")
            col2.metric("Manhours",
                        data.get("annual_manhours") or "N/A")

        # Scores
        with st.expander("Qualification Scores", expanded=True):
            SCORE_LABELS = [
                ("EMR",                 "emr",       15),
                ("Safety Stats / TRIR", "trir",       20),
                ("Fatality History",    "fatality",   10),
                ("Citation History",    "citations",  15),
                ("Insurance",           "insurance",  10),
                ("Training",            "training",   10),
            ]
            for label, key, max_pts in SCORE_LABELS:
                rag   = scoring["rag"][key]
                score = scoring["scores"][key]
                pct   = int((score / max_pts) * 100)
                icon  = {"GREEN": "✅",
                         "AMBER": "⚠️",
                         "RED": "❌"}[rag]
                st.markdown(
                    f"{icon} **{label}:** {score}/{max_pts} ({pct}%)")

        # Red flags
        if data["red_flags"]:
            with st.expander("Risk Flags", expanded=True):
                for flag in data["red_flags"]:
                    st.error(f"⚠️ {flag}")
        else:
            st.success("No critical risk flags identified.")

        # Extraction confidence
        missing = [k for k, v in {
            "Company Name":  data.get("company_name"),
            "Headquarters":  data.get("headquarters"),
            "EMR History":   data.get("emr_history"),
            "OSHA Stats":    data.get("osha_stats"),
        }.items() if not v]
        if missing:
            with st.expander("⚠️ Extraction Warnings"):
                st.warning(
                    f"The following fields could not be extracted "
                    f"and may affect scoring accuracy: "
                    f"{', '.join(missing)}")

        # AI Explanation
        explanation = None
        if api_key:
            with st.spinner("Generating AI analysis..."):
                explanation = generate_explanation(
                    company, scoring, data, api_key)
            with st.expander("AI Analysis", expanded=True):
                st.write(explanation)
        else:
            st.info(
                "Add your Anthropic API key in the sidebar "
                "for AI-generated analysis.")

        # PDF download
        with st.spinner("Generating PDF scorecard..."):
            pdf_bytes = generate_scorecard_pdf(
                company, data, scoring, explanation)

        safe_name = (company.lower()
                     .replace(" ", "_")
                     .replace(",", "")
                     .replace(".", ""))
        key_base = (safe_name if company != "Uknown"
                    else r["filename"].replace(")", "").replace(".pdf", "")
                    .replace(" ", "_")) 
        st.download_button(
            label="⬇️ Download Scorecard PDF",
            data=pdf_bytes,
            file_name=f"scorecard_{safe_name}.pdf",
            mime="application/pdf",
            key=f"download_{key_base}"
        )
        st.divider()

else:
    st.info(
        "Upload one or more contractor PDF packages above "
        "to get started.")