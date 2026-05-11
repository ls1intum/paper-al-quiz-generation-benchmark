"""Results aggregation module."""

import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import krippendorff
import pingouin as pg

from ..models.result import (
    AggregatedResults,
    BenchmarkResult,
    MetricAggregation,
)


class ResultsAggregator:
    """Aggregates benchmark results across multiple runs."""

    @staticmethod
    def bootstrap_confidence_interval(
        data: List[float], ci: float = 0.95, n_bootstrap: int = 10000
    ) -> Tuple[float, float]:
        """Calculate bootstrap confidence interval for a given dataset.

        Args:
            data: List of data points
            ci: Confidence level (default: 0.95 for 95% CI)
            n_bootstrap: Number of bootstrap samples (default: 10000)

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        if len(data) < 2:
            # If less than 2 data points, return the data range
            return (min(data), max(data)) if data else (0.0, 0.0)

        data_array = np.array(data)
        rng = np.random.default_rng(seed=42)

        # Generate bootstrap samples
        bootstrap_samples = rng.choice(
            data_array, size=(n_bootstrap, len(data_array)), replace=True
        )

        # Calculate means across the rows (axis=1)
        bootstrap_means = np.mean(bootstrap_samples, axis=1)

        # Calculate percentile-based confidence interval
        alpha = 1 - ci
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100

        lower_bound = np.percentile(bootstrap_means, lower_percentile)
        upper_bound = np.percentile(bootstrap_means, upper_percentile)

        return (float(lower_bound), float(upper_bound))

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
            ci_lower, ci_upper = ResultsAggregator.bootstrap_confidence_interval(all_scores)

            aggregations[agg_key] = MetricAggregation(
                metric_name=metric_name,
                evaluator_model=evaluator_model,
                mean=statistics.mean(all_scores),
                median=statistics.median(all_scores),
                std_dev=statistics.stdev(all_scores) if len(all_scores) > 1 else 0.0,
                min=min(all_scores),
                max=max(all_scores),
                per_run_scores=all_scores,
                ci_lower=ci_lower,
                ci_upper=ci_upper,
            )

        # Calculate inter-rater reliability for each metric
        inter_rater_reliability = {}
        all_metrics = set(agg.metric_name for agg in aggregations.values())
        for metric_name in all_metrics:
            irr = ResultsAggregator.calculate_inter_rater_reliability(results, metric_name)
            inter_rater_reliability[metric_name] = irr

        return AggregatedResults(
            benchmark_config_name=benchmark_name,
            benchmark_version=benchmark_version,
            quiz_ids=quiz_ids,
            total_runs=total_runs,
            aggregations=aggregations,
            inter_rater_reliability=inter_rater_reliability,
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
                ci_lower, ci_upper = ResultsAggregator.bootstrap_confidence_interval(scores)
                aggregations[evaluator_model] = MetricAggregation(
                    metric_name=metric_name,
                    evaluator_model=evaluator_model,
                    mean=statistics.mean(scores),
                    median=statistics.median(scores),
                    std_dev=statistics.stdev(scores) if len(scores) > 1 else 0.0,
                    min=min(scores),
                    max=max(scores),
                    per_run_scores=scores,
                    ci_lower=ci_lower,
                    ci_upper=ci_upper,
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
                "ci_lower": agg.ci_lower,
                "ci_upper": agg.ci_upper,
                "num_evaluations": agg.num_runs,
            }

        return comparison

    @staticmethod
    def calculate_inter_rater_reliability(
        results: List[BenchmarkResult], metric_name: str
    ) -> Dict[str, Union[str, float, int, List[str], None]]:
        """Calculate inter-rater reliability metrics for a specific metric."""
        # Step 1: Track all unique evaluators and all unique "items" evaluated
        evaluators = set()
        items = set()

        # Dictionary mapping: evaluator -> item_key -> score
        lookup: Dict[str, Dict[Tuple[int, str, Optional[str]], float]] = defaultdict(dict)

        for result in results:
            for metric in result.metrics:
                if metric.metric_name == metric_name:
                    evaluators.add(metric.evaluator_model)

                    # Create a unique key for the exact thing being rated
                    item_key = (result.run_number, metric.quiz_id, metric.question_id)
                    items.add(item_key)

                    lookup[metric.evaluator_model][item_key] = metric.score

        # If we don't have at least 2 evaluators, we can't calculate reliability
        evaluators_list = sorted(list(evaluators))
        items_list = sorted(list(items))

        if len(evaluators_list) < 2 or not items_list:
            return {
                "metric_name": metric_name,
                "krippendorff_alpha": None,
                "num_raters": len(evaluators_list),
                "raters": evaluators_list,
            }

        # Step 2: Build the perfectly aligned M x N matrix
        reliability_data = []
        for evaluator in evaluators_list:
            evaluator_row = []
            for item in items_list:
                # If this evaluator missed this specific item, append NaN
                score = lookup[evaluator].get(item, np.nan)
                evaluator_row.append(score)
            reliability_data.append(evaluator_row)

        reliability_array = np.array(reliability_data, dtype=float)

        # Step 3: Calculate Alpha and ICC
        alpha_value = ResultsAggregator.krippendorff_alpha(reliability_array)
        icc_result = ResultsAggregator.compute_icc(reliability_array)

        return {
            "metric_name": metric_name,
            "krippendorff_alpha": alpha_value,
            "icc": icc_result.get("icc") if icc_result else None,
            "icc_ci_lower": icc_result.get("ci_lower") if icc_result else None,
            "icc_ci_upper": icc_result.get("ci_upper") if icc_result else None,
            "num_raters": len(evaluators_list),
            "raters": evaluators_list,
        }

    @staticmethod
    def krippendorff_alpha(reliability_array: np.ndarray) -> Optional[float]:
        """Calculate Krippendorff's alpha from a pre-aligned reliability matrix."""
        try:
            # Note: The 'krippendorff' package generally uses 'level_of_measurement'
            # rather than 'level'. Double-check your specific library version!
            alpha = krippendorff.alpha(
                reliability_data=reliability_array, level_of_measurement="interval"
            )
            return float(alpha) if alpha is not None else None
        except (ValueError, ZeroDivisionError, TypeError):
            # Returns None if there's no variance (all scores identical) or other math errors
            return None

    @staticmethod
    def compute_icc(reliability_array: np.ndarray) -> Optional[Dict[str, float]]:
        """Calculate Intraclass Correlation Coefficient (ICC) from a pre-aligned reliability matrix.

        Uses ICC(2, 1): two-way mixed effects model with absolute agreement, single measurement.
        """
        if reliability_array.shape[0] < 2:
            return None

        try:
            import pandas as pd

            n_raters, n_items = reliability_array.shape

            # Step 1: Convert the 2D array into a long-format list of dictionaries
            records = []
            for rater_idx in range(n_raters):
                for item_idx in range(n_items):
                    records.append(
                        {
                            "rater": rater_idx,
                            "item": item_idx,
                            "score": reliability_array[rater_idx, item_idx],
                        }
                    )

            # Step 2: Create the DataFrame
            df = pd.DataFrame(records)

            # Step 3: Run Pingouin using column names
            icc_result = pg.intraclass_corr(
                data=df, targets="item", raters="rater", ratings="score"
            )

            # Extract ICC2 (Two-way mixed effects, absolute agreement, single measurement)
            icc_df = icc_result[icc_result["Type"] == "ICC2"]

            if icc_df.empty:
                return None

            # Use .iloc[0] for safer Pandas extraction
            icc_value = float(icc_df["ICC"].iloc[0])
            ci_lower = float(icc_df["CI95%"].iloc[0][0])
            ci_upper = float(icc_df["CI95%"].iloc[0][1])

            return {
                "icc": icc_value,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
            }
        except (ValueError, TypeError, IndexError):
            # Catches issues if data lacks variance or Pingouin throws an internal error
            return None
