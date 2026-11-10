import pytest

from qa_metrics.metrics import MetricThresholds, aggregate_summary, build_insights, calculate_release_metrics, parse_release_csv


SAMPLE = """release_id,release_date,total_tests,passed_tests,failed_tests,blocked_tests,automated_tests,escaped_defects,pre_release_defects,production_incidents,flaky_tests,automation_duration_minutes
R1,2026-01-01,100,80,10,10,70,2,8,0,4,20
R2,2026-01-08,100,70,20,10,75,4,6,1,8,30
"""


def test_csv_parser_sorts_records_and_metrics_are_weighted():
    records = parse_release_csv(SAMPLE)
    metrics = calculate_release_metrics(records)
    summary = aggregate_summary(records)

    assert [row.release_id for row in records] == ["R1", "R2"]
    assert metrics[0].pass_rate == pytest.approx(80 / 90)
    assert summary["pass_rate"] == pytest.approx(150 / 180)
    assert summary["defect_escape_rate"] == pytest.approx(6 / 20)


def test_inconsistent_counts_are_rejected():
    bad = SAMPLE.replace("R1,2026-01-01,100,80,10,10", "R1,2026-01-01,100,90,20,10")

    with pytest.raises(ValueError, match="cannot exceed total_tests"):
        parse_release_csv(bad)


def test_threshold_signals_are_explainable():
    summary = aggregate_summary(parse_release_csv(SAMPLE))
    insights = build_insights(summary, MetricThresholds(min_pass_rate=0.95, min_automation_coverage=0.90))

    assert any("pass rate" in insight.title.lower() for insight in insights)
    assert all(insight.evidence and insight.recommended_action for insight in insights)

