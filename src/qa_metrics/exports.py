"""JSON and CSV export helpers for dashboards and insight summaries."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from typing import Iterable

from .models import MetricInsight, ReleaseMetrics, ReleaseRecord


def dashboard_to_json(records: Iterable[ReleaseRecord], metrics: Iterable[ReleaseMetrics], summary: dict, insights: Iterable[MetricInsight], source: str) -> str:
    return json.dumps({
        "schema_version": "1.0",
        "project": "AI-QA-Metrics-Copilot",
        "source": source,
        "interpretation_note": "Signals are diagnostic prompts, not individual or team performance ratings.",
        "summary": summary,
        "release_metrics": [asdict(item) for item in metrics],
        "insights": [asdict(item) for item in insights],
    }, indent=2, ensure_ascii=False)


def release_metrics_to_csv(metrics: Iterable[ReleaseMetrics]) -> str:
    output = io.StringIO(newline="")
    fields = ["release_id", "release_date", "pass_rate", "automation_coverage", "blocked_rate", "defect_escape_rate", "flaky_rate", "escaped_defects", "production_incidents", "automation_duration_minutes"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for metric in metrics:
        row = asdict(metric)
        for name in ("pass_rate", "automation_coverage", "blocked_rate", "defect_escape_rate", "flaky_rate"):
            row[name] = f"{row[name]:.4f}"
        writer.writerow(row)
    return output.getvalue()

