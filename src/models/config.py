"""Configuration data models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvaluatorConfig:
    """Configuration for an LLM evaluator.

    Attributes:
        name: Unique name for this evaluator instance
        provider: Provider type (azure_openai, openai, anthropic, etc.)
        model: Model name/identifier
        temperature: Sampling temperature (default: 0.0 for deterministic)
        max_tokens: Maximum tokens in response
        additional_params: Provider-specific parameters
    """

    name: str
    provider: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 500
    additional_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricConfig:
    """Configuration for a metric evaluation.

    Attributes:
        name: Name of the metric to evaluate
        version: Version of the metric implementation
        evaluators: List of evaluator names to use for this metric
        parameters: Metric-specific parameters
        enabled: Whether this metric is enabled
    """

    name: str
    version: str
    evaluators: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class InputOutputConfig:
    """Configuration for input/output paths.

    Attributes:
        quiz_directory: Directory containing quiz JSON files
        source_directory: Directory containing source markdown files
        results_directory: Directory for output results
    """

    quiz_directory: str
    source_directory: str
    results_directory: str


@dataclass
class BenchmarkConfig:
    """Complete benchmark configuration.

    Attributes:
        name: Name of this benchmark configuration
        version: Version of the benchmark framework
        runs: Number of times to repeat the evaluation
        evaluators: Dictionary of evaluator configurations
        metrics: List of metric configurations
        input_output: Input/output path configuration
        metadata: Additional metadata
    """

    name: str
    version: str
    runs: int
    evaluators: Dict[str, EvaluatorConfig]
    metrics: List[MetricConfig]
    input_output: InputOutputConfig
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_evaluator(self, name: str) -> Optional[EvaluatorConfig]:
        """Get evaluator configuration by name.

        Args:
            name: Name of the evaluator

        Returns:
            EvaluatorConfig if found, None otherwise
        """
        return self.evaluators.get(name)

    def get_metric(self, name: str) -> Optional[MetricConfig]:
        """Get metric configuration by name.

        Args:
            name: Name of the metric

        Returns:
            MetricConfig if found, None otherwise
        """
        for metric in self.metrics:
            if metric.name == name:
                return metric
        return None

    def get_enabled_metrics(self) -> List[MetricConfig]:
        """Get all enabled metrics.

        Returns:
            List of enabled metric configurations
        """
        return [m for m in self.metrics if m.enabled]

    def validate(self) -> None:
        """Validate the configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        # Check that all metric evaluators exist
        for metric in self.metrics:
            for evaluator_name in metric.evaluators:
                if evaluator_name not in self.evaluators:
                    raise ValueError(
                        f"Metric '{metric.name}' references unknown evaluator '{evaluator_name}'"
                    )

        # Check runs is positive
        if self.runs < 1:
            raise ValueError(f"Number of runs must be at least 1, got {self.runs}")
