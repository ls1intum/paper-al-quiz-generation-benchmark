"""Registry for metric discovery and instantiation."""

from typing import Dict, List, Optional, Type

from .base import BaseMetric


class MetricRegistry:
    """Registry for managing available metrics.

    Provides a central place to register and retrieve metric implementations.
    """

    _metrics: Dict[str, Type[BaseMetric]] = {}

    @classmethod
    def register(cls, metric_class: Type[BaseMetric]) -> None:
        """Register a metric class.

        Args:
            metric_class: Metric class to register

        Raises:
            ValueError: If metric_class doesn't inherit from BaseMetric
        """
        if not issubclass(metric_class, BaseMetric):
            raise ValueError("metric_class must inherit from BaseMetric")

        # Instantiate temporarily to get the name
        instance = metric_class()
        metric_name = instance.name

        cls._metrics[metric_name] = metric_class

    @classmethod
    def get(cls, metric_name: str) -> Optional[Type[BaseMetric]]:
        """Get a metric class by name.

        Args:
            metric_name: Name of the metric

        Returns:
            Metric class if found, None otherwise
        """
        return cls._metrics.get(metric_name)

    @classmethod
    def create(cls, metric_name: str) -> BaseMetric:
        """Create a metric instance by name.

        Args:
            metric_name: Name of the metric

        Returns:
            Metric instance

        Raises:
            ValueError: If metric is not registered
        """
        metric_class = cls.get(metric_name)
        if metric_class is None:
            raise ValueError(
                f"Unknown metric: {metric_name}. " f"Available metrics: {cls.list_metrics()}"
            )

        return metric_class()

    @classmethod
    def list_metrics(cls) -> List[str]:
        """List all registered metric names.

        Returns:
            List of metric names
        """
        return list(cls._metrics.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered metrics.

        Useful for testing.
        """
        cls._metrics.clear()
