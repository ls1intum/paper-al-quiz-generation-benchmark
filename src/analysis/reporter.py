"""Results reporting module."""

from collections import defaultdict
from typing import Any

from ..models.result import AggregatedResults, BenchmarkResult


class ResultsReporter:
    """Generates human-readable reports from benchmark results."""

    @staticmethod
    def generate_summary(aggregated: AggregatedResults) -> str:
        """Generate a text summary of aggregated results.

        Args:
            aggregated: Aggregated results

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("BENCHMARK RESULTS SUMMARY")
        lines.append("=" * 80)
        lines.append(f"Configuration: {aggregated.benchmark_config_name}")
        lines.append(f"Version: {aggregated.benchmark_version}")
        lines.append(f"Total Runs: {aggregated.total_runs}")
        lines.append(f"Quizzes Evaluated: {len(aggregated.quiz_ids)}")
        lines.append("")

        # Display inter-rater reliability metrics if available
        if aggregated.inter_rater_reliability:
            lines.append("INTER-RATER RELIABILITY")
            lines.append("-" * 80)
            for metric_name, irr_metrics in aggregated.inter_rater_reliability.items():
                lines.append(f"\n{metric_name}:")
                status = irr_metrics.get("reliability_status", "unknown").upper()
                lines.append(f"  Status: {status}")

                # Primary metrics
                if irr_metrics.get("icc") is not None:
                    icc_val = irr_metrics["icc"]
                    ci_lower = irr_metrics.get("icc_ci_lower")
                    ci_upper = irr_metrics.get("icc_ci_upper")
                    if ci_lower is not None and ci_upper is not None:
                        lines.append(
                            f"  ICC(2,1): {icc_val:.4f} [95% CI: {ci_lower:.4f}, {ci_upper:.4f}]"
                        )
                    else:
                        lines.append(f"  ICC(2,1): {icc_val:.4f}")
                else:
                    lines.append("  ICC(2,1): Not enough data (requires ≥5 observations)")

                if irr_metrics.get("mad") is not None:
                    mad_val = irr_metrics["mad"]
                    lines.append(f"  MAD (Mean Absolute Deviation): {mad_val:.2f} points")
                else:
                    lines.append("  MAD: Insufficient data")

                if irr_metrics.get("spearman_rho") is not None:
                    rho = irr_metrics["spearman_rho"]
                    lines.append(f"  Spearman ρ: {rho:.4f}")
                else:
                    lines.append("  Spearman ρ: Insufficient data")

                # Raters and warnings
                raters = irr_metrics.get("raters", [])
                num_raters = irr_metrics.get("num_raters", 0)
                lines.append(f"  Raters ({num_raters}): {', '.join(raters)}")

                if irr_metrics.get("reliability_warning"):
                    lines.append(f"\n  ⚠️  {irr_metrics['reliability_warning']}")

            lines.append("")

        # Group by metric
        metrics = aggregated.get_all_metrics()

        for metric_name in sorted(metrics):
            lines.append(f"\n{metric_name.upper()}")
            lines.append("-" * 80)

            # Get all evaluators for this metric
            for agg_key, agg in sorted(aggregated.aggregations.items()):
                if agg.metric_name == metric_name:
                    lines.append(f"\n  Evaluator: {agg.evaluator_model}")
                    lines.append(f"    Mean:   {agg.mean:.2f}")
                    lines.append(f"    Median: {agg.median:.2f}")
                    lines.append(f"    Std Dev: {agg.std_dev:.2f}")
                    lines.append(f"    95% CI: [{agg.ci_lower:.2f}, {agg.ci_upper:.2f}]")
                    lines.append(f"    Min:    {agg.min:.2f}")
                    lines.append(f"    Max:    {agg.max:.2f}")
                    lines.append(f"    N:      {agg.num_runs}")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)

    @staticmethod
    def generate_comparison_report(aggregated: AggregatedResults, metric_name: str) -> str:
        """Generate a comparison report for a specific metric across evaluators.

        Args:
            aggregated: Aggregated results
            metric_name: Metric to compare

        Returns:
            Formatted comparison string
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"EVALUATOR COMPARISON: {metric_name}")
        lines.append("=" * 70)

        # Collect all aggregations for this metric
        metric_aggs = []
        for agg in aggregated.aggregations.values():
            if agg.metric_name == metric_name:
                metric_aggs.append(agg)

        if not metric_aggs:
            lines.append(f"No results found for metric: {metric_name}")
            return "\n".join(lines)

        # Sort by mean score
        metric_aggs.sort(key=lambda x: x.mean, reverse=True)

        # Table header
        lines.append(
            f"\n{'Evaluator':<30} {'Mean':<8} {'Median':<8} {'Std Dev':<8} {'Min':<8} {'Max':<8}"
        )
        lines.append("-" * 70)

        # Table rows
        for agg in metric_aggs:
            lines.append(
                f"{agg.evaluator_model:<30} "
                f"{agg.mean:>7.2f} "
                f"{agg.median:>7.2f} "
                f"{agg.std_dev:>7.2f} "
                f"{agg.min:>7.2f} "
                f"{agg.max:>7.2f}"
            )

        lines.append("=" * 70)

        return "\n".join(lines)

    @staticmethod
    def generate_quiz_report(results: list[BenchmarkResult], quiz_id: str) -> str:
        """Generate a detailed report for a specific quiz.

        Args:
            results: Benchmark results
            quiz_id: Quiz ID to report on

        Returns:
            Formatted report string
        """
        # Filter results for this quiz
        quiz_results = [r for r in results if r.quiz_id == quiz_id]

        if not quiz_results:
            return f"No results found for quiz: {quiz_id}"

        lines = []
        lines.append("=" * 70)
        lines.append(f"QUIZ REPORT: {quiz_id}")
        lines.append("=" * 70)

        # Get quiz metadata
        first_result = quiz_results[0]
        quiz_title = first_result.metadata.get("quiz_title", "Unknown")
        num_questions = first_result.metadata.get("num_questions", 0)

        lines.append(f"Title: {quiz_title}")
        lines.append(f"Questions: {num_questions}")
        lines.append(f"Runs: {len(quiz_results)}")
        lines.append("")

        # Aggregate metrics
        from collections import defaultdict

        metric_scores: dict[str, list[float]] = defaultdict(list)

        for result in quiz_results:
            for metric in result.metrics:
                key = f"{metric.metric_name}_{metric.evaluator_model}"
                metric_scores[key].append(metric.score)

        # Display aggregated metrics
        import statistics

        lines.append("METRIC SCORES")
        lines.append("-" * 70)
        for key, scores in sorted(metric_scores.items()):
            mean_score = statistics.mean(scores)
            std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0
            lines.append(f"{key:<40} {mean_score:>6.2f} ± {std_dev:>5.2f}")

        lines.append("=" * 70)

        return "\n".join(lines)

    @staticmethod
    def usage_summary(results: list[BenchmarkResult]) -> str:
        """One-line-per-cell token usage table grouped by evaluator x metric."""
        buckets: dict[str, dict[str, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"prompt_tokens": 0, "completion_tokens": 0})
        )
        for result in results:
            for m in result.metrics:
                if m.usage:
                    b = buckets[m.evaluator_model][m.metric_name]
                    b["prompt_tokens"] += m.usage.get("prompt_tokens", 0)
                    b["completion_tokens"] += m.usage.get("completion_tokens", 0)

        if not buckets:
            return "No token usage data recorded."

        lines = ["", "=" * 80, "TOKEN USAGE SUMMARY", "=" * 80]
        grand_prompt = grand_completion = 0

        for evaluator in sorted(buckets):
            lines.append(f"\n  Evaluator: {evaluator}")
            lines.append(f"    {'Metric':<30} {'Prompt':>10} {'Completion':>12} {'Total':>10}")
            lines.append("    " + "-" * 66)
            eval_prompt = eval_completion = 0
            for metric in sorted(buckets[evaluator]):
                p = buckets[evaluator][metric]["prompt_tokens"]
                c = buckets[evaluator][metric]["completion_tokens"]
                lines.append(f"    {metric:<30} {p:>10,} {c:>12,} {p + c:>10,}")
                eval_prompt += p
                eval_completion += c
            lines.append("    " + "-" * 66)
            lines.append(
                f"    {'SUBTOTAL':<30} {eval_prompt:>10,} {eval_completion:>12,} "
                f"{eval_prompt + eval_completion:>10,}"
            )
            grand_prompt += eval_prompt
            grand_completion += eval_completion

        lines.append(
            f"\n  {'GRAND TOTAL':<32} {grand_prompt:>10,} {grand_completion:>12,} "
            f"{grand_prompt + grand_completion:>10,}"
        )
        lines.append("=" * 80)
        return "\n".join(lines)

    @staticmethod
    def usage_dict(results: list[BenchmarkResult]) -> dict[str, Any]:
        """Machine-readable usage breakdown: {evaluator: {metric: {tokens}}}."""
        buckets: dict[str, dict[str, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"prompt_tokens": 0, "completion_tokens": 0})
        )
        for result in results:
            for m in result.metrics:
                if m.usage:
                    b = buckets[m.evaluator_model][m.metric_name]
                    b["prompt_tokens"] += m.usage.get("prompt_tokens", 0)
                    b["completion_tokens"] += m.usage.get("completion_tokens", 0)
        # Convert nested defaultdicts to plain dicts for JSON serialization
        return {ev: dict(metrics) for ev, metrics in buckets.items()}

    @staticmethod
    def export_to_dict(aggregated: AggregatedResults) -> dict[str, Any]:
        """Export aggregated results to a simple dictionary format.

        Args:
            aggregated: Aggregated results

        Returns:
            Dictionary with results
        """
        export: dict[str, Any] = {
            "benchmark_name": aggregated.benchmark_config_name,
            "version": aggregated.benchmark_version,
            "total_runs": aggregated.total_runs,
            "num_quizzes": len(aggregated.quiz_ids),
            "metrics": {},
            "inter_rater_reliability": aggregated.inter_rater_reliability,
        }

        for metric_name in aggregated.get_all_metrics():
            export["metrics"][metric_name] = {}

            for agg in aggregated.aggregations.values():
                if agg.metric_name == metric_name:
                    export["metrics"][metric_name][agg.evaluator_model] = {
                        "mean": round(agg.mean, 2),
                        "median": round(agg.median, 2),
                        "std_dev": round(agg.std_dev, 2),
                        "ci_lower": round(agg.ci_lower, 2),
                        "ci_upper": round(agg.ci_upper, 2),
                        "min": round(agg.min, 2),
                        "max": round(agg.max, 2),
                    }

        return export
