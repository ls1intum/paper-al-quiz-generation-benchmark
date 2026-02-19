"""Result data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MetricResult:
    """Result from a single metric evaluation.

    Attributes:
        metric_name: Name of the metric that was evaluated
        metric_version: Version of the metric implementation
        score: Numeric score (0-100)
        evaluator_model: Name of the LLM model used for evaluation
        quiz_id: ID of the quiz being evaluated
        question_id: ID of the question (None for quiz-level metrics)
        parameters: Metric-specific parameters used
        evaluated_at: When the evaluation was performed
        raw_response: Raw LLM response for debugging
    """

    metric_name: str
    metric_version: str
    score: float
    evaluator_model: str
    quiz_id: str
    question_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=datetime.now)
    raw_response: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate score range."""
        if not 0 <= self.score <= 100:
            raise ValueError(f"Score must be between 0 and 100, got {self.score}")


@dataclass
class EvaluationResult:
    """Result from a metric evaluation.

    Attributes:
        score: Numeric score (0-100)
        raw_response: Raw LLM response text
        metadata: Additional metric-specific data
    """

    score: float
    raw_response: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BenchmarkResult:
    """Complete result from a single benchmark run.

    Attributes:
        benchmark_id: Unique identifier for this benchmark run
        benchmark_version: Version of the benchmark framework
        config_hash: Hash of the configuration used
        quiz_id: ID of the quiz evaluated
        run_number: Run number (for multiple runs)
        metrics: List of all metric results
        started_at: When the benchmark started
        completed_at: When the benchmark completed
        metadata: Additional metadata
    """

    benchmark_id: str
    benchmark_version: str
    config_hash: str
    quiz_id: str
    run_number: int
    metrics: List[MetricResult]
    started_at: datetime
    completed_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        """Calculate the duration of the benchmark run in seconds."""
        return (self.completed_at - self.started_at).total_seconds()

    def get_results_by_metric(self, metric_name: str) -> List[MetricResult]:
        """Get all results for a specific metric.

        Args:
            metric_name: Name of the metric

        Returns:
            List of metric results matching the name
        """
        return [m for m in self.metrics if m.metric_name == metric_name]


@dataclass
class MetricAggregation:
    """Aggregated statistics for a single metric across multiple runs.

    Attributes:
        metric_name: Name of the metric
        evaluator_model: Model used for evaluation
        mean: Mean score across runs
        median: Median score
        std_dev: Standard deviation
        min: Minimum score
        max: Maximum score
        per_run_scores: Scores from each individual run
        num_runs: Number of runs aggregated
    """

    metric_name: str
    evaluator_model: str
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    per_run_scores: List[float]
    num_runs: int = field(init=False)

    def __post_init__(self) -> None:
        """Calculate number of runs."""
        self.num_runs = len(self.per_run_scores)


@dataclass
class AggregatedResults:
    """Aggregated results across multiple benchmark runs.

    Attributes:
        benchmark_config_name: Name of the benchmark configuration
        benchmark_version: Version of the benchmark framework
        quiz_ids: List of quiz IDs evaluated
        total_runs: Total number of runs performed
        aggregations: Dictionary mapping (metric_name, evaluator) to aggregation
        created_at: When the aggregation was created
        metadata: Additional metadata
    """

    benchmark_config_name: str
    benchmark_version: str
    quiz_ids: List[str]
    total_runs: int
    aggregations: Dict[str, MetricAggregation]  # key: f"{metric_name}_{evaluator_model}"
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_aggregation(
        self, metric_name: str, evaluator_model: str
    ) -> Optional[MetricAggregation]:
        """Get aggregation for a specific metric and evaluator.

        Args:
            metric_name: Name of the metric
            evaluator_model: Model used for evaluation

        Returns:
            MetricAggregation if found, None otherwise
        """
        key = f"{metric_name}_{evaluator_model}"
        return self.aggregations.get(key)

    def get_all_metrics(self) -> List[str]:
        """Get list of all unique metric names.

        Returns:
            List of metric names
        """
        return list(set(agg.metric_name for agg in self.aggregations.values()))

    def get_all_evaluators(self) -> List[str]:
        """Get list of all unique evaluator models.

        Returns:
            List of evaluator model names
        """
        return list(set(agg.evaluator_model for agg in self.aggregations.values()))
