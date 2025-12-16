"""Results aggregation module."""

import statistics
from collections import defaultdict
from typing import Dict, List

from ..models.result import (
    AggregatedResults,
    BenchmarkResult,
    MetricAggregation,
    MetricResult,
)


class ResultsAggregator:
    """Aggregates benchmark results across multiple runs."""

    @staticmethod
    def aggregate(results: List[BenchmarkResult], benchmark_name: str) -> AggregatedResults:
        """Aggregate results from multiple benchmark runs.

        Args:
            results: List of benchmark results to aggregate
            benchmark_name: Name of the benchmark configuration

        Returns:
            AggregatedResults with statistics
        """
        if not results:
            raise ValueError("Cannot aggregate empty results list")

        # Extract metadata
        benchmark_version = results[0].benchmark_version
        quiz_ids = list(set(r.quiz_id for r in results))
        total_runs = len(set(r.run_number for r in results))

        # Group metric results by (metric_name, evaluator_model, quiz_id, question_id)
        grouped_scores: Dict[tuple, List[float]] = defaultdict(list)

        for result in results:
            for metric in result.metrics:
                key = (
                    metric.metric_name,
                    metric.evaluator_model,
                    metric.quiz_id,
                    metric.question_id or "quiz_level",
                )
                grouped_scores[key].append(metric.score)

        # Calculate aggregations
        aggregations = {}

        # Group by (metric_name, evaluator_model) for overall stats
        overall_groups: Dict[tuple, List[float]] = defaultdict(list)
        for key, scores in grouped_scores.items():
            metric_name, evaluator_model, quiz_id, question_id = key
            overall_groups[(metric_name, evaluator_model)].extend(scores)

        for (metric_name, evaluator_model), all_scores in overall_groups.items():
            agg_key = f"{metric_name}_{evaluator_model}"

            aggregations[agg_key] = MetricAggregation(
                metric_name=metric_name,
                evaluator_model=evaluator_model,
                mean=statistics.mean(all_scores),
                median=statistics.median(all_scores),
                std_dev=statistics.stdev(all_scores) if len(all_scores) > 1 else 0.0,
                min=min(all_scores),
                max=max(all_scores),
                per_run_scores=all_scores,
            )

        return AggregatedResults(
            benchmark_config_name=benchmark_name,
            benchmark_version=benchmark_version,
            quiz_ids=quiz_ids,
            total_runs=total_runs,
            aggregations=aggregations,
        )

    @staticmethod
    def aggregate_by_quiz(results: List[BenchmarkResult]) -> Dict[str, AggregatedResults]:
        """Aggregate results separately for each quiz.

        Args:
            results: List of benchmark results

        Returns:
            Dict mapping quiz_id to AggregatedResults
        """
        # Group results by quiz
        by_quiz: Dict[str, List[BenchmarkResult]] = defaultdict(list)
        for result in results:
            by_quiz[result.quiz_id].append(result)

        # Aggregate each quiz separately
        aggregated_by_quiz = {}
        for quiz_id, quiz_results in by_quiz.items():
            aggregated_by_quiz[quiz_id] = ResultsAggregator.aggregate(
                quiz_results, f"quiz_{quiz_id}"
            )

        return aggregated_by_quiz

    @staticmethod
    def aggregate_by_metric(
        results: List[BenchmarkResult], metric_name: str
    ) -> Dict[str, MetricAggregation]:
        """Aggregate results for a specific metric across all evaluators.

        Args:
            results: List of benchmark results
            metric_name: Name of the metric to aggregate

        Returns:
            Dict mapping evaluator_model to MetricAggregation
        """
        # Group by evaluator
        by_evaluator: Dict[str, List[float]] = defaultdict(list)

        for result in results:
            for metric in result.metrics:
                if metric.metric_name == metric_name:
                    by_evaluator[metric.evaluator_model].append(metric.score)

        # Calculate aggregations
        aggregations = {}
        for evaluator_model, scores in by_evaluator.items():
            if scores:
                aggregations[evaluator_model] = MetricAggregation(
                    metric_name=metric_name,
                    evaluator_model=evaluator_model,
                    mean=statistics.mean(scores),
                    median=statistics.median(scores),
                    std_dev=statistics.stdev(scores) if len(scores) > 1 else 0.0,
                    min=min(scores),
                    max=max(scores),
                    per_run_scores=scores,
                )

        return aggregations

    @staticmethod
    def compare_evaluators(
        results: List[BenchmarkResult], metric_name: str
    ) -> Dict[str, Dict[str, float]]:
        """Compare different evaluators for a specific metric.

        Args:
            results: List of benchmark results
            metric_name: Name of the metric to compare

        Returns:
            Dict mapping evaluator_model to statistics dict
        """
        aggregations = ResultsAggregator.aggregate_by_metric(results, metric_name)

        comparison = {}
        for evaluator_model, agg in aggregations.items():
            comparison[evaluator_model] = {
                "mean": agg.mean,
                "median": agg.median,
                "std_dev": agg.std_dev,
                "min": agg.min,
                "max": agg.max,
                "num_evaluations": agg.num_runs,
            }

        return comparison
