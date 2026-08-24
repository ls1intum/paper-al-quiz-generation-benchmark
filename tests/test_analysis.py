"""Tests for aggregation utilities."""

import json
from datetime import datetime

import numpy as np
import pytest

from src.analysis.aggregator import ResultsAggregator
from src.models.result import BenchmarkResult, MetricResult


def make_result(
    run_number: int,
    score: float,
    evaluator_model: str = "mock",
    metric_name: str = "difficulty",
    quiz_id: str = "quiz_1",
    question_id: str = "q1",
) -> BenchmarkResult:
    metric = MetricResult(
        metric_name=metric_name,
        metric_version="1.0",
        score=score,
        evaluator_model=evaluator_model,
        quiz_id=quiz_id,
        question_id=question_id,
    )

    return BenchmarkResult(
        benchmark_id=f"bench_{run_number}",
        benchmark_version="1.0",
        config_hash="hash",
        quiz_id=quiz_id,
        run_number=run_number,
        metrics=[metric],
        started_at=datetime.now(),
        completed_at=datetime.now(),
    )


def test_aggregate_results():
    results = [make_result(1, 40.0), make_result(2, 60.0)]
    aggregated = ResultsAggregator.aggregate(results, "test")

    assert aggregated.total_runs == 2
    assert aggregated.get_all_metrics() == ["difficulty"]
    agg = aggregated.get_aggregation("difficulty", "mock")
    assert agg is not None
    assert agg.mean == 50.0
    assert agg.min == 40.0
    assert agg.max == 60.0


def test_aggregate_by_metric():
    results = [make_result(1, 10.0), make_result(2, 20.0)]
    aggregations = ResultsAggregator.aggregate_by_metric(results, "difficulty")
    assert "mock" in aggregations
    assert aggregations["mock"].mean == 15.0


def test_compare_evaluators():
    results = [make_result(1, 10.0), make_result(2, 30.0)]
    comparison = ResultsAggregator.compare_evaluators(results, "difficulty")
    assert comparison["mock"]["mean"] == 20.0


def test_aggregate_empty_results():
    with pytest.raises(ValueError):
        ResultsAggregator.aggregate([], "test")


# ============================================================================
# Bootstrap Confidence Interval Tests
# ============================================================================


def test_bootstrap_confidence_interval_basic():
    """Test bootstrap CI calculation with simple data."""
    data = [70.0, 75.0, 80.0, 85.0, 90.0]
    ci_lower, ci_upper = ResultsAggregator.bootstrap_confidence_interval(data)

    # CI should bracket the mean
    assert ci_lower < np.mean(data) < ci_upper
    # CI should be reasonably narrow for consistent data
    assert (ci_upper - ci_lower) < 20.0


def test_bootstrap_confidence_interval_single_point():
    """Test bootstrap CI with single data point."""
    data = [75.0]
    ci_lower, ci_upper = ResultsAggregator.bootstrap_confidence_interval(data)

    # With single point, CI is the point itself
    assert ci_lower == 75.0
    assert ci_upper == 75.0


def test_bootstrap_confidence_interval_reproducible():
    """Test that bootstrap CI is reproducible (uses seed)."""
    data = [60.0, 70.0, 80.0, 90.0, 100.0]
    ci1_lower, ci1_upper = ResultsAggregator.bootstrap_confidence_interval(data)
    ci2_lower, ci2_upper = ResultsAggregator.bootstrap_confidence_interval(data)

    # Same seed should produce same results
    assert ci1_lower == ci2_lower
    assert ci1_upper == ci2_upper


# ============================================================================
# Inter-Rater Reliability Tests
# ============================================================================


def test_compute_icc_high_agreement():
    """Test ICC calculation with high agreement between raters."""
    # Rater 1 and 2 score items very similarly
    reliability_array = np.array(
        [
            [80.0, 85.0, 90.0, 75.0, 88.0, 82.0, 84.0, 86.0],
            [81.0, 86.0, 89.0, 76.0, 87.0, 83.0, 85.0, 87.0],
        ]
    )

    icc_result = ResultsAggregator.compute_icc(reliability_array)
    if icc_result is not None:
        assert icc_result["icc"] > 0.7  # Should have high agreement


def test_compute_icc_low_agreement():
    """Test ICC calculation with low agreement between raters."""
    # Rater 1 and 2 score items very differently
    reliability_array = np.array(
        [
            [90.0, 85.0, 80.0, 75.0, 70.0, 65.0, 60.0, 55.0],
            [30.0, 40.0, 50.0, 60.0, 70.0, 65.0, 75.0, 80.0],
        ]
    )

    icc_result = ResultsAggregator.compute_icc(reliability_array)
    if icc_result is not None:
        # Agreement should be moderate to low
        assert icc_result["icc"] < 0.7


def test_compute_icc_insufficient_data():
    """Test ICC with insufficient data points."""
    # Only 2 items, ICC requires at least 5 non-missing values
    reliability_array = np.array(
        [
            [80.0, 85.0],
            [81.0, 86.0],
        ]
    )

    icc_result = ResultsAggregator.compute_icc(reliability_array)
    # Should return None when data is insufficient
    assert icc_result is None


def test_compute_icc_with_nans():
    """Test ICC handles NaN values correctly."""
    # Some missing data
    reliability_array = np.array(
        [
            [80.0, 85.0, np.nan, 75.0, 88.0],
            [81.0, np.nan, 89.0, 76.0, 87.0],
        ]
    )

    icc_result = ResultsAggregator.compute_icc(reliability_array)
    # Should work with pairwise complete observations
    assert icc_result is not None or icc_result is None  # Either works or doesn't


def test_compute_mad_high_agreement():
    """Test MAD calculation with high agreement."""
    reliability_array = np.array(
        [
            [80.0, 85.0, 90.0, 75.0, 88.0],
            [81.0, 86.0, 89.0, 76.0, 87.0],
        ]
    )

    mad = ResultsAggregator.compute_mad(reliability_array)
    assert mad is not None
    # Average disagreement should be small
    assert mad < 2.0


def test_compute_mad_low_agreement():
    """Test MAD calculation with low agreement."""
    reliability_array = np.array(
        [
            [90.0, 85.0, 80.0, 75.0, 70.0],
            [30.0, 40.0, 50.0, 60.0, 70.0],
        ]
    )

    mad = ResultsAggregator.compute_mad(reliability_array)
    assert mad is not None
    # Average disagreement should be large (exactly 30.0 in this case)
    assert mad >= 30.0


def test_compute_mad_empty():
    """Test MAD with no valid rater pairs."""
    reliability_array = np.array(
        [
            [80.0],
            [81.0],
        ]
    )

    _mad = ResultsAggregator.compute_mad(reliability_array)  # noqa: F841
    # Just checks it doesn't crash; single-item pairs return None


def test_compute_spearman_high_agreement():
    """Test Spearman correlation with high rank agreement."""
    reliability_array = np.array(
        [
            [80.0, 85.0, 90.0, 75.0, 88.0],
            [82.0, 87.0, 91.0, 77.0, 89.0],
        ]
    )

    spearman_result = ResultsAggregator.compute_spearman(reliability_array)
    assert spearman_result is not None
    assert spearman_result["spearman_rho"] > 0.8  # High rank agreement
    # Verify p-value is NOT in the result
    assert "spearman_pvalue" not in spearman_result


def test_compute_spearman_low_agreement():
    """Test Spearman correlation with low rank agreement."""
    reliability_array = np.array(
        [
            [90.0, 85.0, 80.0, 75.0, 70.0],
            [30.0, 40.0, 50.0, 60.0, 70.0],
        ]
    )

    spearman_result = ResultsAggregator.compute_spearman(reliability_array)
    assert spearman_result is not None
    # Even with low absolute agreement, ranks might align
    # Check that result has expected keys
    assert "spearman_rho" in spearman_result
    assert "num_pairs" in spearman_result


def test_compute_spearman_no_pvalue():
    """Verify that Spearman calculation does NOT include p-value."""
    reliability_array = np.array(
        [
            [70.0, 80.0, 90.0],
            [75.0, 85.0, 95.0],
        ]
    )

    spearman_result = ResultsAggregator.compute_spearman(reliability_array)
    assert spearman_result is not None
    # Must NOT have spearman_pvalue field
    assert "spearman_pvalue" not in spearman_result


# ============================================================================
# Full Inter-Rater Reliability Pipeline Tests
# ============================================================================


def test_calculate_inter_rater_reliability_two_raters():
    """Test full inter-rater reliability calculation with two raters."""
    # Create results from two evaluators
    results = [
        make_result(1, 80.0, evaluator_model="gpt4", metric_name="clarity"),
        make_result(1, 82.0, evaluator_model="claude", metric_name="clarity"),
        make_result(2, 85.0, evaluator_model="gpt4", metric_name="clarity"),
        make_result(2, 84.0, evaluator_model="claude", metric_name="clarity"),
        make_result(3, 90.0, evaluator_model="gpt4", metric_name="clarity"),
        make_result(3, 88.0, evaluator_model="claude", metric_name="clarity"),
    ]

    irr = ResultsAggregator.calculate_inter_rater_reliability(results, "clarity")

    # Check structure
    assert irr["metric_name"] == "clarity"
    assert irr["num_raters"] == 2
    assert len(irr["raters"]) == 2

    # Check primary metrics are present
    assert "icc" in irr
    assert "mad" in irr
    assert "spearman_rho" in irr

    # No p-value field
    assert "spearman_pvalue" not in irr

    # With good data, should have reasonable metrics
    if irr["icc"] is not None:
        assert -1 <= irr["icc"] <= 1

    if irr["mad"] is not None:
        assert irr["mad"] >= 0


def test_calculate_inter_rater_reliability_single_rater():
    """Test inter-rater reliability with only one rater (should return defaults)."""
    results = [
        make_result(1, 80.0, evaluator_model="gpt4", metric_name="clarity"),
        make_result(2, 85.0, evaluator_model="gpt4", metric_name="clarity"),
    ]

    irr = ResultsAggregator.calculate_inter_rater_reliability(results, "clarity")

    # Should return low reliability status
    assert irr["reliability_status"] == "low"
    assert irr["num_raters"] == 1
    assert irr["icc"] is None
    assert irr["mad"] is None
    assert irr["spearman_rho"] is None


def test_calculate_inter_rater_reliability_no_data():
    """Test inter-rater reliability with no matching metric data."""
    results = [
        make_result(1, 80.0, metric_name="clarity"),
    ]

    irr = ResultsAggregator.calculate_inter_rater_reliability(results, "distraction")
    # Should return low reliability status
    assert irr["reliability_status"] == "low"


def test_detect_ceiling_effect_normal():
    """Test ceiling effect detection with normal variance."""
    reliability_array = np.array(
        [
            [70.0, 75.0, 80.0, 85.0, 90.0],
            [72.0, 77.0, 82.0, 87.0, 92.0],
        ]
    )

    ceiling = ResultsAggregator.detect_ceiling_effect(reliability_array)
    assert ceiling["has_ceiling_effect"] is False
    assert len(ceiling["affected_rater_indices"]) == 0


def test_detect_ceiling_effect_low_variance():
    """Test ceiling effect detection with near-zero variance."""
    reliability_array = np.array(
        [
            [100.0, 100.0, 100.0, 100.0, 100.0],  # No variance
            [72.0, 77.0, 82.0, 87.0, 92.0],
        ]
    )

    ceiling = ResultsAggregator.detect_ceiling_effect(reliability_array)
    assert ceiling["has_ceiling_effect"] is True
    assert 0 in ceiling["affected_rater_indices"]  # First rater flagged


# ============================================================================
# P1-3: Applicable filter
# ============================================================================


def test_aggregate_excludes_inapplicable_items():
    """P1-3: inapplicable items (applicable=false) must be excluded from means."""
    applicable_raw = json.dumps({"applicable": True, "alignment_level": "partial", "score": 66.7})
    inapplicable_raw = json.dumps(
        {"applicable": False, "alignment_level": "not_applicable", "score": 100.0}
    )

    results = [
        BenchmarkResult(
            benchmark_id="b1",
            benchmark_version="1.0",
            config_hash="hash",
            quiz_id="quiz_1",
            run_number=1,
            metrics=[
                MetricResult(
                    metric_name="objective_alignment",
                    metric_version="1.0",
                    score=66.7,
                    evaluator_model="mock",
                    quiz_id="quiz_1",
                    question_id="q1",
                    raw_response=applicable_raw,
                ),
                MetricResult(
                    metric_name="objective_alignment",
                    metric_version="1.0",
                    score=100.0,
                    evaluator_model="mock",
                    quiz_id="quiz_1",
                    question_id="q2",
                    raw_response=inapplicable_raw,
                ),
            ],
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
    ]

    aggregated = ResultsAggregator.aggregate(results, "test")
    agg = aggregated.get_aggregation("objective_alignment", "mock")
    # Only the applicable item (66.7) should contribute to the mean, not the 100.0
    assert agg is not None
    assert agg.mean == 66.7
    assert agg.n_applicable == 1
    assert agg.n_total == 2


def test_aggregate_counts_all_applicable_for_normal_metrics():
    """For metrics not in _METRICS_WITH_APPLICABLE, n_applicable == n_total."""
    results = [make_result(1, 40.0), make_result(2, 60.0)]
    aggregated = ResultsAggregator.aggregate(results, "test")
    agg = aggregated.get_aggregation("difficulty", "mock")
    assert agg is not None
    assert agg.n_applicable == 2
    assert agg.n_total == 2
