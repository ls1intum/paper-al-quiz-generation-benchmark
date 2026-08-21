"""Results aggregation module."""

import json
import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, TypedDict, Union

import numpy as np
import pingouin as pg
from scipy.stats import spearmanr

from ..models.result import (
    AggregatedResults,
    BenchmarkResult,
    MetricAggregation,
    MetricResult,
)


class CeilingEffectResult(TypedDict):
    has_ceiling_effect: bool
    affected_rater_indices: List[int]
    rater_std_devs: List[float]


_METRICS_WITH_APPLICABLE = {"objective_alignment", "homogeneous_options", "cognitive_level"}


class ResultsAggregator:
    """Aggregates benchmark results across multiple runs."""

    @staticmethod
    def _is_applicable(result: MetricResult) -> bool:
        """Check whether a MetricResult is applicable (should be included in aggregation)."""
        if result.metric_name not in _METRICS_WITH_APPLICABLE:
            return True
        try:
            data = json.loads(result.raw_response)
            return data.get("applicable", True)
        except (json.JSONDecodeError, TypeError, AttributeError):
            return True

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

        return float(lower_bound), float(upper_bound)

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
        # P1-3: exclude inapplicable items so they don't inflate means
        grouped_scores: Dict[tuple, List[float]] = defaultdict(list)
        total_counts: Dict[tuple, int] = defaultdict(int)
        applicable_counts: Dict[tuple, int] = defaultdict(int)

        for result in results:
            for metric in result.metrics:
                agg_key = (metric.metric_name, metric.evaluator_model)
                total_counts[agg_key] += 1
                if not ResultsAggregator._is_applicable(metric):
                    continue
                applicable_counts[agg_key] += 1
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
                n_applicable=applicable_counts[(metric_name, evaluator_model)],
                n_total=total_counts[(metric_name, evaluator_model)],
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
    def _paired_columns(
        reliability_array: np.ndarray,
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Return all valid (rater_i, rater_j) column pairs with no NaNs.

        For each pair of raters we keep only the items where *both* raters
        produced a score, so pairwise statistics are always computed on the
        same observations.
        """
        n_raters = reliability_array.shape[0]
        pairs = []
        for i in range(n_raters):
            for j in range(i + 1, n_raters):
                mask = ~np.isnan(reliability_array[i]) & ~np.isnan(reliability_array[j])
                if mask.sum() >= 2:
                    pairs.append((reliability_array[i][mask], reliability_array[j][mask]))
        return pairs

    @staticmethod
    def compute_mad(reliability_array: np.ndarray) -> Optional[float]:
        """Mean Absolute Deviation averaged across all rater pairs.

        Operates on the same scale as the original scores (0-100 here), so
        the result is immediately interpretable: a MAD of 4.5 means raters
        differ by 4.5 points on average.

        Args:
            reliability_array: M raters × N items matrix (NaN = missing).

        Returns:
            Mean absolute deviation, or None if fewer than one valid pair.
        """
        pairs = ResultsAggregator._paired_columns(reliability_array)
        if not pairs:
            return None

        pair_mads = [float(np.mean(np.abs(a - b))) for a, b in pairs]
        return float(np.mean(pair_mads))

    @staticmethod
    def compute_spearman(reliability_array: np.ndarray) -> Optional[Dict[str, float]]:
        """Spearman rank correlation averaged across all rater pairs.

        Unlike ICC and MAD, Spearman's ρ is insensitive to systematic bias
        (one rater always scoring higher). It answers: *do raters rank items
        the same way?* — which is ideal for comparing LLM raters.

        Returns a dict with:
            - spearman_rho: average ρ across all pairs
            - num_pairs: number of rater pairs used
        """
        pairs = ResultsAggregator._paired_columns(reliability_array)
        if not pairs:
            return None

        rhos = []
        for a, b in pairs:
            result = spearmanr(a, b)
            if not np.isnan(result.statistic):
                rhos.append(result.statistic)

        if not rhos:
            return None

        return {
            "spearman_rho": float(np.mean(rhos)),
            "num_pairs": len(rhos),
        }

    @staticmethod
    def detect_ceiling_effect(
        reliability_array: np.ndarray,
        std_threshold: float = 1.0,
        ceiling_value: float = 100.0,
    ) -> CeilingEffectResult:
        """Detect whether any rater suffers from a ceiling (or floor) effect.

        A rater with near-zero variance makes correlation metrics unreliable.
        This flags the issue so warnings can be surfaced.

        Args:
            reliability_array: M raters × N items matrix (NaN = missing).
            std_threshold: Std-dev below which a rater is flagged (default 1.0).
            ceiling_value: The maximum possible score (default 100.0).

        Returns:
            CeilingEffectResult with keys:
                - has_ceiling_effect (bool)
                - affected_rater_indices (list of int)
                - rater_std_devs (list of float, one per rater)
        """
        rater_stds: List[float] = []
        affected: List[int] = []

        for i, row in enumerate(reliability_array):
            valid = row[~np.isnan(row)]
            std = float(np.std(valid)) if len(valid) > 1 else 0.0
            rater_stds.append(std)
            if std < std_threshold:
                affected.append(i)

        return CeilingEffectResult(
            has_ceiling_effect=len(affected) > 0,
            affected_rater_indices=affected,
            rater_std_devs=rater_stds,
        )

    @staticmethod
    def _compute_reliability_status(
        icc: Optional[float],
        mad: Optional[float],
        spearman_rho: Optional[float],
    ) -> str:
        """Compute a summary reliability status based on primary metrics.

        Returns: "high", "moderate", or "low"
        """
        if icc is None or mad is None or spearman_rho is None:
            return "low"

        # Heuristic: all three metrics need to be good for "high" status
        icc_ok = icc > 0.7
        mad_ok = mad < 10  # Average disagreement less than 10 points
        spearman_ok = spearman_rho > 0.7

        if icc_ok and mad_ok and spearman_ok:
            return "high"
        elif (icc_ok or spearman_ok) and mad_ok:
            return "moderate"
        else:
            return "low"

    @staticmethod
    def calculate_inter_rater_reliability(
        results: List[BenchmarkResult], metric_name: str
    ) -> Dict[str, Union[str, float, int, List[str], None]]:
        """Calculate inter-rater reliability metrics for a specific metric.

        Primary metrics (robust to systematic bias and ceiling effects):
            - ICC(2,1)       — absolute agreement, two-way mixed
            - MAD            — mean absolute deviation (same scale as scores)
            - Spearman ρ     — rank agreement
        """
        # Step 1: Track all unique evaluators and items
        evaluators = set()
        items = set()
        lookup: Dict[str, Dict[Tuple[int, str, Optional[str]], float]] = defaultdict(dict)

        for result in results:
            for metric in result.metrics:
                if metric.metric_name == metric_name:
                    evaluators.add(metric.evaluator_model)
                    item_key = (result.run_number, metric.quiz_id, metric.question_id)
                    items.add(item_key)
                    lookup[metric.evaluator_model][item_key] = metric.score

        evaluators_list = sorted(list(evaluators))
        items_list = sorted(list(items))

        if len(evaluators_list) < 2 or not items_list:
            return {
                "metric_name": metric_name,
                "icc": None,
                "icc_ci_lower": None,
                "icc_ci_upper": None,
                "mad": None,
                "spearman_rho": None,
                "num_raters": len(evaluators_list),
                "raters": evaluators_list,
                "reliability_status": "low",
                "note": "Insufficient raters for reliability calculation",
            }

        # Step 2: Build aligned M (raters) × N (items) matrix
        reliability_data = []
        for evaluator in evaluators_list:
            row = [lookup[evaluator].get(item, np.nan) for item in items_list]
            reliability_data.append(row)

        reliability_array = np.array(reliability_data, dtype=float)

        # Step 3: Calculate all primary metrics
        icc_result = ResultsAggregator.compute_icc(reliability_array)
        mad_value = ResultsAggregator.compute_mad(reliability_array)
        spearman_result = ResultsAggregator.compute_spearman(reliability_array)
        ceiling_info = ResultsAggregator.detect_ceiling_effect(reliability_array)

        # Compute reliability status
        icc_val = icc_result.get("icc") if icc_result else None
        spearman_rho = spearman_result.get("spearman_rho") if spearman_result else None
        reliability_status = ResultsAggregator._compute_reliability_status(
            icc_val, mad_value, spearman_rho
        )

        # Build warning if ceiling effect detected
        warning = None
        if ceiling_info["has_ceiling_effect"]:
            stds = ceiling_info["rater_std_devs"]
            std_summary = ", ".join(
                f"{evaluators_list[i]} (σ={stds[i]:.2f})"
                for i in ceiling_info["affected_rater_indices"]
            )
            warning = (
                f"⚠️ Near-zero variance detected for {std_summary}. "
                f"Rank-based metrics (Spearman ρ) and MAD are more reliable."
            )

        return {
            "metric_name": metric_name,
            # Primary metrics
            "icc": icc_val,
            "icc_ci_lower": icc_result.get("ci_lower") if icc_result else None,
            "icc_ci_upper": icc_result.get("ci_upper") if icc_result else None,
            "mad": mad_value,
            "spearman_rho": spearman_rho,
            # Metadata
            "num_raters": len(evaluators_list),
            "raters": evaluators_list,
            "reliability_status": reliability_status,
            "reliability_warning": warning,
        }

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

            # Pre-check: ensure we have enough non-missing values
            # Pingouin requires at least 5 non-missing values
            non_nan_count = np.sum(~np.isnan(reliability_array))
            if non_nan_count < 5:
                return None

            # Step 1: Convert the 2D array into a long-format list of dictionaries
            records = []
            for rater_idx in range(n_raters):
                for item_idx in range(n_items):
                    score = reliability_array[rater_idx, item_idx]
                    if not np.isnan(score):  # Only include non-NaN values
                        records.append(
                            {
                                "rater": rater_idx,
                                "item": item_idx,
                                "score": score,
                            }
                        )

            if len(records) < 5:
                return None

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

            icc_value = float(icc_df["ICC"].iloc[0])
            ci95 = list(icc_df["CI95%"].iloc[0])
            ci_lower = float(ci95[0])
            ci_upper = float(ci95[1])

            return {
                "icc": icc_value,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
            }
        except (ValueError, TypeError, IndexError, AssertionError, RuntimeWarning):
            # Catches issues if data lacks variance, not enough observations,
            # or Pingouin throws an internal error (including divide-by-zero warnings)
            return None
