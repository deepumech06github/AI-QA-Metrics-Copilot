import csv
import io
import json
from pathlib import Path

from qa_metrics.exports import dashboard_to_json, release_metrics_to_csv
from qa_metrics.metrics import aggregate_summary, build_insights, calculate_release_metrics, parse_release_csv


def test_sample_csv_exports_summary_and_release_rows():
    sample = Path(__file__).parents[1] / "examples" / "release_metrics.csv"
    records = parse_release_csv(sample.read_text(encoding="utf-8"))
    metrics = calculate_release_metrics(records)
    summary = aggregate_summary(records)
    insights = build_insights(summary)

    payload = json.loads(dashboard_to_json(records, metrics, summary, insights, "sample"))
    csv_rows = list(csv.DictReader(io.StringIO(release_metrics_to_csv(metrics))))

    assert payload["project"] == "AI-QA-Metrics-Copilot"
    assert len(payload["release_metrics"]) == 12
    assert len(csv_rows) == 12

