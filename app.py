"""Streamlit dashboard for the AI QA Metrics Copilot."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from qa_metrics.exports import dashboard_to_json, release_metrics_to_csv
from qa_metrics.llm import generate_metric_narrative
from qa_metrics.metrics import MetricThresholds, aggregate_summary, build_insights, calculate_release_metrics, parse_release_csv


def _api_key() -> str | None:
    key = os.getenv("OPENAI_API_KEY", "")
    try:
        key = key or st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        pass
    return key or None


SAMPLE_CSV = (Path(__file__).parent / "examples" / "release_metrics.csv").read_text(encoding="utf-8")

st.set_page_config(page_title="AI QA Metrics Copilot", page_icon="📊", layout="wide")
st.title("📊 AI QA Metrics Copilot")
st.caption("Turn release and test data into contextual, explainable quality signals.")

dashboard_tab, data_tab, about_tab = st.tabs(["Quality dashboard", "Data & AI summary", "About & architecture"])

with dashboard_tab:
    st.subheader("Release metrics overview")
    source_mode = st.radio("Data source", ["Included demo data", "Upload release CSV"], horizontal=True)
    if source_mode == "Included demo data":
        csv_text = SAMPLE_CSV
        source_label = "Fictional sample data"
        st.caption("The included data is synthetic and intended only to demonstrate the dashboard.")
    else:
        file = st.file_uploader("Upload release metrics CSV", type=["csv"])
        csv_text = file.getvalue().decode("utf-8-sig") if file is not None else ""
        source_label = file.name if file is not None else "Uploaded CSV"
        st.caption("CSV data is processed locally in this app. Only aggregate metrics are sent if you explicitly request the optional LLM narrative.")
    if not csv_text:
        st.session_state.pop("qa_metrics_payload", None)
        st.session_state.pop("qa_narrative", None)

    with st.expander("Adjust example signal thresholds"):
        t1, t2, t3 = st.columns(3)
        min_pass = t1.slider("Minimum pass-rate guide", 0.50, 1.00, 0.95, 0.01)
        min_coverage = t2.slider("Minimum automation-coverage guide", 0.00, 1.00, 0.75, 0.01)
        max_blocked = t3.slider("Maximum blocked-rate guide", 0.00, 0.50, 0.10, 0.01)
        t4, t5, t6 = st.columns(3)
        max_escape = t4.slider("Maximum defect-escape guide", 0.00, 0.75, 0.15, 0.01)
        max_flaky = t5.slider("Maximum flaky-test guide", 0.00, 0.50, 0.05, 0.01)
        max_growth = t6.slider("Maximum runtime growth guide (%)", 0.0, 100.0, 20.0, 1.0)
    thresholds = MetricThresholds(min_pass, min_coverage, max_blocked, max_escape, max_flaky, max_growth)

    try:
        if not csv_text:
            st.info("Upload a CSV to view metrics.")
            records = []
            metrics = []
            summary = None
            insights = []
        else:
            records = parse_release_csv(csv_text)
            metrics = calculate_release_metrics(records)
            summary = aggregate_summary(records)
            insights = build_insights(summary, thresholds)
            new_payload = (records, metrics, summary, insights, source_label)
            if st.session_state.get("qa_metrics_payload") != new_payload:
                st.session_state.pop("qa_narrative", None)
            st.session_state["qa_metrics_payload"] = new_payload
    except ValueError as exc:
        st.error(str(exc))
        st.session_state.pop("qa_metrics_payload", None)
        st.session_state.pop("qa_narrative", None)
        records = []
        metrics = []
        summary = None
        insights = []

    payload = st.session_state.get("qa_metrics_payload")
    if summary is not None and records:
        kpis = st.columns(5)
        kpis[0].metric("Releases", summary["release_count"])
        kpis[1].metric("Test pass rate", f"{summary['pass_rate']:.1%}")
        kpis[2].metric("Automation coverage", f"{summary['automation_coverage']:.1%}")
        kpis[3].metric("Defect escape share", f"{summary['defect_escape_rate']:.1%}")
        kpis[4].metric("Production incidents", summary["production_incidents"])

        frame = pd.DataFrame([item.to_dict() for item in metrics]).set_index("release_id")
        chart_left, chart_right = st.columns(2)
        chart_left.markdown("**Pass rate and automation coverage**")
        chart_left.line_chart(frame[["pass_rate", "automation_coverage"]] * 100)
        chart_left.caption("Percent")
        chart_right.markdown("**Escaped defects and production incidents**")
        chart_right.bar_chart(frame[["escaped_defects", "production_incidents"]])
        st.markdown("**Signals to investigate**")
        for insight in insights:
            with st.container(border=True):
                st.markdown(f"**{insight.severity} · {insight.title}**")
                st.write(insight.evidence)
                st.caption(f"Suggested discussion: {insight.recommended_action}")
        st.download_button("Download metrics CSV", release_metrics_to_csv(metrics), "qa-release-metrics.csv", "text/csv")
        st.download_button("Download dashboard JSON", dashboard_to_json(records, metrics, summary, insights, source_label), "qa-metrics-summary.json", "application/json")
        st.caption("Thresholds are editable examples. Interpret signals alongside product risk, release scope, customer impact, and data quality.")

with data_tab:
    st.subheader("Metric definitions and AI narrative")
    st.markdown("""
    - **Pass rate:** passed ÷ (passed + failed); blocked tests are shown separately.
    - **Automation coverage:** automated tests ÷ total test inventory.
    - **Blocked rate:** blocked tests ÷ total test inventory.
    - **Defect escape share:** escaped defects ÷ (escaped + pre-release defects recorded).
    - **Flaky-test rate:** flaky tests ÷ total test inventory.

    These are diagnostic signals. They are not a quality score and should not be used to rank individuals or teams.
    """)
    if "qa_metrics_payload" in st.session_state:
        records, metrics, summary, insights, source_label = st.session_state["qa_metrics_payload"]
        st.dataframe(pd.DataFrame([item.to_dict() for item in metrics]), use_container_width=True, hide_index=True)
        narrative_mode = st.radio("Narrative mode", ["Offline rule summary", "OpenAI narrative"], horizontal=True)
        if st.button("Generate concise QA review summary", type="primary"):
            if narrative_mode == "Offline rule summary":
                text = " ".join(f"{item.title}: {item.evidence} Suggested discussion: {item.recommended_action}" for item in insights)
                st.session_state["qa_narrative"] = text
            else:
                try:
                    st.session_state["qa_narrative"] = generate_metric_narrative(
                        summary, [item.to_dict() for item in insights], api_key=_api_key()
                    )
                except Exception as exc:
                    st.error(str(exc))
        if st.session_state.get("qa_narrative"):
            st.markdown("**Review summary**")
            st.write(st.session_state["qa_narrative"])
    else:
        st.info("Load data on the Quality dashboard tab to view the detailed metric table and summary options.")

with about_tab:
    st.subheader("Metrics that support learning")
    st.markdown("""
    This portfolio demo shows a leadership-friendly way to discuss test health without turning metrics into individual scorecards:

    - Contextual thresholds can be tuned to the product and release model.
    - Trend signals include evidence and a suggested investigation path.
    - The optional LLM narrative sees aggregate metrics and rule-based signals, not raw defect descriptions.
    - CSV validation rejects inconsistent counts and dates before analysis.
    - Exports make definitions and caveats visible to downstream readers.

    See `docs/architecture.md` for design and rollout considerations.
    """)

